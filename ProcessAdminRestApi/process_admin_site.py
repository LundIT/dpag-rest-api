from django.db.models.base import ModelBase
from django.db.models.signals import post_save
from django.http import HttpResponse
from django.urls import path, register_converter
from rest_framework_simplejwt.views import TokenRefreshView

from ProcessAdminRestApi.auth import TokenObtainPairWithUserView
from ProcessAdminRestApi.calculated_model_updates.objects_to_recalculate_store import ObjectsToRecalculateStore
from ProcessAdminRestApi.calculated_model_updates.update_handler import CalculatedModelUpdateHandler
from ProcessAdminRestApi.model_collection.model_collection import ModelCollection
from ProcessAdminRestApi.models.calculated_model import CalculatedModelMixin
from ProcessAdminRestApi.models.model_process_admin import ModelProcessAdmin
from ProcessAdminRestApi.views.file_operations.FileDownload import FileDownloadView
from ProcessAdminRestApi.views.file_operations.ModelExport import ModelExportView
from ProcessAdminRestApi.views.sharepoint.SharePointFileDownload import SharePointFileDownload
from ProcessAdminRestApi.views.sharepoint.SharePointPreview import SharePointPreview
from ProcessAdminRestApi.views.sharepoint.SharePointShareLink import SharePointShareLink
from ProcessAdminRestApi.signals import do_post_save

from ProcessAdminRestApi.views.model_info.Fields import Fields
from ProcessAdminRestApi.views.model_info.Widgets import Widgets
from ProcessAdminRestApi.views.model_relation_views import ModelStructureObtainView, Overview, ProcessStructure
from ProcessAdminRestApi.views.model_entries.List import ListModelEntries
from ProcessAdminRestApi.views.model_entries.Many import ManyModelEntries
from ProcessAdminRestApi.views.model_entries.One import OneModelEntry
from ProcessAdminRestApi.views.permissions.ModelPermissions import ModelPermissions
from ProcessAdminRestApi.views.process_flow.CreateOrUpdate import CreateOrUpdate
from ProcessAdminRestApi.views.project_info.ProjectInfo import ProjectInfo

from ProcessAdminRestApi import converters
from ProcessAdminRestApi.views.global_search_for_models.Search import Search

