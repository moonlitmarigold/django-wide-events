# django-wide-events

## What this project is

A reusable Django package that makes it easy to adopt the **wide event** (canonical
log line) pattern described at <https://loggingsucks.com/>.

Instead of scattering many log statements through a request, the app builds up **one**
rich, structured event per request and emits it once at the end.

## The pattern (from loggingsucks.com)

- **One event per request per service.** ~13 scattered log lines collapse into a single
  structured record emitted when request handling finishes.
- **Log what happened to the request, not what the code is doing.**
- **High cardinality / high dimensionality.** 50+ fields are fine and desirable —
  user attributes, business metrics, timings, error detail — so the log store can be
  queried like an analytics dataset rather than grepped as a debugging diary.
- **Build throughout, emit once.** Initialise the event early, enrich it as the request
  flows through middleware/views/services, emit it in a `finally` block.
- **Tail sampling.** Always keep errors, slow requests, writes, and security-relevant
  statuses; sample fast successful reads at a low rate to control cost.

Typical field categories: request metadata (timestamp, request_id, trace_id, service,
version, env, commit, region), HTTP (method, path, route, status, duration_ms), user
context (id, tier, account age), business data, performance counters (query count, cache
hits), error info (type, message, stack).

## Design constraints (from the project owner)

1. **Adapt to Django's logging system, do not replace it.** Everything must plug into
   `settings.LOGGING` via standard `logging` primitives — Formatters, Filters, Handlers
   — plus Django middleware. No custom logging pipeline, no monkey-patching stdlib
   logging.
2. **Support tracebacks via sessions.** Events must be correlatable across a user
   session, not just within a single request, so a trace can be followed from one
   request to the next.
3. Ship as an installable Django package (`pip install django-wide-events`), configured
   through Django settings, usable with minimal boilerplate in a host project.

## Reference implementation in this repo

`example_code/` holds the hand-rolled version this package generalises. It is reference
material, not part of the package:

- `example_code/logging.py`
  - `JSONFormatter` / `IndentJSONFormatter` — render `record.event` as JSON (indented
    variant for local dev readability); merge in `exc_info` as an `error` object.
  - `LoggingMiddleware` — creates `request.event` with request_id, timestamps, method,
    path, env, commit; fills in route/status/duration/user_id; emits exactly one
    `logger.info("request", extra={"event": ...})` (or `.error`) in a `finally` block;
    sets the `X-Request-Id` response header; skips paths in `settings.NO_LOGGING_PATHS`;
    `process_exception` records error type/message/stack onto the event.
  - `TailSampling(logging.Filter)` — keeps everything that is an error, 5xx, missing
    status, slow (`slow_ms`), non-GET/HEAD, or 401/403/429; otherwise deterministically
    samples on a SHA1 hash of `request_id` at `base_rate`, and records `sample_rate` on
    the event.
- `example_code/logging_settings.py` — the `LOGGING` dict wiring formatter + filter +
  stdout handler, choosing the indented formatter in dev.
- `example_code/picture_log.py` — `SimplePictureLog`, a dataclass with named
  constructors (`own`, `raw`, `upload`, `download`) and chainable enrichers
  (`form_valid`, `is_public`, `is_owner`, `thumbnail`) that `render(request)` onto
  `request.event['picture']`. Shows the intended ergonomics for domain-specific
  enrichment from views.

## Layout

- `src/django_wide_events/` — the package (currently a stub).
- `example_code/` — reference implementation, excluded from the distribution.
- Python >= 3.13, built with `uv_build`.

## Status

Planning stage. Nothing of the package itself is implemented yet.
