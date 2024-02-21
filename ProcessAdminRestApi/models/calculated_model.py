import itertools
import math
from copy import deepcopy

from celery.result import ResultSet, allow_join_result
from django.db.models import Model, TextField, UniqueConstraint
from django.db.models.base import ModelBase

from DjangoProcessAdminGeneric import settings
def _flatten(list_2d):
    return list(itertools.chain.from_iterable(list_2d))

def calc_and_save(models, *args):
    for model in models:
        model.calculate(*args)
        try:
            model.save()
        except Exception as e:
            old_model = model.delete_models_with_same_defining_fields()
            model.pk = old_model.pk
            model.save()


class CalculatedModelMixinMeta(ModelBase):
    def __new__(cls, name, bases, attrs, **kwargs):
        if 'Meta' not in attrs:
            class Meta:
                pass

            attrs['Meta'] = Meta

        if len(attrs['defining_fields']) != 0:
            attrs['Meta'].constraints = [
                UniqueConstraint(fields=attrs['defining_fields'], name='defining_fields_' + name)
            ]

        return super().__new__(cls, name, bases, attrs, **kwargs)


class CalculatedModelMixin(Model, metaclass=CalculatedModelMixinMeta):
    input = False
    defining_fields = []
    parallelizable_fields = []

    class Meta:
        abstract = True

    def get_selected_key_list(self, key: str) -> list:
        pass

    def calculate(self):
        pass


    @classmethod
    def create(cls, *args, **kwargs):
        # define cls as base model
        models = [cls()]
        deleted = False
        # remove all the fields that are in the kwargs
        ordered_defining_fields = sorted(cls.defining_fields, key=lambda x: 0 if x in kwargs.keys() else 1)
        for field_name in ordered_defining_fields:
            field_name = field_name.__str__().split('.')[-1]
            i_temp_models = []
            # create new models from existing model by applying new selected key list
            for i, model in enumerate(models):
                if field_name in kwargs.keys():
                    selected_keys = kwargs[field_name]
                else:
                    selected_keys = model.get_selected_key_list(field_name)

                j_temp_models = [deepcopy(model) for i in range(len(selected_keys))]
                for j, fk in enumerate(selected_keys):
                    setattr(j_temp_models[j], field_name, fk)
                i_temp_models.append(j_temp_models)
            models = _flatten(i_temp_models)

            """if not deleted and field_name not in kwargs:
                for model in models:
                    keys = kwargs.keys()
                    filter_keys = {}
                    for k in keys:
                        filter_keys[k] = getattr(model, k)

                    filtered_objects = cls.objects.filter(**filter_keys)
                    filtered_objects.delete()"""

        for i in range(0, len(models)):
            model = models[i]
            model = model.delete_models_with_same_defining_fields()

            models[i] = model

        model: CalculatedModelMixin
        cluster_dict = {}
        for model in models:
            local_dict = cluster_dict
            for parallel_cluster in cls.parallelizable_fields[:-1]:
                attribute = getattr(model, parallel_cluster, None)
                if getattr(model, parallel_cluster, None) in local_dict.keys():
                    local_dict = local_dict[attribute]
                else:
                    cluster_dict[getattr(model, parallel_cluster, None)] = {}
            attribute = getattr(model, cls.parallelizable_fields[-1], None) if len(cls.parallelizable_fields)>0 else None
            if attribute in local_dict.keys():
                local_dict[attribute].append(model)
            else:
                local_dict[attribute] = [model]

        def add_to_group(local_cluster, groups):
            for k, v in local_cluster.items():
                if isinstance(v, dict):
                    groups = add_to_group(v, groups)
                else:
                    groups.append(v)
            return groups

        if settings.celery_active:
            groups = add_to_group(cluster_dict, [])
            rs = ResultSet([])
            try:
                rs.join()
                for group in groups:
                    rs.add(calc_and_save.delay(group))
                try:
                    rs.join()
                except Exception as e:
                    return
            except Exception as e:
                calc_and_save(models, *args)
        else:
            calc_and_save(models, *args)

    def delete_models_with_same_defining_fields(self):
        filter_keys = {}
        for k in self.defining_fields:
            filter_keys[k] = getattr(self, k)
        filtered_objects = type(self).objects.filter(**filter_keys)
        if filtered_objects.count() == 1:
            model = filtered_objects.first()
        elif filtered_objects.count() == 0:
            # we do not modify the list
            model = self
        else:
            raise Exception(f"More than 1 object found for {self} with {filter_keys}")
        return model