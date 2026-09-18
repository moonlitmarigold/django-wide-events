# django-wide-events — roadmap

- Features that are designed but not built yet
- v1 ships the core: middleware, collectors, event blocks, sampling filters, formatters
- Carried over from the planning doc (`docs/EXAMPLE_USAGE.md`); section numbers below refer to it

---

## Session traceability

- A second, optional middleware: `WideEventTraceMiddleware`, placed before `WideEventMiddleware`
- Why it's separate: many platforms already supply trace ids (Cloud Run's `X-Cloud-Trace-Context`, load balancers' `X-Request-Id`), and not every project wants session correlation
- It would own:
  - Where the request id comes from (moved out of the core `RequestID` collector?)
  - Reading `traceparent` / `X-Cloud-Trace-Context`
  - Deriving `session_id`, `session_seq`, `prev_request_id`
  - Response headers
- The core still needs an id either way, because sampling hashes it
- Detailed design: still open

## Per-view control

- `@capture(sample_rate=N)`: a per-view sample rate
  - `@always_capture` becomes shorthand for `@capture(sample_rate=1)`
- `@capture` with no arguments: opt in at the base rate
- `@never_capture(reason="...")`: an opt-out with a reason, for humans reading the code
- `CaptureMixin` for class-based views, with `capture` and `capture_sample_rate`
- `WIDE_EVENTS["MODE"] = "opt-in"`: only decorated views are logged, useful when adopting the package gradually in a large project

## Event blocks

- `@capture_block` / `CaptureBlockMixin`: build and attach a block from view kwargs before the view runs

  ```python
  @capture_block(PictureBlock.download, picture_id="public_id")
  def download(request, public_id): ...
  ```

  - Carries data only; combine it with the per-view decorators to control logging
  - Open question: the name `@capture_block` vs. `@capture` (§ "Still open" in the planning doc)
- `Block.require()`: like `current()`, but raises when no block is attached
- Strict / declared blocks:
  - `fields` declared on the class, generated setters, protection against typos
  - A subclass of `EventBlock` that restricts what `.set()` accepts, so existing loose blocks keep working

## Event API shortcuts

- A module-level `event` proxy: `event.set`, `event.update`, `event.timer`, `event.incr`
- `get_event()`: returns the raw dict, or `None` outside a request
- For advanced use only; blocks stay the documented way in

## Beyond requests

- Celery: one event per task, linked back to the request that queued it
- Management commands
- Relies on collector hooks following the event lifecycle rather than the request cycle

## Database counters

- `db_queries` / `db_time_ms`
- Parked: `connection.queries` only fills when `DEBUG=True`, so production use needs a `CursorWrapper` on every connection
  - That adds overhead and edge cases with multiple databases and async connections
- Will ship as an extra middleware, or as wiring the host project adds itself, never as a default collector

## Configuration

- Configurable log message: the logger name is already the `LOGGER_NAME` setting, but the message is fixed to `"request"`
- `ImproperlyConfigured` at startup for missing or invalid settings, instead of errors on the first request

## Documentation

- "Lifecycle of a log" section in the README: request → middleware → collectors / blocks → filter → formatter → handler
- PyPI / CI badges
