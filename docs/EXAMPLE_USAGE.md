# django-wide-events — vision / example usage

> Status: **design sketch, revision 2**. Nothing is implemented. This file is the target
> API we refine before writing code.

## Design goals

1. Adapt to Django's `logging` (formatters / filters / handlers) + middleware. No parallel pipeline.
2. One event per request, built up everywhere, emitted once.
3. Pluggable: **you** decide which fields exist, at three depths (settings → collectors → view code).
4. Opt-out (and opt-in) per view via decorators, not just settings paths.
5. Correlatable across a session — but as a *separate, optional* middleware.
6. Ship defaults only for **collectors** and **keep rules**. Everything else is explicit.

---

## 1. Install & minimal setup

```bash
pip install django-wide-events
```

```python
# settings.py
INSTALLED_APPS = [..., "django_wide_events"]

MIDDLEWARE = [
    "django_wide_events.middleware.WideEventMiddleware",   # as early as possible
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    ...,
]

WIDE_EVENTS = {
    "STATIC_FIELDS": {...},   # §4
    "SAMPLING": {...},        # §7
}

LOGGING = {...}               # §6 — you write this, the package ships no helper
```

Result: one JSON line per request.

```json
{
  "severity": "INFO", "message": "request", "logger": "wide_events.request",
  "created": "2026-08-27T09:14:22.481Z",
  "request_id": "6f1c…",
  "method": "GET", "path": "/pictures/42/", "route": "pictures:detail",
  "status_code": 200, "duration_ms": 37.4,
  "user_id": 17, "user_authenticated": true,
  "env": "prod", "service": "mysite", "commit": "e4e2fa5",
  "picture": {"action": "download", "picture_id": 42, "is_owner": true},
  "sample_rate": 1
}
```

---

## 2. Writing to the event

The event lives in a `ContextVar`. There is **no `request.event`** — one way in, and deep
service code never needs the `request` object plumbed through to it.

```python
from django_wide_events import event, get_event

def picture_detail(request, public_id):
    event.set(picture_id=public_id)
    event.update({"picture": {"is_owner": True}})   # deep-merged
    with event.timer("s3.fetch"):                   # -> s3_fetch_ms
        blob = storage.read(pic.key)
    event.incr("cache_misses")

    current = get_event()      # the raw dict, or None outside a request
```

`event` is a module-level proxy — safe to import anywhere, resolves to the current
context's event on each call. `get_event()` is the escape hatch when you need the dict
itself (tests, a debug view, handing it to something else). Writing outside an active
event is a silent no-op.

That is the *ad-hoc* path. For domain data, use blocks (§3).

---

## 3. Event blocks — the class-based enrichment API

This generalises `example_code/picture_log.py`. A block is an object you build up over
the life of a view, which lands in the event as **one JSON block** under its namespace
when the event is emitted.

### 3a. Declaring a block

Blocks are **loose**: no field declarations, set what you like. This keeps v1 small.

```python
# myapp/observability.py
from django_wide_events import EventBlock

class PictureBlock(EventBlock):
    namespace = "picture"          # -> event["picture"] = {...}

    # named constructors, exactly like your SimplePictureLog
    @classmethod
    def download(cls, picture_id: int):
        return cls(action="download", picture_id=picture_id)

    @classmethod
    def upload(cls):
        return cls(action="upload")

    # enrichers stay hand-written and chainable
    def owner(self, is_owner: bool):
        return self.set(is_owner=is_owner)

    def from_form(self, form):
        self.set(form_valid=form.is_valid())
        if not form.is_valid():
            self.set(form_error=form.errors.as_json())
        return self
```

`EventBlock` gives you: `__init__(**kwargs)`, a chainable `.set(**kwargs)` /
`.update(dict)`, `None`-valued keys dropped at render time, and the attach/flush
lifecycle below. Everything else is your class.

> **Planned, not v1:** a strict/declared variant (`fields` on the class, generated
> setters, typo protection) for apps with many views sharing one block. The base class
> is designed so it can be added later without changing this API — a strict subclass
> just constrains what `.set()` accepts. Same for auto-generated setters. Not building
> it now; not designing it out either.

