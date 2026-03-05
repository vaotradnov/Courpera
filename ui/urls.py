"""Public UI routes for Courpera (Stage 1)."""

from django.urls import path

from .views import index

urlpatterns = [
    path("", index, name="index"),
]
