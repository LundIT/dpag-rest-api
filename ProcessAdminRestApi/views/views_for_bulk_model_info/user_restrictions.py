from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_api_key.permissions import HasAPIKey

from ProcessAdminRestApi.model_collection.model_collection import ModelCollection


class ModelWiseUserRestrictionsObtainView(APIView):
    http_method_names = ['get']
    model_collection: ModelCollection = None
    permission_classes = [HasAPIKey | IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        all_model_restrictions = {model_container.id: model_container.get_general_modification_restrictions_for_user(user) for
                                  model_container in self.model_collection.all_containers}

        print(all_model_restrictions)

        return Response(all_model_restrictions)
