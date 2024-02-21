import json
import logging
import traceback
from datetime import datetime

from django.db.models import FileField, ImageField
from django.db.models.fields import *
from django.db.models.fields.related import ForeignKey
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import ListAPIView, CreateAPIView, UpdateAPIView, DestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# TODO: also: diese Views am besten durch Django Generic bumms ersetzen, dabei auch Pagination und filtering verwenden
#       (filtern zuerst nach denen, die der User sehen darf, und dann nach dem gesetzten Filter)
# TODO: Permissions einfügen, und zwar grundsätzliche und Objekt-spezifische wie vom User definiert
# TODO: der Serializer muss außerdem beim Read von Model-Info und Objekten die Permissions mitgeben
# TODO: beim Erstellen eines neues Objekts (was btw optisch von der Tabelle getrennt wird) bekommt das Frontend
#   die Nachricht, auf welcher Seite das neue Objekt gelandet ist
# TODO: auch User-definierte Sortierung nach Spalten wird dann leichter; prinzipiell wird nach Anwendung neuer
#   Sortierung wieder auf die erste Seite gesprungen
# TODO: hilfreich: Django SearchFilter --> kann automatisch Textsuche auf bestimmten Feldern durchführen
# TODO: folgende Entscheidungen müssen wir treffen:
#   - wenn der Filter verändert wird, soll dann einfach
#       zu Seite 1 gesprungen oder auf der aktuellen Seite verblieben werden (oder falls diese nicht mehr
#       existiert, weil nicht mehr so viele Elemente übrig bleiben, auf die letzte Seite geprungen werden)?
#
from rest_framework_api_key.permissions import HasAPIKey

from ProcessAdminRestApi.generic_filters import ForeignKeyFilterBackend, \
    PrimaryKeyListFilterBackend, StringFilterBackend
from ProcessAdminRestApi.models.fields.Bokeh_field import BokehField
from ProcessAdminRestApi.models.fields.HTML_field import HTMLField
from ProcessAdminRestApi.models.fields.PDF_field import PDFField
from ProcessAdminRestApi.models.fields.XLSX_field import XLSXField
from ProcessAdminRestApi.models.upload_model import CalculateField, IsCalculatedField
from ProcessAdminRestApi.serializers import model2serializer
from ProcessAdminRestApi.views.pagination import CustomPageNumberPagination, CustomLimitOffsetPagination
from ProcessAdminRestApi.views.model_entries.filter_backends import UserReadRestrictionFilterBackend
from generic_app.submodels.UserChangeLog import UserChangeLog

user_change_log = logging.getLogger("user_change_log")


class ModelIdListView(ListAPIView):
    filter_backends = [UserReadRestrictionFilterBackend, ForeignKeyFilterBackend, StringFilterBackend]
    pagination_class = None
    permission_classes = [HasAPIKey | IsAuthenticated]

    # TODO: add permission functionality that throws exception if @can_read_in_general fails for user

    def get_queryset(self):
        model_container = self.kwargs['model_container']
        return model_container.model_class.objects.all().order_by('-pk')  # TODO: also allow custom ordering //

    def get_serializer_class(self):
        model_container = self.kwargs['model_container']
        return model2serializer(model_container.model_class, ['pk'])


class ModelIdListViewWithPageNumberPagination(ModelIdListView):
    pagination_class = CustomPageNumberPagination


class ModelIdListViewWithLimitOffsetPagination(ModelIdListView):
    pagination_class = CustomLimitOffsetPagination


class ModelPagingInfoView(ListAPIView):
    filter_backends = [UserReadRestrictionFilterBackend, ForeignKeyFilterBackend, StringFilterBackend]
    permission_classes = [HasAPIKey | IsAuthenticated]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._info_types = {
            'number_instances': lambda model_container: self.filter_queryset(self.get_queryset()).count(),
        }

    def get_queryset(self):
        model_container = self.kwargs['model_container']
        return model_container.model_class.objects.all()

    def get(self, request, *args, **kwargs):
        model_container = kwargs['model_container']
        info_type = kwargs['info']
        info = self._info_types[info_type](model_container)
        result = {info_type: info}
        return Response(result)


