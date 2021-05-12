from rest_framework.pagination import PageNumberPagination

#needs to become common
class ModifiedPageNumberPagination(PageNumberPagination):

    def get_paginated_response(self,data):
        #Adds a serial number to each entry
        current_page = self.request.query_params.get('page',1)
        current_page = int(current_page)

        offset = (current_page-1) * self.page_size
        for serial,item in enumerate(data,1):
            item['index'] = offset+serial

        return super().get_paginated_response(data)
