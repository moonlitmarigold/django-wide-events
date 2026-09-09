"""URLconf for the middleware tests.

Exercised through ``django.test.Client`` so the middleware runs inside
Django's real handler stack: ``convert_exception_to_response`` turns view
exceptions into responses, and ``resolver_match`` is populated so
``apply_route`` has something to read.
"""

from django.http import Http404, HttpResponse
from django.urls import path


def ok_view(request):
    return HttpResponse("ok")


def status_523_view(request):
    """A 5xx without an exception - error log level, no ``error`` payload."""
    return HttpResponse(status=523)


def not_found_view(request):
    raise Http404


def boom_view(request):
    raise ValueError("boom")


urlpatterns = [
    path("", ok_view, name="ok"),
    path("523/", status_523_view, name="status-523"),
    path("404/", not_found_view, name="not-found"),
    path("boom/", boom_view, name="boom"),
]