### 3b. Using a block

```python
def download(request, public_id):
    block = PictureBlock.download(public_id)        # auto-attaches to the current event
    pic = get_object_or_404(Picture, public_id=public_id)
    block.owner(pic.owner_id == request.user.id).set(is_public=pic.is_public)
    return FileResponse(...)
```

**No `.emit()` / `.render(request)` call.** Constructing a block inside an active event
registers it on that event; the **middleware flushes every attached block** in its
`finally`, alongside everything else. Nothing is lost when a view returns early or
raises — which is exactly when you most want the data.

Retrieve the block anywhere downstream, no plumbing:

```python
PictureBlock.current()                  # the attached block, or None
PictureBlock.current().set(is_thumbnail=True)
PictureBlock.require()                  # same, but raises if not attached
```

Constructing a block outside an active event is harmless — it just never flushes, so
shells, tests and management commands don't blow up.

Collision policy per block class:

```python
class QueryBlock(EventBlock):
    namespace = "queries"
    multiple = True      # attaching twice -> event["queries"] is a list of blocks
```

With `multiple = False` (the default), a second attach merges into the first, and
`.current()` is unambiguous.

### 3c. The auto-fill decorator

Most blocks start with values already sitting in the view signature. The decorator
builds and attaches the block before the view body runs:

```python
from django_wide_events import capture_block

@capture_block(PictureBlock, action="download", picture_id="public_id")
def download(request, public_id):
    ...                                       # block already exists and is attached
    PictureBlock.current().set(is_owner=True)
```

- `action="download"` — a literal value.
- `picture_id="public_id"` — pull from the view's URL kwarg of that name.

Also against a named constructor, and on class-based views:

```python
@capture_block(PictureBlock.download, picture_id="public_id")

class PictureDetail(CaptureBlockMixin, DetailView):
    event_block = PictureBlock
    event_block_defaults = {"action": "detail"}
    event_block_from_kwargs = ["picture_id"]
```


## 4. Static fields

```python
WIDE_EVENTS = {
    "STATIC_FIELDS": {          # merged into every event; no default, no magic
        "service": "mysite",
        "env": env("ENV_NAME"),
        "commit": env("GIT_COMMIT"),
        "region": env("FLY_REGION", default=None),   # None values are dropped
    },
}
```

---

## 5. Collectors

Collectors produce the framework-level fields. They are keyed to the **event lifecycle**,
not to the request cycle, because an event can also come from a management command, a
task, or an autoloader — anything that isn't a request.

```python
from django_wide_events import Collector

class TenantFields(Collector):
    requires_request = True          # skipped for non-request events

    def on_created(self, ctx) -> dict:
        return {"tenant_id": ctx.request.tenant.id}

    def on_finished(self, ctx) -> dict:
        return {"cache_status": ctx.response.headers.get("X-Cache", "miss")}

    def on_exception(self, ctx, exc) -> dict:
        return {"tenant_degraded": isinstance(exc, TenantUnavailable)}
```

`ctx` is an `EventContext`: `.event`, `.request` (may be `None`), `.response`
(may be `None`), `.source` (`"request"` / `"command"` / `"task"`), `.started_at`.
All hooks optional. A collector that raises records
`collector_errors: ["TenantFields: KeyError('tenant')"]` rather than breaking the
request; `"STRICT_COLLECTORS": True` re-raises in dev.

### Configuring the list

**Setting `COLLECTORS` replaces the default list entirely** — it flushes, it never
appends. Nothing is silently bolted on top of what you wrote.

To get the defaults back, name them explicitly. `DEFAULTS` is a sentinel that expands in
place to the shipped list:

```python
WIDE_EVENTS = {
    "COLLECTORS": [
        "django_wide_events.collectors.DEFAULTS",         # expands here
        "myapp.observability.TenantFields",               # yours, wins on conflict
    ],
}
```

Because it expands *in place*, you control precedence — put `DEFAULTS` last and the
shipped collectors override yours instead:

