# django-wide-events — internals

Currently under construction

<!-- one-line scope: how the package works under the hood. Usage lives in the README; -->
<!-- this page is for contributors and for users who hit an edge case. -->

---

## Overview

<!-- NOTES: the three moving parts and how they depend on each other: -->
<!--   context vars  -> hold per-request state (source of truth) -->
<!--   event blocks  -> typed writers/readers on top of the context vars -->
<!--   middleware    -> opens the context, runs collector hooks, emits, closes -->
<!-- A small diagram fits here (request -> middleware -> view -> finally -> logger). -->

### Request lifecycle at a glance

<!-- NOTES: numbered list of what happens for one request, in order: -->
<!--   1. no_logging() path check -> bail out early -->
<!--   2. CtxDict.init() opens the four context vars -->
<!--   3. collectors instantiated per request, stored in ContextCollectors -->
<!--   4. on_create hooks -->
<!--   5. process_view reads `capture` off the view (FBV or view_class) -->
<!--   6. view runs; on raise -> process_exception (ExceptionEvent + on_exception hooks) -->
<!--   7. finally: on_finish / on_finish_no_response hooks -->
<!--   8. _log() emits once with extra={"event", "capture"} -->
<!--   9. drop_all() resets the context vars -->

---

## Context vars

<!-- NOTES: why ContextVar and not request attributes / thread locals: -->
<!-- async-safe, reachable from code that never sees `request`, isolated per task. -->

### The four variables

<!-- NOTES: table — name, type, what it holds, who writes it: -->
<!--   _current     dict | None   the event payload        ContextEvent / blocks -->
<!--   _blocks      dict | None   key -> attached block(s) ContextBlock.attach -->
<!--   _collectors  list | None   collector instances      middleware -->
<!--   _capture     bool | None   per-view capture flag    process_view -->

### Lifecycle: init, token, drop

<!-- NOTES: BaseContext.init() sets a fresh value and keeps the Token; drop() resets -->
<!-- to that token and returns the value it held. Why reset() instead of set(None): -->
<!-- nesting / restoring outer state. ContextCapture.init() starts at None, not {}. -->

### Outside a request

<!-- NOTES: get() returns {} / [] / None when nothing is open — writes then go into -->
<!-- a throwaway dict and are lost silently. Decide: is that the intended behaviour? -->
<!-- Link to the Celery / "anything else" story once it exists. -->

### Merge semantics

<!-- NOTES: ContextEvent.merge rules, one example each: -->
<!--   - dicts merge recursively -->
<!--   - drop_none skips None values -->
<!--   - append_lists: list-on-list extends, list-on-scalar overwrites, -->
<!--     list-on-nothing writes a copy -->
<!--   - payload is positional on purpose (field names like 'ctx' / 'drop_none') -->

### The raw event API (advanced)

- Not part of the everyday API; blocks cover normal use. Documented here for power users
- `ContextEvent.set(**fields)`: shallow write at the top level
- `ContextEvent.update(payload, drop_none=True, append_lists=False)`: deep merge, following the rules above
- `ContextEvent.get()`: the current event dict, or `{}` outside a request

---

## Collectors reference

<!-- NOTES: the lists below moved here from the README. -->

### Built-in collectors (always run)

