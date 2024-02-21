from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_api_key.permissions import HasAPIKey


class ModelQuickAccessConfigObtainView(APIView):
    http_method_names = ['get']
    model_collection = None
    permission_classes = [HasAPIKey | IsAuthenticated]

    def get(self, request, *args, **kwargs):
        res = {
            c.id: {
                'allow_quick_instance_creation': c.process_admin.allow_quick_instance_creation(c.model_class)
            }
            for c in self.model_collection.all_containers
        }
        return Response(res)
