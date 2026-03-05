from django.contrib import admin

from .models import Material


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "uploaded_by", "size_bytes", "created_at")
    search_fields = ("title", "course__title", "uploaded_by__username")
