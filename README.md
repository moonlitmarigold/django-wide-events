# django-wide-events

<!-- one-line pitch: what it does, in a sentence -->
Implementation of Wide Events for Django
AINOTE: Maybe spice up a bit
https://loggingsucks.com/ (Reference for the project)

<!-- badges: PyPI version, Python versions, Django versions, license, CI -->
AINOTE:You do

---

## Why wide events

<!-- NOTES: the problem with scattered log lines. Keep to a short paragraph -- the -->
<!-- argument itself lives at loggingsucks.com, link it rather than restate it. -->
As explained in https://loggingsucks.com/

### Before / after

<!-- NOTES: the N-scattered-log-lines vs. one-canonical-line contrast. Probably two -->
<!-- short code blocks side by side. -->

### What one event looks like

<!-- NOTES: a real emitted JSON line. This is the single most persuasive thing in the -->
<!-- README -- decide how many fields to show (enough to look high-dimensional, few -->
<!-- enough to read at a glance). -->



---

## Install

<!-- NOTES: pip / uv line. Requirements: Python >=3.10, Django >=4.2. -->

## Quickstart

<!-- NOTES: the smallest thing that produces one JSON line per request. -->
<!-- INSTALLED_APPS + MIDDLEWARE placement (as early as possible, and why) + a minimal -->
<!-- LOGGING dict. Decide: does the package ship a LOGGING helper, or is it hand-written? -->
AINOTE: As in my tests for filters, the logging config should remain handwritten to ensure max customiability

---

## Writing to the event

<!-- NOTES: the ad-hoc path. The event lives in a ContextVar, not on `request`. -->
<!-- Say why that matters: deep service code needs no plumbing. -->

### The event API

<!-- NOTES: set / update / timer / incr, and get_event() as the escape hatch. -->
<!-- Note that writing outside an active event is a silent no-op. -->

---

## Event blocks

<!-- NOTES: the class-based path for domain data. Lead with when to reach for a block -->
<!-- instead of the ad-hoc API. -->

### Declaring a block

<!-- NOTES: namespace, named constructors, chainable enrichers. Blocks are loose -- -->
<!-- no declared fields in v1. -->

### Attaching and retrieving

<!-- NOTES: construction auto-attaches; no .emit() / .render() call. current() and the -->
<!-- flush-in-finally guarantee (nothing lost on early return or exception). -->

### Nested blocks

<!-- NOTES: parent / path, and the dotted registry key. Worth stating the rule that -->
<!-- makes it work: '.' is banned inside a namespace, so paths stay unambiguous. -->

### Attaching twice

<!-- NOTES: multiple = True for list-valued blocks; BlockAlreadyAttached for the -->
<!-- single case, and why that raises instead of merging silently. -->

### Timers

<!-- NOTES: the context-manager timer, named and nestable. -->

### The capture decorator

<!-- NOTES: @capture_block, pulling values from view kwargs; the CBV mixin. -->

---

## Collectors

<!-- NOTES: framework-level fields, keyed to the event lifecycle rather than the -->
<!-- request cycle (so commands and tasks work too). on_create / on_finish / -->
<!-- on_exception. What ships by default. -->

## Static fields

<!-- NOTES: STATIC_FIELDS -- service, env, commit, region. None values dropped. -->

## Sampling

<!-- NOTES: tail sampling as a logging.Filter. Keep rules (errors, slow, writes, -->
<!-- 401/403/429) vs. the base rate for fast successful reads. Deterministic on -->
<!-- request_id, and sample_rate recorded on the event. -->

## Formatters

<!-- NOTES: JSON, indented JSON for local dev, Google Cloud Logging. -->

## Per-view control

<!-- NOTES: opt-in / opt-out decorators, NO_LOGGING_PATHS. -->

## Session traceability

<!-- NOTES: the second, optional middleware. This is a headline feature, not a -->
<!-- footnote -- decide whether it deserves its own top-level section higher up. -->

---

## Settings reference

<!-- NOTES: the full WIDE_EVENTS dict, every key with its default. Table or annotated -->
<!-- code block -- pick one and be exhaustive; this is the section people return to. -->

## Compatibility

<!-- NOTES: supported Python and Django versions; WSGI/ASGI; thread and async safety. -->

---

## Documentation

<!-- NOTES: links out to docs/. Decide the split: how much lives in the README vs. -->
<!-- docs/EXAMPLE_USAGE.md, so the two don't drift. -->

## Status

<!-- NOTES: pre-1.0, what's stable vs. moving. Link the roadmap. -->

## Contributing

<!-- NOTES: dev setup (uv sync), running tests (uv run pytest). -->

## Prior art

<!-- NOTES: loggingsucks.com, and the canonical-log-line lineage generally. -->

## License

<!-- NOTES: name it and link LICENSE. -->
