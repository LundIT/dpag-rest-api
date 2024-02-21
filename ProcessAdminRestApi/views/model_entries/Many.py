from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from ProcessAdminRestApi.views.model_entries.filter_backends import PrimaryKeyListFilterBackend
from ProcessAdminRestApi.views.model_entries.mixins.ModelEntryProviderMixin import ModelEntryProviderMixin


class ManyModelEntries(ModelEntryProviderMixin, GenericAPIView):
    filter_backends = [PrimaryKeyListFilterBackend]

    def get_filtered_query_set(self):
        filtered_qs = self.filter_queryset(self.get_queryset())
        # we check user-permissions object-wise; our permission class UserPermission automatically
        #   differentiates between read - and modify-restrictions, depending on the http-method
        for entry in filtered_qs:
            self.check_object_permissions(self.request, entry)
        return filtered_qs

    def get(self, request, *args, **kwargs):
        queryset = self.get_filtered_query_set()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        queryset = self.get_filtered_query_set()
        serializer = self.get_serializer(queryset, data=request.data, partial=True, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        pk_name = self.kwargs['model_container'].pk_name
        return Response([d[pk_name] for d in serializer.data])

    def delete(self, request, *args, **kwargs):
        queryset = self.get_filtered_query_set()
        ids = list(queryset.values_list('pk', flat=True))
        queryset.delete()
        return Response(ids)
