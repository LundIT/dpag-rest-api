from rest_framework.permissions import IsAuthenticated
from rest_framework_api_key.permissions import HasAPIKey

from ProcessAdminRestApi.views.permissions.UserPermission import UserPermission


class ModelEntryProviderMixin:
    permission_classes = [HasAPIKey | IsAuthenticated, UserPermission]

    def get_queryset(self):
        return self.kwargs['model_container'].model_class.objects.all()

    def get_serializer_class(self):
        return self.kwargs['model_container'].obj_serializer