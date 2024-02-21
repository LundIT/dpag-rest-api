from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_api_key.permissions import HasAPIKey

from ProcessAdminRestApi.views.permissions.UserPermission import UserPermission
from django.http import JsonResponse
from generic_app import models

class Widgets(APIView):
    http_method_names = ['get']
    permission_classes = [HasAPIKey | IsAuthenticated]

    def get(self, *args, **kwargs):
        return JsonResponse({"widget_structure": models.widget_structure})
