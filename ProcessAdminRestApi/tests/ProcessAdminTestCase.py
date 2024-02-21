import io
import os
import inspect
import pathlib
import threading
import dateutil.parser
from django.core.cache import cache
from django.core.files import File
from django.core.files.storage import default_storage
from django.test import TestCase
from unittest import TestCase
import json
from generic_app.models import *
from pathlib import Path
class ProcessAdminTestCase(TestCase):

    def replace_tagged_parameters(self, object_parameters):
        for key in object_parameters:
            value: str = object_parameters[key]
            if isinstance(value, str):
                parsed_value = value
                if value.startswith("tag:"):
                    parsed_value = self.tagged_objects[value.replace("tag:", "")]
                elif value.startswith("datetime:"):
                    parsed_value = dateutil.parser.parse(value.replace("datetime:", ""))
                object_parameters[key] = parsed_value

        return object_parameters

    test_path = None

    def setUpCloudStorage(self) -> None:
        from datetime import datetime
        self.t0 = datetime.now()
        One.frontendId = "TestCase"
        self.tagged_objects = {}
        test_data = self.get_test_data()
        for object in test_data:
            klass = globals()[object['class']]
            action = object['action']
            tag = object['tag'] if 'tag' in object else 'instance'
            if action == 'create':
                object['parameters'] = self.replace_tagged_parameters(object['parameters'])
                self.tagged_objects[tag] = klass(**object['parameters'])
                for parameter in object['parameters'].keys():
                    if (isinstance(self.tagged_objects[tag]._meta.get_field(parameter), (FileField))):
                        upload_to = self.tagged_objects[tag]._meta.get_field(parameter).upload_to
                        if upload_to and not upload_to.endswith('/'):
                            upload_to += "/"
                        path = f"{upload_to}{os.path.basename(self.tagged_objects[tag].__dict__[parameter])}"
                        file_name = os.path.basename(self.tagged_objects[tag].__dict__[parameter])
                        f = open(f"{os.getcwd()}/generic_app/{self.tagged_objects[tag].__dict__[parameter]}", "rb")
                        file_content = f.read()
                        self.tagged_objects[tag].__dict__[parameter] = f"{upload_to}{file_name}"
                        default_storage.save(path, content=File(io.BytesIO(file_content), name=f"{file_name}"))

                cache.set(threading.get_ident(), str(object['class']) + "_" + action)
                self.tagged_objects[tag].save()
            elif action == 'update':
                object['filter_parameters'] = self.replace_tagged_parameters(object['filter_parameters'])
                self.tagged_objects[tag] = klass.objects.filter(**object['filter_parameters']).first()
                if self.tagged_objects[tag] is not None:
                    for key in object['parameters']:
                        if isinstance(self.tagged_objects[tag]._meta.get_field(key), (FileField)):
                            upload_to = self.tagged_objects[tag]._meta.get_field(key).upload_to
                            if upload_to and not upload_to.endswith('/'):
                                upload_to += "/"
                            path = f"{upload_to}{os.path.basename(object['parameters'][key])}"
                            file_name = os.path.basename(object['parameters'][key])
                            f = open(f"{os.getcwd()}/generic_app/{object['parameters'][key]}", "rb")
                            file_content = f.read()
                            default_storage.save(path, content=File(io.BytesIO(file_content), name=f"{file_name}"))
                            setattr(self.tagged_objects[tag], key, f"{upload_to}{file_name}")
                        else:
                            setattr(self.tagged_objects[tag], key, object['parameters'][key])

                    cache.set(threading.get_ident(),
                              str(object['class']) + "_" + action + "_" + str(self.tagged_objects[tag].pk))
                    self.tagged_objects[tag].save()
            elif action == 'delete':
                klass.objects.filter(**object['filter_parameters']).delete()

    def setUp(self) -> None:
        from datetime import datetime
        self.t0 = datetime.now()
        One.frontendId = "TestCase"
        self.tagged_objects = {}
        test_data = self.get_test_data()
        for object in test_data:
            klass = globals()[object['class']]
            action = object['action']
            tag = object['tag'] if 'tag' in object else 'instance'
            if action == 'create':
                object['parameters'] = self.replace_tagged_parameters(object['parameters'])
                self.tagged_objects[tag] = klass(**object['parameters'])
                cache.set(threading.get_ident(), str(object['class']) + "_" + action)
                self.tagged_objects[tag].save()
            elif action == 'update':
                object['filter_parameters'] = self.replace_tagged_parameters(object['filter_parameters'])
                self.tagged_objects[tag] = klass.objects.filter(**object['filter_parameters']).first()
                if self.tagged_objects[tag] is not None:
                    for key in object['parameters']:
                        setattr(self.tagged_objects[tag], key, object['parameters'][key])

                    cache.set(threading.get_ident(),
                              str(object['class']) + "_" + action + "_" + str(self.tagged_objects[tag].pk))
                    self.tagged_objects[tag].save()
            elif action == 'delete':
                klass.objects.filter(**object['filter_parameters']).delete()

    def tearDown(self) -> None:
        import pandas as pd
        from datetime import datetime
        pass
        # logs = pd.DataFrame.from_records(CalculationLog.objects.filter(message_type__in=["Test: Success", "Test: Error"], timestamp__gt=self.t0).values())
        # if len(logs) > 0:
        #     traces = logs['method'].str.replace("'", "").str.replace("\[", "").str.replace("\]", "").str[:-1].str[1:].str.split("\), \(", expand=True)
        #     logs = pd.concat([logs, traces], axis=1)
        #     logs.drop(columns=['id', 'method'], inplace=True)
        #     path = "generic_app/ExcelLogs/TestLogs/" + f"""TestLogs_{datetime.now().strftime("%Y-%m-%d-%H_%M_%S")}.xlsx"""
        #     logs.to_excel(path)
        #     raise Exception
        #
        # super().tearDown()

    def get_test_data(self):
        if self.test_path is None:
            file = inspect.getfile(self.__class__)
            path = Path(file).parent
            clean_test_path = str(path) + os.sep + "test_data.json"
        else:
            clean_test_path = self.test_path.replace('/', os.sep)
        test_data = self.get_test_data_from_path(clean_test_path)
        return test_data


    def get_test_data_from_path(self, path):
        with open(str(path), 'r') as f:
            test_data = json.loads(f.read())
            for index, object in enumerate(test_data):
                if "subprocess" in object:
                    subprocess_path = object['subprocess'].replace('/', os.sep)
                    sublist = self.get_test_data_from_path(subprocess_path)
                    test_data[index] = sublist
        flat_list = []
        for sublist in test_data:
            if type(sublist) == list:
                flat_list.extend(sublist)
            else:
                flat_list.append(sublist)
        return flat_list


    def get_classes(self):
        test_data = self.get_test_data()
        return set([globals()[object['class']] for object in test_data])

    def check_if_all_models_are_empty(self):
        for klass in self.get_classes():
            if klass.objects.all().count() > 0:
                return False
        return True

    def get_list_of_non_empty_models(self):
        count_of_objects_in_non_empty_models = {}
        for klass in self.get_classes():
            c = klass.objects.all().count()
            if c > 0:
                count_of_objects_in_non_empty_models[str(klass)]=c
        return count_of_objects_in_non_empty_models
