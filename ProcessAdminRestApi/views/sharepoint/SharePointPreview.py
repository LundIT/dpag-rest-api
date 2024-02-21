from django_sharepoint_storage.SharePointClients import ctx
from django_sharepoint_storage.SharePointCloudStorageUtils import get_server_relative_path
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_api_key.permissions import HasAPIKey
import os
from django.http import JsonResponse


class SharePointPreview(APIView):
    model_collection = None
    http_method_names = ['get']
    permission_classes = [HasAPIKey | IsAuthenticated]
    def get(self, request, *args, **kwargs):
        model = kwargs['model_container'].model_class
        instance = model.objects.filter(pk=request.query_params['pk'])[0]
        file = instance.__getattribute__(request.query_params['field'])

        file = ctx.web.get_file_by_server_relative_path(get_server_relative_path(file.url)).get().execute_query()
        preview_link = str(os.getenv('FILE_PREVIEW_LINK_BASE')) + "sourcedoc={" +file.unique_id +"}&action=embedview"



        return JsonResponse({"preview_link": preview_link})