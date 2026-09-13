```

src/django-wide-events
    config
    collectors/
        __init__
        HTTP
        ...
    

```

## Basic Workflow

One dict per request. The middleware creates it, anything anywhere writes to it
through the `event` proxy, and the middleware takes it back with `drop()`.

```mermaid
sequenceDiagram
    autonumber
    participant M as Middleware
    participant CV as context.py<br/>_current: ContextVar
    participant E as event (proxy)
    participant V as View / services
    participant L as logging

    M->>CV: init(request_id) -> fresh dict
    Note over CV: default is None, never a shared {}
    M->>V: get_response(request)
    V->>E: event.set(**kwargs)
    E-->>CV: lazy import, _current.get()
    E->>CV: dict.update(kwargs)
    Note over E: no active event -> silent no-op
    V-->>M: response
    M->>CV: drop() -> returns dict, clears ContextVar
    Note over M,CV: in a finally block
    M->>M: merge dict at top level of the emitted event
    M->>L: logger.info("request", extra={"event": ...})
```

`drop()` replaces the usual `set()`/`reset(token)` pair: the middleware owns the
whole lifecycle, so there is no outer value to restore — clearing is enough, and
handing the dict back in the same call means the middleware never reads the
ContextVar after it has been cleared.

## Context Vars

`context.py` owns the ContextVar and imports nothing from the rest of the package
(and nothing from Django). The `event` proxy resolves it **lazily, on each call**,
so importing `event` at module scope anywhere in a host project is safe and cannot
close over a stale context.

```mermaid
flowchart LR
    app["your app code<br/>from django_wide_events import event"]
    ev["event proxy<br/>.set(**kwargs)"]
    ctx["context.py<br/>_current: ContextVar[dict | None]<br/>default=None"]
    mw["middleware.py"]

    app -->|import at module scope| ev
    ev -.->|lazy import, per call| ctx
    mw -->|init / drop| ctx
```

```mermaid
classDiagram
    class context {
        <<module>>
        -ContextVar _current
        +init(request_id) dict
        +get_event() dict|None
        +drop() dict
    }
    class Event {
        +set(kwargs) None
    }
    Event ..> context : lazy import per call
    context --o "0..1 per execution context" dict : the event
```

## Running outside a request

The core is stdlib-only and works in any Python process. Requests are just the
most common unit of work, not the only one — Celery tasks, management commands
and scripts get the same one-event-per-unit treatment through the same
ContextVar, formatter and filter.

**The layering rule:** nothing outside the adapter layer imports Django.

```mermaid
flowchart TB
    subgraph core["core — stdlib only"]
        ctx["context.py<br/>ContextVar, event, wide_event()"]
        fmt["formatters/<br/>logging.Formatter"]
        flt["filters/<br/>logging.Filter"]
    end
    subgraph adapters["adapters — import their framework"]
        mw["middleware.py<br/>source='request'"]
        cel["contrib/celery.py<br/>source='task'"]
        cmd["management commands<br/>source='command'"]
    end
    mw --> ctx
    cel --> ctx
    cmd --> ctx
    ctx --> fmt
    ctx --> flt
```

Each adapter does exactly three things: open a context, seed the fields only it
can know, emit once in a `finally`. Everything between is identical.

```mermaid
sequenceDiagram
    participant A as Adapter (middleware / celery / command)
    participant CV as ContextVar
    participant W as work (view, task body, handle())
    participant L as logging

    A->>CV: ContextEvent.init(source=..., request_id=...)
    A->>W: run
    W->>CV: event.set(...)
    W-->>A: done or raise
    A->>CV: drop()
    Note over A,CV: finally
    A->>L: one record, extra={"event": ...}
```

### Celery

`contrib/celery.py` wires four signals, so no task needs decorating:

| signal | does |
| --- | --- |
| `before_task_publish` | stamps the **caller's** trace_id/request_id onto the message headers |
| `task_prerun` | opens the context, seeds task name, task_id, retries, and the inherited trace |
| `task_failure` | records `error.type` / `error.message` |
| `task_postrun` | drops the context and emits exactly one event |

The publish/prerun pair is what makes a task correlatable back to the request
that queued it: `trace_id` survives the hop, `parent_request_id` names the
request, and the task's own `task_id` becomes its `request_id`. One query on
`trace_id` returns the request and every task it spawned.

