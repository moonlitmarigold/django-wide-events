# django-wide-events

![Static Badge](https://img.shields.io/badge/github-repo-blue?logo=github)


One rich, structured log line per request, instead of a dozen scattered ones.

`django-wide-events` brings the *wide event* (or *canonical log line*) pattern to Django. It is built on Django's own `logging`, so it drops into the `LOGGING` config you already have instead of replacing it. The pattern is described in detail at <https://loggingsucks.com/>.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-3776AB?logo=python&logoColor=white)](https://github.com/moonlitmarigold/django-wide-events/blob/main/pyproject.toml)
[![Django](https://img.shields.io/badge/django-4.2%20%7C%205.2%20%7C%206.0-092E20?logo=django&logoColor=white)](https://github.com/moonlitmarigold/django-wide-events/blob/main/pyproject.toml)
[![License](https://img.shields.io/github/license/moonlitmarigold/django-wide-events)](https://github.com/moonlitmarigold/django-wide-events/blob/main/LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-orange)](https://github.com/moonlitmarigold/django-wide-events/blob/main/docs/ROADMAP.md)

<!-- badges to add later: PyPI version (after first release), CI (once a workflow exists) -->

---

## Table of contents

1. [Why wide events](#-why-wide-events)
   1. [How is this different from django-structlog?](#how-is-this-different-from-django-structlog)
   2. [What one event looks like](#what-one-event-looks-like)
2. [Install](#-install)
3. [Quickstart](#-quickstart)
4. [Lifecycle of a log in this project](#-lifecycle-of-a-log-in-this-project)
5. [Event blocks](#-event-blocks)
   1. [Example](#example)
   2. [Rules](#rules)
6. [Collectors](#-collectors)
   1. [Example](#example-1)
7. [Static fields](#-static-fields)
8. [Sampling](#-sampling)
9. [Formatters](#-formatters)
10. [Per-view control](#-per-view-control)
11. [Settings reference](#-settings-reference)
12. [Compatibility](#-compatibility)
13. [Design philosophy](#-design-philosophy)
14. [Documentation](#-documentation)
15. [Status](#-status)
16. [Contributing](#-contributing)
17. [Prior art](#-prior-art)
18. [License](#-license)

---

## 💡 Why wide events

Scattered log lines describe what the *code* did. A wide event describes what happened to the *request*. Instead of a dozen `logger.info(...)` calls spread over middleware, views and services, each request builds up one structured record as it runs and emits it once when it finishes.

That record is meant to be wide: user context, route, status, timings and your own domain data all sit side by side. With many fields per event, your logs can be queried like an analytics table ("slow downloads by paid users, grouped by route") instead of grepped line by line. The full argument is at <https://loggingsucks.com/>.

### How is this different from django-structlog?

  [django-structlog](https://github.com/jrobichaud/django-structlog) adds request
  context (request id, user, IP) to every log line you write, and logs
  `request_started` / `request_finished` itself. It makes scattered logs easier to
  correlate.

  django-wide-events replaces the scattered lines with one event per request that
  you build up as the request runs. On top of that it adds:

  - **Tail sampling** as a standard `logging.Filter`: errors, slow requests and writes are always kept, the rest
  sampled
  - **Namespaced event blocks** for nested, domain-specific fields and timers
  - **No extra logging framework**: just Django and stdlib `logging`

### What one event looks like

```json
{
  "loglevel": "INFO",
  "message": "request",
  "logger": "wide_events.request",
  "timestamp": 1789650000.123,
  "service": "shop",
  "env": "prod",
  "request_id": "9f1c2e...",
  "meta": {"method": "GET", "timezone": "UTC", "timestamp": "2026-09-17T10:00:00.000+00:00"},
  "user": {"id": 42, "username": "ada", "is_authenticated": true, "is_staff": false},
  "picture": {"id": "abc", "is_owner": true, "timers": {"s3_fetch_ms": 12.4}},
  "route": "pictures:download",
  "status_code": 200,
  "duration_ms": 48.31,
  "sample_rate": 10
}
```

Framework fields (`route`, `status_code`, `duration_ms`, `user`) sit next to your own domain data (`picture`).

---

## 📦 Install

- `pip install django-wide-events` / `uv add django-wide-events`
- Requires Python >= 3.10 and Django >= 4.2

## 🚀 Quickstart

- Add the middleware to `MIDDLEWARE`, as early as possible, so the event covers (and times) the rest of the stack
  - No `INSTALLED_APPS` entry needed

  ```python
  MIDDLEWARE = [
      "django_wide_events.middleware.WideEventMiddleware",
      # ... the rest of your middleware
  ]
  ```

- Write the `LOGGING` config yourself; the package deliberately ships no helper, so you keep full control over handlers, formatters and filters
  - Minimal setup: a formatter, a sampling filter and a stdout handler on the `wide_events.request` logger

  ```python
  LOGGING = {
      "version": 1,
      "disable_existing_loggers": False,
      "formatters": {
          "wide": {
              "()": "django_wide_events.formatters.JSONFORMATTER",
          },
      },
      "filters": {
          "sampling": {
              "()": "django_wide_events.filter.TailSampling",
              "base_rate": 10,
          },
      },
      "handlers": {
          "stdout": {
              "class": "logging.StreamHandler",
              "formatter": "wide",
              "filters": ["sampling"],
          },
      },
      "loggers": {
          "wide_events.request": {
              "handlers": ["stdout"],
              "level": "INFO",
              "propagate": False,
          },
      },
  }
  ```

- Result: one JSON line per request
- For readable output during local development, indent it:

  ```python
  "formatters": {
      "wide": {
          "()": "django_wide_events.formatters.JSONFORMATTER",
          "indent": True,
      },
  },
  ```

- The split of responsibilities:
  - The middleware collects the data and emits the event once
  - Formatters decide what the line looks like
  - Filters decide whether it's kept

---

## 🔄 Lifecycle of a log in this project

![Lifecycle of a log](https://raw.githubusercontent.com/moonlitmarigold/django-wide-events/main/docs/request_cycle.svg)

Each step is explained in detail in [docs/INTERNALS.md](https://github.com/moonlitmarigold/django-wide-events/blob/main/docs/INTERNALS.md).

---

## 🧱 Event blocks

- Blocks are **the intended way to write to the event**
- A block is a class with a `namespace`; everything it writes lands under that key in the event
- Blocks are stateless: the class holds no data
  - Every `set(...)` goes straight into the current request's event
  - `Block.current()` finds the attached block again from anywhere in the request
- The middleware writes everything the blocks collected to the log at the end of the request, including after an early return or an exception
- There's nothing to emit or render yourself

### Example

```python
from django.http import HttpResponse
from django_wide_events.event_blocks import EventBlock, TimerEventBlock


class PictureBlock(TimerEventBlock):
    namespace = "picture"

    @classmethod
    def download(cls, picture_id):
        return cls.from_kwargs(action="download", id=picture_id)

    def owner(self, is_owner):
        return self.set(is_owner=is_owner)


class StorageBlock(EventBlock):
    namespace = "storage"
    parent = PictureBlock                   # nests under event["picture"]


def download(request, picture_id):
    PictureBlock.download(picture_id)       # attaches to this request's event
    fetch_file(picture_id)
    return HttpResponse("ok")


def fetch_file(picture_id):
    block = PictureBlock.current()          # no request object needed
    block.owner(True).set(caption=None)     # chainable; None is dropped
    with block.timer("s3_fetch"):
        ...
    StorageBlock(kwargs={"bucket": "pictures"})
```

- Resulting event (only the block part shown):

  ```json
  {
    "picture": {
      "action": "download",
      "id": "abc",
      "is_owner": true,
      "timers": {"s3_fetch_ms": 10.07},
      "storage": {"bucket": "pictures"}
    }
  }
  ```

### Rules

- `namespace` is required (or `abstract=True` for base classes), and can't contain `.`
- `from_kwargs(...)` reuses the attached block; constructing the same block twice raises `BlockAlreadyAttached`
- `multiple = True`: each instance is kept as a list entry; `current()` returns the latest
- `parent = OtherBlock` nests the block; the parent can't be abstract or `multiple`
- `TimerEventBlock.timer(name)` works as a context manager or via `start_timer()` / `stop_timer()`, and writes `timers.<name>_ms`
- Class flags: `drop_none`, `append_list`, `use_namespace_on_write`
- Advanced: the raw event API behind the blocks is described in [docs/INTERNALS.md](https://github.com/moonlitmarigold/django-wide-events/blob/main/docs/INTERNALS.md)

---

## 🪝 Collectors

- Collectors add framework-level fields at fixed points in the event's lifecycle: `on_create`, `on_exception`, `on_finish`, `on_finish_no_response`
- A collector only runs for the hooks it overrides
- A collector that raises never breaks the request; the error is recorded under `hook_error.hook_errors`
- Collectors are stateful: anything stored in `__init__` or `on_create` is still there for the later hooks
- A fresh set of collectors is created at the start of every request
- Built-in and default collectors: see [docs/INTERNALS.md](https://github.com/moonlitmarigold/django-wide-events/blob/main/docs/INTERNALS.md#collectors-reference)

### Example

- Record which picture was requested, and whether it was served:

  ```python
  # myapp/collectors.py
  from django_wide_events.collectors import Collector


  class RequestedPicture(Collector):

      def __init__(self):
          self.picture_id = None

      def on_create(self, request):
          # resolver_match isn't set yet in on_create; read the raw path instead
          parts = request.path.strip("/").split("/")
          if len(parts) >= 2 and parts[0] == "pictures":
              self.picture_id = parts[1]
              self.set(picture={"id": self.picture_id})

      def on_finish(self, request, response):
          if self.picture_id is not None:
              self.set(picture={"served": response.status_code == 200})

      def on_exception(self, request, exception):
          if self.picture_id is not None:
              self.set(picture={"failed": True})
  ```

- Register it next to the defaults; setting `COLLECTORS` replaces the list, so keep `DEFAULT_COLLECTORS` in it:

  ```python
  # settings.py
  from django_wide_events.collectors import DEFAULT_COLLECTORS

  WIDE_EVENTS = {
      "COLLECTORS": [
          *DEFAULT_COLLECTORS,
          "myapp.collectors.RequestedPicture",
      ],
  }
  ```

## 📌 Static fields

- `STATIC_FIELDS`: fixed fields written on every event, e.g. `service`, `env`, `commit`, `region`
- `None` values are dropped

  ```python
  WIDE_EVENTS = {
      "STATIC_FIELDS": {
          "service": "shop",
          "env": os.environ.get("ENV"),
          "commit": os.environ.get("GIT_SHA"),
      },
  }
  ```

## 🎲 Sampling

- Sampling is a standard `logging.Filter`, so it's configured in `LOGGING`
- `TailSampling` keeps every event that matches a rule, and 1 in `base_rate` of the rest:

  ```python
  "filters": {
      "sampling": {
          "()": "django_wide_events.filter.TailSampling",
          "base_rate": 20,      # 1 = keep all, 0 = drop everything no rule keeps
      },
  },
  ```

- Default rules: errors, 5xx / no status, slow (>= 1000 ms), non-GET/HEAD, 401/403/429
- The decision is deterministic per `request_id`
- Events sampled at the base rate carry `sample_rate`, so counts can be scaled back up
- Custom rules replace the defaults; keep `DEFAULT_RULES` in the list to extend them instead:

  ```python
  from django_wide_events.filter.rules import DEFAULT_RULES, BaseRule


  class PaidUser(BaseRule):
      def keep(self, record, event):
          return self.lookup(event, "user.tier") == "paid"


  "sampling": {
      "()": "django_wide_events.filter.TailSampling",
      "base_rate": 20,
      "keep_rules": [*DEFAULT_RULES, PaidUser()],
  },
  ```

- Built-in rules take options, e.g. `SlowRequest(slow_ms=500)`, when you list them yourself
- `RandomSampling` takes the same arguments but has no rules

## 🎨 Formatters

- `JSONFORMATTER` writes the event as one JSON line; any `exc_info` becomes `error.{type, stack}`
- `GoogleFormatter` does the same, using a `severity` field for Google Cloud Logging
- A common setup: indented output in dev, one line in prod:

  ```python
  "formatters": {
      "wide": {
          "()": "django_wide_events.formatters.JSONFORMATTER",
          "indent": DEBUG,
      },
      "gcp": {
          "()": "django_wide_events.formatters.GoogleFormatter",
      },
  },
  ```

---

## 🎛️ Per-view control

- Decorators mark individual views; they never add data:

  ```python
  from django_wide_events.decorators import always_capture, never_capture


  @always_capture          # kept even when sampling would drop it
  def checkout(request): ...


  @never_capture           # dropped by the sampling filter
  def poll(request): ...


  class PictureDetail(DetailView):
      capture = True       # the class-based form
  ```

  - The decorators take effect in the sampling filter, so they need `TailSampling` or `RandomSampling` installed

- `NO_LOGGING_PATHS` skips path prefixes entirely: no event is created and no collectors run

  ```python
  WIDE_EVENTS = {
      "NO_LOGGING_PATHS": ["/static/", "/media/", "/health", "/metrics"],
  }
  ```

- Use settings for URL prefixes you never want logged; use decorators for views you own

---

## ⚙️ Settings reference

- All settings live in one `WIDE_EVENTS` dict:

  | Key | Default | Notes |
  |---|---|---|
  | `COLLECTORS` | `DEFAULT_COLLECTORS` (`User`, `MetaData`) | dotted paths; setting it **replaces** the list; built-ins always run |
  | `STATIC_FIELDS` | `{}` | merged into every event |
  | `LOGGER_NAME` | `"wide_events.request"` | the logger your `LOGGING` config should target |
  | `NO_LOGGING_PATHS` | `[]` | path prefixes skipped entirely |
  | `REQUEST_ID.TRUST_ID_HEADER` | `True` | `True`: always reuse an incoming `X-Request-Id`; `False`: always generate a new id |
  | `REQUEST_ID.RESPONSE_HEADER` | `"X-Request-Id"` | name of the response header that carries the id; falsy = don't set it |
  | `REQUEST_ID.ID_GENERATOR` | uuid4 hex | callable returning a new id |

- `REQUEST_ID` is merged key by key with the defaults; the other keys are replaced whole
- Sampling settings are passed to the filter in `LOGGING`

## ✅ Compatibility

`django-wide-events` supports Python 3.10 and newer with Django 4.2 LTS and 5.x, under both WSGI and ASGI.

The event lives in a `ContextVar`, so it follows the request wherever Python copies the context: views and code run through `sync_to_async` or `asyncio.to_thread` all write to the same event.

**One caveat: manual threads.** A thread started with `threading.Thread(...)` or a bare `ThreadPoolExecutor.submit(...)` begins with an empty context, so anything it writes is silently lost. Run such code inside `contextvars.copy_context().run(...)` to give it access to the request's event.

---

## 🧭 Design philosophy

The package is built to be modular. Each part does one job: the middleware collects, collectors and blocks supply fields, filters decide what's kept, and formatters decide how it looks. Every part plugs into Django's standard middleware and `logging` machinery rather than working around it.

Nearly everything can be customised. When the settings don't cover your case, subclass the part in question (the middleware, a collector, a sampling filter or rule, a formatter) and override only the behaviour you need.

## 📚 Documentation

This README is the usage reference. For what happens under the hood (the context variables, event blocks, collectors and middleware) read [docs/INTERNALS.md](https://github.com/moonlitmarigold/django-wide-events/blob/main/docs/INTERNALS.md). Planned features that aren't built yet are collected in [docs/ROADMAP.md](https://github.com/moonlitmarigold/django-wide-events/blob/main/docs/ROADMAP.md). `docs/EXAMPLE_USAGE.md` served as the planning document and is retired now that these files cover it.

## 🚧 Status

The project is pre-1.0 (`0.1.0`). Event blocks, collector hooks and the filter and formatter wiring are considered stable; setting names may still change before 1.0. See [docs/ROADMAP.md](https://github.com/moonlitmarigold/django-wide-events/blob/main/docs/ROADMAP.md) for what comes next.

## 🤝 Contributing

- `uv sync`
- `uv run pytest`
- The tests use a small Django project in `tests/`

## 🔍 Prior art

The pattern comes from <https://loggingsucks.com/>, which builds on Stripe's "canonical log lines" and the wide events popularised by Honeycomb and the observability-2.0 movement.

## 📄 License

GPL-3.0. See [LICENSE](https://github.com/moonlitmarigold/django-wide-events/blob/main/LICENSE).
