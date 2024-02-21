from rest_framework import serializers, viewsets


class RestApiModelSerializerTemplate(serializers.ModelSerializer):
    short_description = serializers.SerializerMethodField()

    def get_short_description(self, obj):
        return str(obj)

    class Meta:
        model = None
        fields = "__all__"


class RestApiModelViewSetTemplate(viewsets.ModelViewSet):
    queryset = None
    serializer_class = None


ID_FIELD_NAME = 'id_field'
SHORT_DESCR_NAME = 'short_description'


def model2serializer(model, fields=None):
    if fields is None:
        fields = [field.name for field in model._meta.fields]

    serialized_pk_name = serializers.ReadOnlyField(default=model._meta.pk.name)
    fields.append(ID_FIELD_NAME)
    fields.append(SHORT_DESCR_NAME)

    return type(
        model._meta.model_name + 'Serializer',
        (RestApiModelSerializerTemplate,),
        {
            # the primary-key field is always mapped to a field with name id, as the frontend requires it
            ID_FIELD_NAME: serialized_pk_name,
            'Meta': type(
                'Meta',
                (RestApiModelSerializerTemplate.Meta,),
                {
                    'model': model,
                    'fields': fields
                }
            )
        }
    )