```python
    "COLLECTORS": ["myapp.observability.TenantFields",
                   "django_wide_events.collectors.DEFAULTS"],
```

Drop the sentinel and you get exactly your list, nothing else:

```python
    "COLLECTORS": ["myapp.observability.TenantFields"],   # no framework fields at all
```

Omit the `COLLECTORS` key entirely and you get the defaults — zero-config still works.

It's a **string** sentinel, not an imported symbol, so `settings.py` stays free of
package imports at module level (no app-registry-not-ready surprises).

The shipped default list:

```python
"django_wide_events.collectors.RequestMeta"    # request_id, created, timezone
"django_wide_events.collectors.Http"           # method, path, route, status, duration_ms
"django_wide_events.collectors.User"           # user_id, authenticated, is_staff
"django_wide_events.collectors.Exception"      # error.type / .message / .stack
```

Shipped but **not** in the defaults, name them to switch them on:

```python
"django_wide_events.collectors.Headers"        # allow-listed request headers
"django_wide_events.collectors.DatabaseCounters"   # see §12
```

---

## 6. Logging config — yours to write

The package ships `JSONFormatter`, `IndentJSONFormatter`, `RandomSampling` and
`TailSampling`. It does **not** ship a `LOGGING` builder; you wire it exactly like your
example project does today, including the dev-indent switch:

```python
# settings/logging.py
_formatter = (
    "django_wide_events.logging.IndentJSONFormatter" if is_dev
    else "django_wide_events.logging.JSONFormatter"
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"wide": {"()": _formatter}},
    "filters": {
        "tail_sampling": {"()": "django_wide_events.logging.TailSampling"},
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "wide",
            "filters": ["tail_sampling"],
        },
    },
    "loggers": {
        # fixed name in v1 — see §14
        "wide_events": {"handlers": ["stdout"], "level": "INFO", "propagate": False},
        "django.request": {"handlers": ["stdout"], "level": "ERROR", "propagate": False},
    },
}
```

Note the filter takes **no kwargs** — its knobs live in `WIDE_EVENTS["SAMPLING"]` (§7),
so tuning rates never means editing the `LOGGING` dict.

`IndentJSONFormatter` stays a two-line subclass overriding `_dumps`, as in your example.

---

## 7. Sampling

Two filters, two separate concerns, both plain `logging.Filter`:

- **`RandomSampling`** — outcome-independent. Deterministic hash of `request_id` at a flat
  rate. Cheap, unbiased, good for firehose endpoints.
- **`TailSampling`** — outcome-aware. Keep rules first (errors, slow, writes, security),
  deterministic hash sampling for whatever is left. Needs `duration_ms` and
  `status_code`, which is why it belongs in the filter, after the event is complete.

Both record `sample_rate` on the event so counts can be re-weighted downstream.

```python
WIDE_EVENTS = {
    "SAMPLING": {
        "BASE_RATE": 100,      # required if a sampling filter is installed
        "SLOW_MS": 1000,       # required by TailSampling
        "KEEP_RULES": [                                       # default shown
            "django_wide_events.sampling.keep_errors",        # level >= ERROR or event.error
            "django_wide_events.sampling.keep_server_errors", # status missing or >= 500
            "django_wide_events.sampling.keep_slow",          # duration_ms >= SLOW_MS
            "django_wide_events.sampling.keep_writes",        # non GET/HEAD
            "django_wide_events.sampling.keep_security",      # 401 / 403 / 429
        ],
    },
}

# a keep rule is just a function; any True => keep, sample_rate 1
def keep_checkout(event, record) -> bool:
    return event.get("route", "").startswith("checkout:")
```

`KEEP_RULES` follows the same flush-and-compose rule as collectors: setting it replaces
the shipped list, and `"django_wide_events.sampling.DEFAULTS"` expands in place to the
five rules above.

```python
    "KEEP_RULES": [
        "django_wide_events.sampling.DEFAULTS",
        "myapp.observability.keep_checkout",
    ],
```

---

## 8. Marking views — whether and how much to log

