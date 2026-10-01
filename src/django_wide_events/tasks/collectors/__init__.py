# Overridable through WIDE_EVENTS["TASK"]["TASK_COLLECTORS"]; the builtin task
# collectors (identity, timing, status, error, static fields) always run first.
DEFAULT_TASK_COLLECTORS = [
    "django_wide_events.tasks.collectors.defaults.QueueWait",
    "django_wide_events.tasks.collectors.defaults.Attempt",
    "django_wide_events.tasks.collectors.defaults.EnqueuedInCaller",
]
