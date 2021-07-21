from collections import OrderedDict

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class EnhancedPagination(PageNumberPagination):

    def get_paginated_response(self, data,**kwargs):

        response = OrderedDict([
            ('count', self.page.paginator.count),
            ('currentPage',self.page.number),
            ('totalPages', self.page.paginator.num_pages),

        ])
        
        for key,value in kwargs.items():
            if value is not None:
                response[key] = value

        #Inserts an index (relative to the page number)
        index = range(self.page.start_index(), self.page.end_index()+1)
        for index,item in zip(index,data):
            item['index'] = index

        response['results'] = data
        return Response(response)
