from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_api_key.permissions import HasAPIKey


class ShortDescriptionRequestHandlerView(APIView):
    # TODO: also use ListAPIView here with filter_backends and serializer (which uses to_display_string)
    http_method_names = ['get']
    permission_classes = [HasAPIKey | IsAuthenticated]

    def get(self, request, *args, **kwargs):
        model_container = kwargs['model_container']
        filter_arguments = {
            model_container.pk_name + '__in':
                list(filter(lambda x: x != '', request.query_params.dict()['pks'].split(',')))
        } if 'pks' in request.query_params.dict() else {}
        objects = model_container.model_class.objects.filter(**filter_arguments)
        data = {obj.pk: model_container.process_admin.to_display_string(obj) for obj in list(objects)}
        return Response(data)
