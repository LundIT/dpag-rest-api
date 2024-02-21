from django_sharepoint_storage.SharePointClients import ctx
from django_sharepoint_storage.SharePointCloudStorageUtils import get_server_relative_path
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_api_key.permissions import HasAPIKey
from django.http import JsonResponse


class SharePointShareLink(APIView):
    model_collection = None
    http_method_names = ['get']
    permission_classes = [HasAPIKey | IsAuthenticated]
    def get(self, request, *args, **kwargs):
        model = kwargs['model_container'].model_class
        instance = model.objects.filter(pk=request.query_params['pk'])[0]
        file = instance.__getattribute__(request.query_params['field'])

        file = ctx.web.get_file_by_server_relative_path(get_server_relative_path(file.url)).execute_query()
        share_link = file.share_link(2).execute_query().value.sharingLinkInfo.Url

        return JsonResponse({"share_link": share_link})