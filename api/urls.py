"""API routes for Courpera (Stage 2).

Exposes OpenAPI schema and interactive documentation. Versioned REST
endpoints will be added in subsequent stages under /api/v1/.
"""

from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter

from .views import (
    CourseViewSet,
    EnrolmentViewSet,
    FeedbackViewSet,
    MaterialViewSet,
    StatusViewSet,
    UserViewSet,
    search_users,
)

router = DefaultRouter()
router.register(r"api/v1/users", UserViewSet, basename="users")
router.register(r"api/v1/courses", CourseViewSet, basename="courses")
router.register(r"api/v1/enrolments", EnrolmentViewSet, basename="enrolments")
router.register(r"api/v1/materials", MaterialViewSet, basename="materials")
router.register(r"api/v1/feedback", FeedbackViewSet, basename="feedback")
router.register(r"api/v1/status", StatusViewSet, basename="status")


class UnthrottledSpectacularAPIView(SpectacularAPIView):
    throttle_classes: list = []


urlpatterns = [
    path("api/schema/", UnthrottledSpectacularAPIView.as_view(), name="schema"),
    # Use custom templates without inline JS/CSS to satisfy CSP
    path(
        "docs/",
        SpectacularSwaggerView.as_view(url_name="schema", template_name="api/swagger_ui.html"),
        name="swagger-ui",
    ),
    path(
        "redoc/",
        SpectacularRedocView.as_view(url_name="schema", template_name="api/redoc.html"),
        name="redoc",
    ),
    path("api/v1/search/users", search_users, name="search-users"),
    path("", include(router.urls)),
]
