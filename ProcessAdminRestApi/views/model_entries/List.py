import traceback
from math import inf

from django.db.models import FloatField, IntegerField, DateField, DateTimeField, TextField, AutoField
from django_filters import FilterSet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import APIException
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination

from ProcessAdminRestApi.models.upload_model import IsCalculatedField, CalculateField
from ProcessAdminRestApi.views.model_entries.filter_backends import UserReadRestrictionFilterBackend
from ProcessAdminRestApi.views.model_entries.mixins.ModelEntryProviderMixin import ModelEntryProviderMixin

INTERVAL_REQUIRING_FIELDS = {FloatField, IntegerField, DateField, DateTimeField}
CALCULATION_FIELDS = {IsCalculatedField, CalculateField}

class CustomPageNumberPagination(PageNumberPagination):
    page_query_param = 'page'
    page_size_query_param = 'perPage'
    def paginate_queryset(self, queryset, request, view=None):
        if request.query_params["perPage"] == -1:
            self.page_size = queryset.count()  # Set the page size equal to the total number of objects in the queryset

        return super().paginate_queryset(queryset, request, view)

class ListModelEntries(ModelEntryProviderMixin, ListAPIView):
    pagination_class = CustomPageNumberPagination
    # see https://stackoverflow.com/a/40585846
    # We use the UserReadRestrictionFilterBackend for filtering out those instances that the user
    #   does not have access to
    filter_backends = [UserReadRestrictionFilterBackend, DjangoFilterBackend, OrderingFilter]

    def get_lookup_expressions(self, field_type):
        if field_type in INTERVAL_REQUIRING_FIELDS:
            if field_type in [DateField, DateTimeField]:
                return ['exact', 'lte', 'gte', 'year', 'month', 'day']
            return ['exact', 'lte', 'gte']
        if field_type in [TextField, AutoField]:
            return ['exact', 'icontains']
        return ['exact']

    @property
    def filterset_fields(self):
        # we need to only take those fields where a django-filter exists
        try:
            return_fields = {f.name: self.get_lookup_expressions(type(f)) for f in
                    self.kwargs['model_container'].model_class._meta.fields if (type(f) in FilterSet.FILTER_DEFAULTS or type(f) in CALCULATION_FIELDS)}
            return return_fields
        except Exception as e:
            raise APIException({"error": f"Filter fields could not be generated!", "traceback": traceback.format_exc()})