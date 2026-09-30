DEFAULT_TASK_COLLECTORS = [
    "django_wide_events.tasks.collectors.builtin.TaskIdentity",
    "django_wide_events.tasks.collectors.builtin.Timing",
    "django_wide_events.tasks.collectors.builtin.QueueWait",
    "django_wide_events.tasks.collectors.builtin.Attempt",
    "django_wide_events.tasks.collectors.builtin.Status",
    "django_wide_events.tasks.collectors.builtin.Error",
    "django_wide_events.tasks.collectors.builtin.StaticFields",
    "django_wide_events.tasks.collectors.builtin.EnqueuedInCaller",
]
