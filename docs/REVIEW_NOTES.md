# Review notes — event blocks

> Snapshot: 2026-09-14, working tree on `main` (uncommitted). Suite at the time:
> **50 passed, 1 failed** (the one failure is pre-existing and unrelated, see P3-7).
> Every finding below was reproduced against the tree, not read off the page.

## Rating

| | |
|---|---|
| **Design** | Strong. The instincts are right nearly everywhere. |
| **Execution** | Mixed. One whole subsystem is wired up but never runs. |

The block registry — `ContextBlock`, `_attach`, the `from_kwargs` de-dup, `current()` —
is **entirely inert**. Every piece of it is written, and none of it executes, because
`_blocks` is never initialised. The view-level behaviour looks correct only because all
block state happens to live in the event dict, so identity never mattered *yet*. It will
matter the moment a block holds instance state.

Worth saying plainly: the parts that are good are good for real reasons. `ContextEvent` /
`ContextBlock` splitting off a shared `BaseContext`, `abstract=True` as a class keyword,
`ClassVar` for the class-level options, `merge` living in `context.py` instead of in each
block, and `_Timer` as a separate handle closing over a save callback — that last one is
a genuinely nice bit of design, and it's what makes named, nestable, concurrent timers
fall out for free.

---

## P1 — blocking: the block registry never runs

### P1-1. `_blocks` is never initialised

`middleware/wide_event_middleware.py:96` calls `ContextEvent.init()` and nothing else.
`ContextBlock.init()` is never called anywhere, so `_blocks` stays `None` for the whole
request, and `ContextBlock.get()` (`context.py:58-63`) hands back a fresh throwaway `{}`
on every call.

Reproduced:

```
_blocks after ContextEvent.init(): None
registry contents: {}
current() is b   : False
```

Consequences, all live right now:

- `_attach()` writes into a dict that is discarded immediately.
- `from_kwargs`'s "return the already-attached block" branch (`Base.py:47-51`) can never
  be taken.
- `current()` never finds anything and always falls through to `cls()`.

### P1-2. `BaseContext.init()` / `drop()` are hardcoded to `_current`

`context.py:12-22` operates on `_current` regardless of which subclass you call it on.
So `ContextBlock.init()` doesn't initialise `_blocks` — it **replaces the event dict**:

```
same event dict after ContextBlock.init(): False
_blocks still: None
```