class PrimaryKeyFilterView(ListAPIView):
    filter_backends = [ForeignKeyFilterBackend]
    permission_classes = [HasAPIKey | IsAuthenticated]

    def get_queryset(self):
        # FIXME: can this be replaced by another filter backend before the current one??
        model_container = self.kwargs['model_container']
        all_selected_pks = json.loads(self.request.GET.get('allSelectedPks'))
        return model_container.model_class.objects.filter(pk__in=all_selected_pks)

    def get(self, request, *args, **kwargs):
        qs = self.get_queryset()
        filtered_qs = self.filter_queryset(qs)
        result = {'results': {i.pk: filtered_qs.filter(pk=i.pk).exists() for i in qs}}
        return Response(result)


# TODO: Do authentication properly
class ModelInstancesListView(ListAPIView):
    filter_backends = [PrimaryKeyListFilterBackend, UserReadRestrictionFilterBackend]
    permission_classes = [HasAPIKey | IsAuthenticated]

    def get_queryset(self):
        return self.kwargs['model_container'].model_class.objects.all()

    def get_serializer_class(self):
        return self.kwargs['model_container'].obj_serializer

def get_user_name(request):
    user_name = f"{request.auth['name']} ({request.auth['sub']})"
    return user_name


class ModelInstanceCreateView(CreateAPIView):
    permission_classes = [HasAPIKey | IsAuthenticated]

    def create(self, request, *args, **kwargs):
        model_class = self.kwargs['model_container'].model_class
        model_class_name = str(model_class).split(".")[-1][:-2]
        violations = []
        if not hasattr(model_class,
                       'modification_restriction') or model_class.modification_restriction.can_create_in_general(
            self.request.user, violations=violations):
            try:
                response = super(ModelInstanceCreateView, self).create(request, *args, **kwargs)
            except Exception as e:
                log = UserChangeLog(user_name=get_user_name(request), timestamp=datetime.now(),
                                    message=f"""Creation of a {model_class_name} Failed ({e})""")
                log.save()
                raise ValidationError()

            log = UserChangeLog(user_name=get_user_name(request), timestamp=datetime.now(),
                                message=f"""Creation of {model_class_name} with id {response.data['id']} successful""")
            log.save()
            return response
        raise PermissionDenied()

    def get_serializer_class(self):
        return self.kwargs['model_container'].obj_serializer


class ModelInstanceUpdateView(UpdateAPIView, DestroyAPIView):
    # permission_classes = (IsAuthenticated,)
    permission_classes = [HasAPIKey | IsAuthenticated]

    def update(self, request, *args, **kwargs):
        model_class = self.kwargs['model_container'].model_class
        model_class_name = str(model_class).split(".")[-1][:-2]
        model_instance = model_class.objects.get(pk=self.kwargs['pk'])
        violations = []
        if not hasattr(model_class,
                       'modification_restriction') or model_class.modification_restriction.can_modify_in_general(
            self.request.user, violations=violations):
            if not hasattr(model_class,
                           'modification_restriction') or model_instance.modification_restriction.can_be_modified(
                model_instance, self.request.user, violations):
                try:
                    response = super(ModelInstanceUpdateView, self).update(request, *args, **kwargs)
                except Exception as e:
                    print(traceback.print_exc())
                    log = UserChangeLog(user_name=get_user_name(request), timestamp=datetime.now(),
                                        message=f"""Update {model_class_name} {model_instance} Failed ({e})""")
                    log.save()
                    raise ValidationError()
                log = UserChangeLog(user_name=get_user_name(request), timestamp=datetime.now(),
                                    message=f"""Update {model_class_name} {model_instance} successful""")
                log.save()
                return response
        raise PermissionDenied()

    def delete(self, request, *args, **kwargs):
        model_class = self.kwargs['model_container'].model_class
        model_class_name = str(model_class).split(".")[-1][:-2]
        model_instance = model_class.objects.get(pk=self.kwargs['pk'])
        violations = []
        if not hasattr(model_class,
                       'modification_restriction') or model_class.modification_restriction.can_modify_in_general(
            self.request.user, violations=violations):
            if not hasattr(model_class,
                           'modification_restriction') or model_instance.modification_restriction.can_be_modified(
                model_instance, self.request.user, violations):
                try:
                    response = self.destroy(request, *args, **kwargs)
                except Exception as e:
                    log = UserChangeLog(user_name=get_user_name(request), timestamp=datetime.now(),
                                        message=f"""Deleting {model_class_name} {model_instance} Failed ({e})""")
                    log.save()
                    raise ValidationError()

                log = UserChangeLog(user_name=get_user_name(request), timestamp=datetime.now(),
                                    message=f"""Deleting {model_class_name} {model_instance} successful""")
                log.save()
                return response
        raise PermissionDenied()

    def get_queryset(self):
        return self.kwargs['model_container'].model_class.objects.all()

    # def perform_update(self, serializer):
    #    model_class_name = str(self.kwargs['model_container'].model_class).split(".")[-1][:-2]
    #    model_name = self.kwargs['model_container'].model_class.objects.get(pk=self.kwargs['pk'])
    #    user_change_log.info(f"""Updated {model_class_name} {model_name}""", extra={'user': self.request.user})
    #    try:
    #        super(ModelInstanceUpdateView, self).perform_update(serializer=serializer)
    #    except:
    #        log = UserChangeLog(user_name=self.request.user, message=f"""Update {model_class_name} {model_name} Failed""")
    #        log.save()
    #    finally:
    #        log = UserChangeLog(user_name=self.request.user, message=f"""Update {model_class_name} {model_name} successful""")
    #        log.save()
    def get_serializer_class(self):
        return self.kwargs['model_container'].obj_serializer