- `Duration`: `duration_ms`; runs first on create and last on finish, so it times everything else
- `StatusCode`: `status_code` (`500` when the view produced no response)
- `RequestRoute`: `route` (the resolver's `view_name`)
- `StaticFields`: copies `STATIC_FIELDS` into the event
- `RequestID` (via `RequestIDFactory`): `request_id`, also set as `request.request_id`; reuses an incoming `X-Request-Id` when `TRUST_ID_HEADER` is on
- `ResponseID` (via `ResponseIDFactory`): writes the id to the response header named by `REQUEST_ID.RESPONSE_HEADER`
- Registered with `@builtin_collector` / `@factory_collector` in `collectors/builtin/registry.py`

### Default collectors (replaceable through `COLLECTORS`)

- `User`: `user.{id, username, is_authenticated, is_staff, is_superuser, is_anonymous}`
- `MetaData`: `meta.{method, timezone, timestamp}`

### Order

- Built-ins, then factories, then `COLLECTORS`; hook ordering rules are applied on top (see [Hook ordering](#hook-ordering))

---

## Event blocks

<!-- NOTES: a block is a typed handle onto one sub-dict of the event, found by its path. -->

### Class creation: namespace and path

<!-- NOTES: __init_subclass__ validation (namespace required unless abstract, str, -->
<!-- non-empty, no '.'), and how `path` is built from the parent chain. -->
<!-- Parent rules: must be an EventBlock, not abstract, not multiple. -->

### Keys and the block registry

<!-- NOTES: get_key() = ".".join(path); why banning '.' keeps keys unique. -->
<!-- The registry is the _blocks context var, keyed by that string. -->

### Attaching

<!-- NOTES: __post_init__ -> _attach() -> ContextBlock.attach. -->
<!--   multiple=False: second attach raises BlockAlreadyAttached -->
<!--   multiple=True:  appended to a list; current() returns the last one -->

### Writing

<!-- NOTES: set() -> merge into get() (the namespaced sub-dict), or into the event -->
<!-- root when use_namespace_on_write=False. Which class flags feed merge: -->
<!-- drop_none, append_list. get() creates the path with setdefault. -->

### from_kwargs vs. constructing

<!-- NOTES: from_kwargs reuses the attached block for single blocks, constructs -->
<!-- for multiple ones. Constructing directly a second time raises. -->

### Timers

<!-- NOTES: TimerEventBlock.timer(name) -> _Timer; context manager or start/stop; -->
<!-- writes timers.<name>_ms rounded to 2 dp via perf_counter. TimerNotStarted. -->

### Built-in blocks

<!-- NOTES: ExceptionEvent ("error": type/message/stack) and HookErrorEvent -->
<!-- ("hook_error", append_list -> hook_errors list). Who writes them and when. -->

---

## Middleware

### Startup: assembling collectors

<!-- NOTES: order is BUILTIN_COLLECTORS + FACTORY_COLLECTORS (called once) + -->
<!-- settings COLLECTORS. Copy of the builtin list so the registry isn't mutated. -->
<!-- Built once in __init__, instances created per request (return_collectors). -->

### The hook table

<!-- NOTES: self.hooks maps phase -> list of indexes into collectors_classes. -->
<!-- A collector is included only if it overrides the base Collector method -->
<!-- (get_hook_phase_function, factories resolved via type(cls())). -->

### Hook ordering

<!-- NOTES: HookPositionChanges / HookPosition / Change. Duration is first on -->
<!-- on_create and last on on_finish(+_no_response) so it wraps every other hook. -->
<!-- Index semantics: resolved against phase length before removal; -1 = append. -->
<!-- Phases the class doesn't implement are skipped. -->

### Running a phase

<!-- NOTES: run_hook_phase: each hook isolated in try/except; a failing hook never -->
<!-- breaks the request, it lands in HookErrorEvent as "<Class>.<phase>" + stack. -->
<!-- on_finish switches to the on_finish_no_response list when response is None. -->

### Exceptions

<!-- NOTES: process_exception records ExceptionEvent, runs on_exception, returns -->
<!-- None so Django's own handling continues. -->

### Per-view capture

<!-- NOTES: process_view reads `capture` from the view (view_class for CBVs) and -->
<!-- stores it in ContextCapture; the filter reads it back from the log record. -->

### Emitting

<!-- NOTES: one call per request. ERROR when status_code is missing or >= 500, -->
<!-- INFO otherwise. extra carries "event" and "capture" for formatter + filter. -->

### Skipped paths

<!-- NOTES: NO_LOGGING_PATHS prefix match; no context is opened at all, so -->
<!-- block writes in those views go nowhere. -->

---

## From the event to the log line

<!-- NOTES: short hand-off to settings.LOGGING: filter (sampling, capture) and -->
<!-- formatter (JSON, exc_info -> error) read record.event / record.capture. -->
<!-- Link the README sections rather than repeating them. -->

## Extending

<!-- NOTES: pointers for contributors — writing a collector, adding a hook -->
<!-- position rule, adding a built-in block. -->
