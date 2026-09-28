"""Tasks for the task wide event tests.

Django resolves a task by its module path, so they live at module level here
rather than inside the test module."""

from django.tasks import task
from django_wide_events.event_blocks import EventBlock


class InvoiceBlock(EventBlock):

    namespace = "invoice"


@task
def send_invoice(invoice_id):
    # enriched from inside the task body, the same way a view enriches a request event
    InvoiceBlock.from_kwargs(invoice_id=invoice_id, sent=True)
    return invoice_id


@task
def failing_task():
    raise ValueError("task boom")
