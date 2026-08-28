"""Views covering the request shapes the package has to handle.

Kept deliberately dumb: no logging calls of their own. Everything the wide event
knows about a request should come from middleware, collectors and blocks — if a test
needs a view to say something, that is a sign the API under test is missing.
"""

import time

from django.http import HttpResponse, JsonResponse


def ok(request):
    return HttpResponse("ok")


def health(request):
    """Matches settings.WIDE_EVENTS["EXCLUDE_PATHS"] — should never be logged."""
    return HttpResponse("healthy")


def boom(request):
    raise ValueError("kaboom")


def slow(request):
    """Sleeps past a low SLOW_MS so tail sampling's keep-slow rule fires."""
    time.sleep(float(request.GET.get("seconds", "0.05")))
    return HttpResponse("eventually")


def server_error(request):
    return HttpResponse("nope", status=500)


def forbidden(request):
    return HttpResponse("no", status=403)


def echo(request):
    """Non-GET traffic, for the keep-writes rule."""
    return JsonResponse({"method": request.method}, status=201)


def picture_download(request, public_id: int):
    """Stand-in for the picture views the block API is modelled on."""
    return HttpResponse(f"picture {public_id}")


def redirect_ish(request):
    return HttpResponse(status=302, headers={"Location": "/ok/"})
