"""
Custom pagination for mobile-friendly responses.
"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class ManifestPagination(PageNumberPagination):
    """PageNumber pagination with meta/data response structure."""
    page_size = 20
    page_size_query_param = 'size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'meta': {
                'total_count': self.page.paginator.count,
                'current_page': self.page.number,
                'next_link': self.get_next_link(),
                'previous_link': self.get_previous_link(),
            },
            'data': data,
        })
