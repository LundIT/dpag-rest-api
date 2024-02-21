import json
from io import BytesIO

import pandas as pd
from django.http import FileResponse
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_api_key.permissions import HasAPIKey

from ProcessAdminRestApi.generic_filters import UserReadRestrictionFilterBackend, ForeignKeyFilterBackend
from ProcessAdminRestApi.model_collection.model_collection import get_relation_fields
from ProcessAdminRestApi.views.model_entries.filter_backends import PrimaryKeyListFilterBackend


class ModelExportView(GenericAPIView):
    filter_backends = [UserReadRestrictionFilterBackend, PrimaryKeyListFilterBackend, ForeignKeyFilterBackend]
    model_collection = None
    http_method_names = ['post']
    permission_classes = [HasAPIKey | IsAuthenticated]



    def post(self, request, *args, **kwargs):
        model_container = kwargs['model_container']
        model = model_container.model_class
        queryset = ForeignKeyFilterBackend().filter_queryset(request, model.objects.all(), None)
        queryset = UserReadRestrictionFilterBackend()._filter_queryset(request, queryset, model_container)
        json_data = json.loads(str(request.body, encoding='utf-8'))
        if json_data["filtered_export"] is not None:
            queryset = PrimaryKeyListFilterBackend().filter_for_export(json_data, queryset, self)

        df = pd.DataFrame.from_records(queryset.values())
        relationfields = get_relation_fields(model)

        for field in relationfields:
            fieldName = field.attname
            fieldObjects = field.remote_field.model.objects.all()
            fieldObjectsDict = {v.pk: str(v) for v in fieldObjects}
            df[fieldName] = df[fieldName].map(fieldObjectsDict)

        excel_file = BytesIO()
        writer = pd.ExcelWriter(excel_file, engine='xlsxwriter')

        df.to_excel(writer, sheet_name=model.__name__, merge_cells=False, freeze_panes=(1, 1), index=True)

        writer.save()
        writer.close()
        excel_file.seek(0)

        return FileResponse(excel_file)