# TODO: Do authentication properly
class ModelFieldInfoRequestHandlerView(APIView):
    http_method_names = ['get']
    permission_classes = [HasAPIKey | IsAuthenticated]

    def get(self, request, *args, **kwargs):
        model_container = kwargs['model_container']
        model = model_container.model_class
        fields = model._meta.fields
        field_info = {'fields': [], 'pk': model._meta.pk.name, 'fks': [], 'not_required_fields': [], 'defaults': {}}
        for field in fields:
            name = field.name

            # FIXME: also send an array containing only those fields that should be presented in the table
            #   to the frontend. This is configured in the model-process-admin-class for the model (which can
            #   be accessed via the model_container) --> The idea is, that the table only shows the main fields
            #   but avoids unnecessary information

            # FIXME: why does the backend send a different JSON-structure here than the frontend requires, so that
            # in the frontend the structure has to be transformed?? Why not just sending the same as in the frontend
            # and simply copy the received data in the frontend??

            # Hint: the field's blank-property is the only property that should be used to derive if a user has to
            # specify a value for this field when creating an instance. All other possible ways
            # (like using whether a default is given) are not meant to be used for this (see Django docs).
            if field.blank:
                field_info['not_required_fields'].append(name)

            if field.get_default() is not None:
                field_info['defaults'][name] = field.get_default()
                field_info['not_required_fields'].append(name)

            if type(field) == ForeignKey:
                field_info['fks'].append({
                    'name': name,
                    'target': field.target_field.model._meta.model_name
                })
                field_info['fields'].append({
                    'name': name,
                    'type': 'ForeignKey'
                })
            elif type(field) == IntegerField:
                field_info['fields'].append({
                    'name': name,
                    'type': 'Integer'
                })
            elif type(field) == FloatField:
                field_info['fields'].append({
                    'name': name,
                    'type': 'Float'
                })
            elif type(field) == BooleanField:
                field_info['fields'].append({
                    'name': name,
                    'type': 'Boolean'
                })
            elif type(field) == DateField:
                field_info['fields'].append({
                    'name': name,
                    'type': 'Date'
                })
            elif type(field) == DateTimeField:
                field_info['fields'].append({
                    'name': name,
                    'type': 'DateTime'
                })
            elif type(field) == FileField:
                field_info['fields'].append({
                    'name': name,
                    'type': 'File'
                })
            elif type(field) == PDFField:
                field_info['fields'].append({
                    'name': name,
                    'type': 'Pdf'
                }),
            elif type(field) == XLSXField:
                field_info['fields'].append({
                    'name': name,
                    'type': 'Xlsx'
                })
            elif type(field) == HTMLField:
                field_info['fields'].append({
                    'name': name,
                    'type': 'Html'
                })
            elif type(field) == BokehField:
                field_info['fields'].append({
                    'name': name,
                    'type': 'Bokeh'
                })
            elif type(field) == ImageField:
                field_info['fields'].append({
                    'name': name,
                    'type': 'ImageFile'
                })
            elif type(field) == BooleanField:
                field_info['fields'].append({
                    'name': name,
                    'type': 'Boolean'
                })
            elif type(field) == CalculateField:
                field_info['fields'].append({
                    'name': name,
                    'type': 'CalculateAction'
                })
            elif type(field) == IsCalculatedField:
                field_info['fields'].append({
                    'name': name,
                    'type': 'CalculatedStatus'
                })
            else:
                field_info['fields'].append({
                    'name': name,
                    'type': 'String'
                })
        return Response(field_info)