class ProcessAdminSite:
    """
    Used as instance, i.e. inheriting this class is not necessary in order to use it.
    """
    name = 'process_admin_rest_api'

    def __init__(self) -> None:
        super().__init__()

        self.registered_models = {}  # Model-classes to ModelProcessAdmin-instances
        self.model_structure = {}
        self.model_styling = {}
        self.global_filter = {}
        self.global_filter_structure = {}
        self.html_reports = {}
        self.processes = {}

        self.initialized = False
        self.model_collection = None

        # Instantiating singleton classes
        CalculatedModelUpdateHandler()
        ObjectsToRecalculateStore()

    def register_model_styling(self, model_styling):
        """
        :param model_styling: dict that contains styling parameters for each model
        """
        self.model_styling = model_styling

    def register_global_filter_structure(self, global_filter_structure):
        """
        :param global_filter_structure: dict that contains information which models are affected by the global filtering
        """
        self.global_filter_structure = global_filter_structure

    def registerHTMLReport(self, name, report):
        self.html_reports[name] = report

    def registerProcess(self, name, process):
        self.processes[name] = process

    def register_model_structure(self, model_structure):
        """
        :param model_structure: multiple trees that structure the registered models, i.e. the leaves of the trees
        must correspond to the model-names, and all other nodes are interpreted as model categories.
        The roots have a special meaning, i.e. their categorization should be the most general one,
        and is represented in a special way.
        E.g.:
        {
            'Main_1': {
                'Sub_1_1': {
                    'Model_1_1_1': None,
                    'Model_1_1_2': None
                }
            },
            'Main2': {
                'Sub_2_1': {
                    'Model_2_1_1': None,
                    'Model_2_1_2': None
                },
                'Sub_2_2': {
                    'Model_2_2_1': None,
                    'Model_2_2_2': None
                }
            }
        }
        Hint: not every model has to be contained in this tree
        :return:
        """
        self.model_structure = model_structure

    def register(self, model_or_iterable, process_admin=None):
        if process_admin is None:
            process_admin = ModelProcessAdmin()

        if isinstance(model_or_iterable, ModelBase):
            model_or_iterable = [model_or_iterable]

        for model in model_or_iterable:
            if model in self.registered_models:
                raise Exception('Model %s already registered' % model._meta.model_name)
            else:
                self.registered_models[model] = process_admin
                # TODO why was this in here in the first place?
                # if not issubclass(model, CalculatedModelMixin):
                post_save.connect(do_post_save, sender=model)

    def create_model_objects(self, request):
        for model in self.registered_models:
            if issubclass(model, CalculatedModelMixin):
                model.create()
        return HttpResponse("Created")

    def _get_urls(self):
        register_converter(converters.create_model_converter(self.model_collection), 'model')

        urlpatterns = [
            path('api/model-structure', ModelStructureObtainView.as_view(model_collection=self.model_collection),
                 name='model-structure'),
            path('api/auth/token/', TokenObtainPairWithUserView.as_view(), name='token'),
            path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='refresh_token'),
            path('api/<model:model_container>/file-download',
                 FileDownloadView.as_view(model_collection=self.model_collection), name='file-download'),
            path('api/<model:model_container>/export',
                 ModelExportView.as_view(model_collection=self.model_collection), name='model-export'),
            path('api/htmlreport/<str:report_name>',
                 Overview.as_view(HTML_reports=self.html_reports), name='htmlreports'),
            path('api/process/<str:process_name>',
                 ProcessStructure.as_view(processes=self.processes), name='process'),
        ]

        url_patterns_for_react_admin = [
            path('api/model_entries/<model:model_container>/list', ListModelEntries.as_view(),
                 name='model-entries-list'),
            path('api/model_entries/<model:model_container>/<str:calculationId>/one/<int:pk>', OneModelEntry.as_view(),
                 name='model-one-entry-read-update-delete'),
            path('api/model_entries/<model:model_container>/<str:calculationId>/one', OneModelEntry.as_view(), name='model-one-entry-create'),
            path('api/run_step/<model:model_container>/<str:pk>', CreateOrUpdate.as_view(),
                 name='run_step'),
            path('api/model_entries/<model:model_container>/many', ManyModelEntries.as_view(),
                 name='model-many-entries'),
            path('api/global-search/<str:query>', Search.as_view(model_collection=self.model_collection),
                 name='global-search'),
            path('api/<model:model_container>/model-permissions', ModelPermissions.as_view(), name='model-restrictions'),
            path('api/project-info', ProjectInfo.as_view(),
                 name='project-info'),
            path('api/widget_structure', Widgets.as_view(), name='widget-structure'),
        ]

        url_patterns_for_model_info = [
            path('api/model_info/<model:model_container>/fields', Fields.as_view(), name='model-info-fields'),
        ]

        url_patterns_for_sharepoint = [
            path('api/<model:model_container>/sharepoint-file-download', SharePointFileDownload.as_view(), name='sharepoint-file-download'),
            path('api/<model:model_container>/sharepoint-file-share-link', SharePointShareLink.as_view(),
                 name='sharepoint-file-share-link'),
            path('api/<model:model_container>/sharepoint-file-preview-link', SharePointPreview.as_view(),
                 name='sharepoint-file-preview-link'),
        ]

        return urlpatterns + url_patterns_for_react_admin + url_patterns_for_model_info + url_patterns_for_sharepoint

    @property
    def urls(self):
        # TODO: Move this to a logically more appropriate place
        # TODO: remove tree induction
        if not self.initialized:
            self.model_collection = ModelCollection(self.registered_models, self.model_structure,
                                                    self.model_styling, self.global_filter_structure)
            CalculatedModelUpdateHandler.instance.set_model_collection(self.model_collection)
            self.initialized = True

        return self._get_urls(), 'process_admin', self.name  # TODO: what is the name exactly for??
