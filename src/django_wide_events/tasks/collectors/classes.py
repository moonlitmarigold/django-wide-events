from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class TaskInfo:

    task_id:int
    name:str
    framework:str
    backend:str
    queue:str
    priority:str
    enqueued_at:datetime | None
    attempt:int
    worker:str | None

@dataclass(frozen=True)
class TaskResult:

    status:str
    exception:Exception