That is the trap waiting behind P1-1: the obvious fix ("just call `ContextBlock.init()`
in the middleware") silently destroys the event instead.

The base class needs to know which ContextVar it owns — a `ClassVar` holding the var,
set per subclass, with `init`/`drop` going through it. Then `ContextBlock` gets correct
`init`/`drop` for free, which is what the inheritance was for in the first place.

### P1-3. `drop()` never resets `_blocks`

`context.py:12-17` resets only `_current`. Once P1-1/P1-2 are fixed this becomes a
**cross-request data leak**: WSGI reuses worker threads, so an unreset registry hands
one request's blocks to whatever request lands on that worker next. This is the single
thing in the whole design that corrupts data silently rather than failing loudly —
`docs/project-structure.md` step 1 already flags it ("Reset discipline").

Fix both vars in one `drop()`, so there is no way to reset one and forget the other.

### P1-4. `current()` constructs and attaches on miss

`Base.py:54-61` returns `cls()` when the namespace isn't found. Three problems:

- It returns a **new object every call**, so instance state (`_Timer`, anything added
  later) is lost. Verified: `current() returned a NEW object: True`.
- Construction runs `__post_init__` → `_attach()`, so a *read* mutates the registry.
  A lookup should never have side effects.
- It contradicts `docs/EXAMPLE_USAGE.md` §3b, which specifies `current()` → the attached
  block **or `None`**, with `require()` as the raising variant. Outside a request you
  currently get a happily-usable object that writes into the void.

`current()` should be a pure lookup returning `None`; add `require()` raising a
`BlockNotAttached`. An `isinstance(found, cls)` guard is worth it too, so two classes
sharing a namespace don't hand you each other's block.

### P1-5. `_attach` overwrites for `multiple = False`

`ContextBlock.set` (`context.py:65-73`) does `ctx[key] = value` on the non-list path, so
a second block on the same namespace **replaces** the first in the registry. §3b says a
second attach merges into the first and `current()` stays unambiguous. `setdefault` is
the one-word fix — first wins, later constructions merge into it.

---

## P2 — correctness papercuts

- **P2-1 `context.py:5`** — `_blocks` is declared with the name `"django_wide_events.event"`,
  the same name as `_current`. Functionally harmless (the name is only for `repr`), but
  every debugger, traceback and log line will show two different vars under one name.
  It also reads like a copy-paste that was never finished, which is exactly what P1-1 is.
- **P2-2 `Base.py:25-31`** — the namespace check only tests `is None`. A non-string
  namespace reaches `"." in namespace` and dies as
  `TypeError: argument of type 'int' is not iterable`. Add an `isinstance(ns, str)` test
  so the error names the actual problem.
- **P2-3 `Base.py:27`** — the message interpolates `cls.namespace`, which is `None` at
  exactly this point, so it reads `None must define a 'namespace'`. Use `cls.__name__`.
  The check is right and fires at import time, which is the valuable part; only the
  message is wrong.
- **P2-4 `Base.py:19-20`** — `super().__init_subclass__()` drops `**kwargs`. Pass them
  through, or any future class keyword (or cooperating mixin) breaks here.
- **P2-5 `TimerEventBlock.py:22`** — `if not self.timer_start` is a falsy test on a
  float. `perf_counter()` realistically never returns `0.0`, so it isn't live, but
  `is None` is what's meant.
- **P2-6 `TimerEventBlock.py:28-29`** — `__enter__` returns `None`, so
  `with block.timer("s3") as t:` binds `t = None`. `return self`.
- **P2-7 `context.py:45`** — `ctx[key] = ContextEvent.merge(new, **value)` assigns back
  the same object `new` already is; harmless but reads as if it might rebind. Separately,
  `**value` requires string keys, so `{1: "a"}` raises `TypeError` at the call site
  rather than at format time. Passing the dict positionally avoids both.
- **P2-8 `context.py:27-35`** — `set()` is shallow (`dict.update`) and `update()` is a
  deep merge. Those names lead the reader the wrong way, and
  `docs/EXAMPLE_USAGE.md` §2 documents `update()` as taking a **dict**, not `**kwargs`.
  Pick one story and make the docs and code agree.

---

## P3 — conventions, tests, hygiene

- **P3-1** `tests/test_event_blocks.py:10` is `assert True` under a name that promises a
  block test. It passes unconditionally. It's also the only thing exercising the block
  path, so the whole feature is currently untested.
- **P3-2** `tests/event_block_view.py:20,23` sleep `1` second each — 2 seconds added to
  every suite run for timings nothing asserts on. `0.01` proves the same thing.
- **P3-3** `tests/event_block_view.py` carries `is_flase` (for `is_false`) in two places.
  Worth keeping as the exhibit for the validation discussion: a typo'd field name doesn't
  error, it silently becomes a second column in the log store and splits every query
  against the real field from then on. That — not type coercion — is what declared
  fields would buy.
- **P3-4** A class named `TestBlock` is a pytest collection hazard. It's safe today only
  because `event_block_view.py` doesn't match `test_*.py`. If that file is ever renamed
  or the pattern widened, pytest tries to collect it and warns about `__init__`.
  `SampleBlock` / `DemoBlock` avoids the whole question.
- **P3-5** Module names matching class names (`TimerEventBlock.py` → `TimerEventBlock`)
  caused a real import failure earlier: `from django_wide_events.event_blocks import
  TimerEventBlock` silently bound the **module** and took down the URLconf and 23 tests.
  The explicit re-export in `__init__.py` masks it now, but the collision is still there,
  and `collectors/` and `filter/` share the pattern. PEP 8 wants lowercase modules;
  either way, don't let a module and a class share a name.
- **P3-6** `@dataclass` on `TimerEventBlock` (`TimerEventBlock.py:35`) adds nothing — the
  class declares no fields. Harmless, but it implies state that isn't there.
- **P3-7** `tests/test_config.py:8` expects `STRICT_COLLECTORS`, absent from
  `config.py:9` `DEFAULTS` → the one suite failure. Pre-existing, unrelated to blocks.
  `docs/EXAMPLE_USAGE.md` §5 specifies it (re-raise collector errors in dev); `run_hook`
  currently always swallows. Either implement it or drop the test.

---

## Still unbuilt (design decided, code absent)

- **Flush.** Blocks write straight into the event dict on `set()`, so they work without a
  flush step — but that means `drop_none` (§3a), `multiple = True` rendering as a list,
  and `redact` have nowhere to happen. Whether to keep write-through or move to
  attach-then-render at emit time is the next real design decision.
- **Middleware integration.** Nothing in the middleware knows blocks exist.
- **`all()`** for `multiple = True` — `current()` returning the latest is useless for
  reading back a list.
- **Base-class options** discussed but not started: `drop_none`, `incr()`, `redact`,
  declared `fields`.

---

## Suggested order next session

1. Give `BaseContext` its ContextVar as a `ClassVar` (P1-2), then init **and** drop both
   vars from one place in the middleware (P1-1, P1-3). Nothing else works until this does.
2. Make `current()` a pure lookup returning `None`, add `require()` (P1-4), and switch
   `_attach` to `setdefault` (P1-5).
3. Write a real `tests/test_event_blocks.py` — assert `current() is block`, that two
   timers coexist, and that block state does **not** leak between two sequential requests.
   That last one is the test that would have caught P1-3.
4. Mop up P2.