These decorators answer **"should this path be logged, and at what rate?"** and nothing
else. They carry **no data**. Field content comes from `STATIC_FIELDS` (§4), collectors
(§5), or blocks (§3) — three ways in is already plenty, and a fourth that only works on
views would be the one people reach for by accident.

```python
WIDE_EVENTS = {"EXCLUDE_PATHS": ["/health", "/static/"]}   # no default
```

```python
from django_wide_events import always_capture, capture, never_capture

@never_capture                                  # never emitted
def healthz(request): ...

@never_capture(reason="noisy poller")           # documented opt-out, reason is for humans
def sse_stream(request): ...

@always_capture                                 # never sampled away, whatever the rate
def checkout(request): ...

@capture(sample_rate=1000)                      # cheap, high volume — sample hard
def thumbnail(request): ...

@capture                                        # opt in at the configured base rate
def signup(request): ...
```

`@always_capture` is the readable spelling of `@capture(sample_rate=1)`; both exist, the
first is what you should write.

Class-based views get the same knobs and nothing more:

```python
class PictureDetail(CaptureMixin, DetailView):
    capture = True               # or False, the CBV form of @never_capture
    capture_sample_rate = 10
```

`WIDE_EVENTS["MODE"] = "opt-in"` flips the default so only `@capture` /
`@always_capture` views are logged — useful when retrofitting a large project gradually.

Note the deliberate split, and the two mixins that follow from it:

| | marks paths | carries data |
|---|---|---|
| `@capture` / `@always_capture` / `@never_capture` / `CaptureMixin` (§8) | ✅ | ❌ |
| `@capture_block` / `CaptureBlockMixin` (§3c) | ❌ | ✅ |

A view that wants both stacks them:

```python
@always_capture
@capture_block(PictureBlock.download, picture_id="public_id")
def download(request, public_id): ...
```

---

## 9. Session traceability — a second, optional middleware

Deliberately *not* part of the core middleware: plenty of deployments already get this
from the platform (Cloud Run injects `X-Cloud-Trace-Context`, load balancers set
`X-Request-Id`), and plenty of projects don't want session correlation at all.

```python
MIDDLEWARE = [
    "django_wide_events.middleware.WideEventTraceMiddleware",   # must precede the core one
    "django_wide_events.middleware.WideEventMiddleware",
    ...,
]
```

It owns: sourcing the request id (trust incoming headers or not), reading `traceparent`
/ `X-Cloud-Trace-Context`, deriving `session_id` / `session_seq` / `prev_request_id`, and
setting response headers.

Interaction with the core: the core middleware always needs *an* id (the sampling hash
depends on it), so it uses the id the trace middleware set and falls back to `uuid4()`
when the trace middleware isn't installed. Nothing else in the core knows about traces.

**Detailed design deferred** — we plan this properly once the core exists.

---

## 10. Defaults policy

| Setting | Default? |
|---|---|
| `COLLECTORS` | ✅ default list when omitted; setting it **replaces**, compose with the `DEFAULTS` sentinel |
| `SAMPLING.KEEP_RULES` | ✅ same — default when omitted, `DEFAULTS` sentinel to compose |
| `SAMPLING.BASE_RATE`, `SAMPLING.SLOW_MS` | ❌ required when a filter is installed |
| `STATIC_FIELDS` | ❌ explicit |
| `EXCLUDE_PATHS` | ❌ explicit (empty = log everything) |
| `LOGGING` (formatter/filter/handler wiring) | ❌ user writes it |
| logger name / message | 🔒 fixed at `wide_events.request` / `"request"` for v1 (§14) |

Missing required settings raise `ImproperlyConfigured` at startup with a message naming
the setting, not a `KeyError` at first request.

---

## 11. Packaging

- `requires-python = ">=3.10"`, Django 4.2 LTS / 5.x / 6.x.
- Drop the `[project.scripts]` console entry point — this is a library, not a CLI.
- `example_code/` excluded from the wheel.
- Sync **and** async middleware (`ContextVar` survives `await`).

---

## 12. Deferred — database counters