### Anything else

```python
from django_wide_events.context import wide_event, event

with wide_event("command", name="backfill_thumbnails"):
    event.set(processed=n)
```

Emits on the way out, records the exception and re-raises if the block fails.

# Step 1 - Event Core

**Goal:** an event exists per request, code anywhere can write to it, and writing
outside one is harmless.

**Observable outcome:** pure pytest tests. No Django client, no settings, no
middleware, no logging. If a test here needs `client`, the step has grown too big.

## In scope

1. `context.py` — **no Django imports at all**
2. `EventContext`: the event dict + `source` ("request"/"command"/"task"),
   `request`/`response` (None here), `started_at`
3. The ContextVar holding the current `EventContext`
4. `get_event()` -> `dict | None`
5. The `event` proxy — module-level, safe to import anywhere, resolves to the
   current context **on each call**: `.set(**kwargs)`, `.update(dict)`
6. An enter/exit helper (contextmanager) that sets the ContextVar and **resets the
   token** on the way out

## Out of scope — deliberately

- `event.timer()` / `event.incr()` — conveniences over `.set()`, and `timer()` hides
  an undecided naming rule (`"s3.fetch"` -> `s3_fetch_ms`). Nothing downstream blocks
  on them.
- Blocks — they attach to the core, but the attach/flush lifecycle is its own step
- Settings — the core reads none. Keep it that way; it is what keeps `context.py`
  Django-free.
- The middleware. Step 1 proves the core works; step 2 drives it from a request.

## How ContextVars work — the short version

`contextvars.ContextVar` is stdlib (3.7+). Think of it as a global whose value is
scoped to "the current execution context" — one value per thread, and one per asyncio
task, without either of them seeing the others'.

```python
_current: ContextVar[EventContext | None] = ContextVar("wide_event", default=None)

token = _current.set(ctx)   # set() returns a Token = the PREVIOUS value
try:
    ...                     # anything called from here sees ctx via _current.get()
finally:
    _current.reset(token)   # restore what was there before
```

Four properties that matter for us:

- **Reads are ambient.** Deep service code calls `_current.get()` with no arguments and
  no plumbing — that is why there is no `request.event`.
- **`set()` returns a Token, not None.** `reset(token)` puts back the *previous* value,
  which is why the enter/exit helper has to hold onto it. Ignoring the token is the
  classic bug.
- **A new asyncio task copies the current context.** Values set before the task started
  are visible inside it; values the task sets afterwards are invisible to the parent.
  Awaiting in the same task keeps everything as-is, which is what makes one async
  middleware work.
- **A new thread starts empty**, but a *reused* one does not — WSGI runs requests on a
  worker pool, so a context left unreset stays visible to whatever request lands on that
  worker next. Hence the `finally`.

## Decide while building

- **Deep merge semantics.** §2 says `update()` is "deep-merged" — merge nested dicts
  recursively, or replace at the top level? Lists: replace or extend?
- **No-op return value.** Writing with no active event is a silent no-op — does
  `.set()` return `self` (so chaining keeps working) or None?
- **Reset discipline.** Token per context, reset in a `finally`. This is the one thing
  in step 1 that silently corrupts data if wrong: a missed reset leaks one request's
  event into the next on a reused worker.

## Tests

- set -> `get_event()` roundtrip inside an active context
- write outside a context is a no-op; `get_event()` is None
- `update()` deep-merges rather than clobbering a sibling key
- two sequential contexts don't leak into each other
- the value survives an `await` (this is the ContextVar's whole point, and §11 promises
  async middleware)

# Step 2 - Formatter

## Time?
How should the time be set? time needs to be configureable with django and not
propose: extra time file

## Formatter split
Formatters will be spilt. if_indent will be set at top-level

# Step 3 - Middleware

## Configure settings
- how read the settings from the file?
- How to split into django and non-django
## Build Middleware

- build all collectors and stuff at init/variables
- each run:
  - skips logging for certain paths
  - adds static fields
  - runs collectors
  - feeds context to event
  - sets the error of the request / decides if logging info or error
  - set the request id // if not trusted by the header

## Collectors

- Add Static Fields
- Add the base range of Collectors

### Test No logging Paths // increased performance 

- 

# Step 4 - Filter

1. Incooperate settings
2. Write simple randomsampling filter
3. Write Tailsampling filter
4. Add keep Rules

