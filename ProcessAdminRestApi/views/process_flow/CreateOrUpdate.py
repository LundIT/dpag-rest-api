import traceback
from datetime import datetime

from django.db.models.signals import post_save
from rest_framework.exceptions import APIException
from rest_framework.generics import RetrieveUpdateDestroyAPIView, CreateAPIView
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin

from ProcessAdminRestApi.subprocess_lib.Logger import Logger
from ProcessAdminRestApi.views.model_entries.mixins.DestroyOneWithPayloadMixin import DestroyOneWithPayloadMixin
from ProcessAdminRestApi.views.model_entries.mixins.ModelEntryProviderMixin import ModelEntryProviderMixin
from ProcessAdminRestApi.views.utils import get_user_name, get_user_email

from django.db import transaction

user_name = None
user_email = None


class CreateOrUpdate(ModelEntryProviderMixin, DestroyOneWithPayloadMixin, RetrieveUpdateDestroyAPIView, CreateAPIView):
    def update(self, request, *args, **kwargs):
        from generic_app.submodels.UserChangeLog import UserChangeLog
        from generic_app.models import update_handler
        model_container = self.kwargs['model_container']
        global user_name
        global user_email

        user_change_log = UserChangeLog(message=f"Update of a {model_container.id} started", timestamp=datetime.now(), user_name=get_user_name(request))
        user_change_log.save()
        user_name = get_user_name(request)
        user_email = get_user_email(request)
        instance = model_container.model_class.objects.filter(pk=self.kwargs["pk"]).first()
        try:
            if "next_step" in request.data:
                post_save.disconnect(update_handler)
            with transaction.atomic():
                if instance:
                    response = UpdateModelMixin.update(self, request, *args, **kwargs)
                else:
                    response = CreateModelMixin.create(self, request, *args, **kwargs)
        except Exception as e:
            user_change_log = UserChangeLog(message=f"{e}",
                                            timestamp=datetime.now(), user_name=get_user_name(request), traceback=traceback.format_exc())
            user_change_log.save()

            print(e)
            raise APIException({"error": f"{e} ", "traceback": traceback.format_exc()})

        user_change_log = UserChangeLog(message=f'Update of {model_container.id} with id {response.data["id"]} successful',
                                        timestamp=datetime.now(), user_name=get_user_name(request))
        user_change_log.save()
        post_save.connect(update_handler)
        return response