`db_queries` / `db_time_ms` are worth having, but they are not a settings flag away:
`connection.queries` only populates under `DEBUG=True`, so a production-correct counter
means installing a `CursorWrapper` per connection, and that has real cost and real
multi-database / async-connection edge cases.

Decision: **park it.** Revisit once the core is working, and expect it to land as either
an explicitly-installed extra middleware or something the host project wires itself —
not as a default collector. Nothing in the core design blocks either route.

Same treatment for anything else with production-level complexity: it ships off, or it
ships as its own middleware.

---

## 13. Test environment

A throwaway Django project lives in `tests/`, wired through `pytest-django`:

```
tests/settings.py    minimal settings + a WIDE_EVENTS block mirroring this document
tests/urls.py        namespaced include, so route names look like "tests:ok"
tests/app_urls.py    the URL patterns
tests/views.py       one view per request shape: ok, health, boom, slow, 500, 403,
                     non-GET, redirect, and a picture view with a URL kwarg
tests/conftest.py    the `events` fixture and friends
```

Views are deliberately dumb — no logging of their own. If a test needs a view to say
something, that means the API under test is missing something.

Assertions go through an `events` fixture that attaches a capturing handler to the
`wide_events` logger, because that is where wide events actually come out:

```python
def test_event_carries_request_basics(client, events):
    client.get("/pictures/42/download/")

    event = events.one()              # asserts exactly one event was emitted
    assert event["route"] == "tests:picture-download"
    assert event["status_code"] == 200
```

`events` also exposes `.records` (for level and `exc_info` assertions, and for feeding
real `TailSampling` filters), `.events`, `.last` and `.clear()`. Companion fixtures:
`client_quiet` (returns the 500 instead of re-raising, for exception paths) and
`assert_json_safe` (every event must survive a JSON formatter).

`tests/test_middleware.py` is the **spec to build against**: real behavioural tests that
`importorskip` the not-yet-existing middleware, so they sit skipped today and light up
the moment the module lands. Verified against a throwaway no-op middleware — 6 of the 7
failed for the right reasons.

```bash
uv sync
uv run pytest
```

---

## 14. Roadmap — deliberately not in v1

Ship the smallest thing that is actually useful, see whether anyone else wants it, then
extend. These are designed-for, not built:

| Later | Why not now | What keeps the door open |
|---|---|---|
| **Strict/declared blocks** (§3a) | Two block flavours doubles the surface before we know the ergonomics are right | Strict subclasses `EventBlock` and constrains `.set()`; loose code keeps working |
| **Generated setters on blocks** | Only pays off once fields are declared | Falls out of strict blocks |
| **Configurable logger name / message** | Fixed `wide_events.request` / `"request"` keeps queries portable across projects, which is the point of a shared package | `WIDE_EVENTS["LOGGER_NAME"]` slots in without touching anything else |
| **Database counters** (§12) | Production complexity, see above | Extra middleware or host-project wiring |
| **Session / trace correlation** (§9) | Optional by nature, many platforms supply it | Already its own middleware |
| **Celery / management-command events** | Core first | `EventContext.source` already exists |

## Settled

- Blocks are **loose** in v1; strict is a planned subclass, not a v1 fork.
- Blocks **auto-attach** on construction and are **flushed by the middleware**, not by
  the view. No `.emit()`.
- No `request.event`. The ContextVar proxy plus `get_event()` / `Block.current()` is the
  single way in.
- Logger `wide_events.request`, message `"request"` — fixed for v1.
- Naming: the control family is `@capture` / `@always_capture` / `@never_capture`
  (+ `CaptureMixin`); the data one is `@capture_block` (+ `CaptureBlockMixin`).
- §8 decorators mark paths only — sampling and skip. They never carry field data.
- No dotted-path keys (`event["a.b"]`) — ambiguous when a real key contains a dot;
  `event.set()`, `event.update()` and blocks cover the ground.

## Still open

1. **`@capture_block` vs. plain `@capture` for blocks.** "Use capture and always_capture"
   was read as *the control family*, which pushes the block decorator to
   `@capture_block`. If you meant `@capture` to stay the block decorator, say so — then
   the control pair needs different names again.
