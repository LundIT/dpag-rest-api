import base64
from urllib.parse import parse_qs
from rest_framework import filters


class PrimaryKeyListFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        model_container = view.kwargs['model_container']

        if 'ids' in request.query_params.dict():
            ids = {**request.query_params}['ids']
            ids_cleaned = list(filter(lambda x: x != '', ids))
            filter_arguments = {
                f'{model_container.pk_name}__in': ids_cleaned
            }
        else:
            filter_arguments = {}
        return queryset.filter(**filter_arguments)

    def filter_for_export(self, json_data, queryset, view):
        model_container = view.kwargs['model_container']
        decoded = base64.b64decode(json_data["filtered_export"]).decode("utf-8")
        params = parse_qs(decoded)
        if 'ids' in dict(params):
            ids = dict(params)['ids']
            ids_cleaned = list(filter(lambda x: x != '', ids))
            filter_arguments = {
                f'{model_container.pk_name}__in': ids_cleaned
            }
        else:
            filter_arguments = {}
        return queryset.filter(**filter_arguments)


class UserReadRestrictionFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        model_container = view.kwargs['model_container']
        user = request.user
        modification_restriction = model_container.get_modification_restriction()

        # Hint: we do not check the general read-permission here, as this is already done by the class UserPermission

        permitted_entry_ids = [entry.id for entry in queryset if
                               modification_restriction.can_be_read(entry, user, None)]
        return queryset.filter(id__in=permitted_entry_ids)
