from collections import OrderedDict

from rest_framework.response import Response

from AdminUser.pagination import ModifiedPageNumberPagination


class BroadcastPagination(ModifiedPageNumberPagination):


    def get_paginated_response(self, data,unread=None):
        response = OrderedDict([
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link())
        ])
        if unread is not None:
            response['unread_broadcasts'] = unread

        response['results'] = data
        return Response(response)
