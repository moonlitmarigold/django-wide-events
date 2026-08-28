from django.urls import include, path

# Namespaced include, so ``resolver_match.view_name`` looks like a real project's
# ("tests:picture-download") rather than a bare function name.
urlpatterns = [
    path("", include("tests.app_urls", namespace="tests")),
]
