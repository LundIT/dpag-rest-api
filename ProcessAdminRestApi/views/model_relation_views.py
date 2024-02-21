from contextlib import suppress
import copy
from typing import Dict

from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_api_key.permissions import HasAPIKey

from ProcessAdminRestApi.model_collection.model_collection import ModelCollection


class ModelStructureObtainView(APIView):
    http_method_names = ['get']
    model_collection = None
    permission_classes = [HasAPIKey | IsAuthenticated]

    def delete_restricted_nodes_from_model_structure(self, model_structure, user):
        """credit to MSeifert
        https://stackoverflow.com/questions/3405715/elegant-way-to-remove-fields-from-nested-dictionaries"""
        nodes = list(model_structure.keys())
        for n in nodes:
            if 'children' not in model_structure[n]:
                container = self.model_collection.get_container(n)
                if not container.get_general_modification_restrictions_for_user(user)['can_read_in_general']:
                    del model_structure[n]

        for subTree in model_structure.values():
            if 'children' in subTree:
                self.delete_restricted_nodes_from_model_structure(subTree['children'], user)

    def get(self, request, *args, **kwargs):
        user = request.user
        user_dependet_model_structure = copy.deepcopy(self.model_collection.model_structure_with_readable_names)
        self.delete_restricted_nodes_from_model_structure(user_dependet_model_structure, user)
        return Response(user_dependet_model_structure)


class ModelStylingObtainView(APIView):
    http_method_names = ['get']
    model_collection: ModelCollection = None
    permission_classes = [HasAPIKey | IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        user_dependent_model_styling = self.model_collection.model_styling.copy()
        for key in user_dependent_model_styling.keys():
            # FIXME remove try-catch
            try:
                container = self.model_collection.get_container(key).model_class

                if hasattr(container, 'modification_restriction'):  # FIXME change these ugly calls of hasattr
                    # FIXME: this is only set if there is an entry in @user_dependent_model_styling for the model
                    #   if this is not the case (which mostly holds), then the restrictions are not transfered to the
                    #   frontend --> fix this via own route for modification_restriction (which is better anyway)
                    user_dependent_model_styling[key][
                        'can_read_in_general'] = container.modification_restriction.can_read_in_general(user,
                                                                                                        violations=None)
                    user_dependent_model_styling[key][
                        'can_modify_in_general'] = container.modification_restriction.can_modify_in_general(user,
                                                                                                            violations=None)
                    user_dependent_model_styling[key][
                        'can_create_in_general'] = container.modification_restriction.can_create_in_general(user,
                                                                                                            violations=None)
            except KeyError:
                # happens if key not in container
                pass

        return Response(user_dependent_model_styling)


class GlobalFilterObtainView(APIView):
    http_method_names = ['get']
    model_collection: ModelCollection = None

    def get(self, request, *args, **kwargs):
        user = request.user
        global_filter_structure = self.model_collection.global_filters.copy()
        return Response(global_filter_structure)


class Overview(APIView):
    http_method_names = ['get']
    HTML_reports = None

    def get(self, request, *args, **kwargs):
        user = request.user
        class_name = kwargs['report_name']
        html_report_class = self.HTML_reports[class_name]
        html = html_report_class().get_html(user)
        return Response(html)

class ProcessStructure(APIView):
    http_method_names = ['get']
    processes = None

    def get(self, request, *args, **kwargs):
        class_name = kwargs['process_name']
        process_class = self.processes[class_name]
        process_structure = process_class().get_structure()
        return Response(process_structure)
