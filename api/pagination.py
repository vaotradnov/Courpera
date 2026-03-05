from __future__ import annotations

from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    """Default pagination with client page_size and a safe cap.

    - Default page_size: 20 (matches settings)
    - Client may request `?page_size=N` up to `max_page_size`
    - Cap prevents excessive payloads during testing and demos
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
