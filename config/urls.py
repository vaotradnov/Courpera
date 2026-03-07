"""URL routing for Courpera (Stage 1 — scaffold).

Defines admin and the base UI index route. API and documentation routes
will be added in subsequent stages.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path

from config.health import healthz, readyz
from config.metrics import metrics


def _favicon(request):  # inline SVG favicon to avoid 404s in tests/dev
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><rect width="16" height="16" fill="#0056D2"/></svg>'
    return HttpResponse(svg, content_type="image/svg+xml")


urlpatterns = [
    path("favicon.ico", _favicon),
    path("healthz", healthz),
    path("readyz", readyz),
    path("metrics", metrics),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("courses/", include("courses.urls")),
    path("materials/", include("materials.urls")),
    path("assignments/", include("assignments.urls")),
    path("activity/", include("activity.urls")),
    path("messaging/", include("messaging.urls")),
    path("discussions/", include("discussions.urls")),
    path("", include("ui.urls")),  # public index
    # API schema and docs
    path("", include("api.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
