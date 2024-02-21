import os
from io import BytesIO

from django.http import FileResponse, JsonResponse
from django_sharepoint_storage.SharePointClients import ctx
from django_sharepoint_storage.SharePointCloudStorageUtils import get_server_relative_path
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_api_key.permissions import HasAPIKey



class FileDownloadView(APIView):
    model_collection = None
    http_method_names = ['get']
    permission_classes = [HasAPIKey | IsAuthenticated]

    def get(self, request, *args, **kwargs):
        model = kwargs['model_container'].model_class
        instance = model.objects.filter(pk=request.query_params['pk'])[0]
        file = instance.__getattribute__(request.query_params['field'])

        if os.getenv("KUBERNETES_ENGINE", "NONE") == "NONE":
            file_url = file.url

        if os.getenv("STORAGE_TYPE") == "SHAREPOINT":
            file = ctx.web.get_file_by_server_relative_path(get_server_relative_path(file.url)).execute_query()
            binary_file = file.open_binary(ctx, get_server_relative_path(file_url))
            bytesio_object = BytesIO(binary_file.content)
            return FileResponse(bytesio_object)
        elif os.getenv("STORAGE_TYPE") == "GCS":
            return JsonResponse({"download_url": file_url})
        else:
            return FileResponse(open(file_url, 'rb'))