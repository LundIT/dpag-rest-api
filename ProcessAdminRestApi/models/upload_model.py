import os
import threading
import uuid
from functools import wraps

from celery import shared_task, Task
from celery.app.control import Control
from celery.signals import task_failure, task_success, task_postrun

from django.db.models import Model, BooleanField

from ProcessAdminRestApi.signals import update_calculation_status
from generic_app.submodels.Log import Log


def custom_shared_task(function):
    @shared_task(base=CallbackTask)
    @wraps(function)
    def wrap(*args, **kwargs):
        return_value = (function(*args, **kwargs), args)
        return return_value

    return wrap

##################
# CELERY SIGNALS #
##################
@task_postrun.connect
def task_done(sender=None, task_id=None, task=None, args=None, kwargs=None, **kw):
    control = Control(app=task.app)
    control.shutdown()

class CallbackTask(Task):
    def on_success(self, retval, task_id, args, kwargs):
        '''
        retval – The return value of the task.
        task_id – Unique id of the executed task.
        args – Original arguments for the executed task.
        kwargs – Original keyword arguments for the executed task.
        '''
        if self.name != "initial_data_upload":
            record = retval[1][0]
            record.is_calculated = True
            record.calculate = False
            record.save()
            update_calculation_status(self)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        '''
        exc – The exception raised by the task.
        task_id – Unique id of the failed task.
        args – Original arguments for the task that failed.
        kwargs – Original keyword arguments for the task that failed.
        '''
        if self.name != "initial_data_upload":
            record = args[0]
            record.is_calculated = False
            record.calculate = False
            record.dont_update = True
            record.save()
            record.dont_update = False
            update_calculation_status(record)

class UploadModelMixin(Model):

    class Meta():
        abstract = True
        # app_label = "ACP_PFE"

        

    def update(self):
        pass


class IsCalculatedField(BooleanField):
    pass

class CalculateField(BooleanField):
    pass

class ConditionalUpdateMixin(Model):

    celery_result = None
    class Meta():
        abstract = True

    is_calculated = IsCalculatedField(default=False)
    calculate = CalculateField(default=False)

    @staticmethod
    def conditional_calculation(function):
        def wrap(*args, **kwargs):
            self = args[0]

            if getattr(self, 'dont_update', False):
                return None

            if not self.calculate:
                self.is_calculated = False
                self.dont_update = True
                self.save()
                self.dont_update = False
                return None

            try:
                self.is_calculated = False
                self.dont_update = True
                self.save()

                if (hasattr(function, 'delay') and
                    os.getenv("DEPLOYMENT_ENVIRONMENT")
                        and os.getenv("ARCHITECTURE") == "MQ/Worker"):
                    return_value = function.apply_async(args=args, kwargs=kwargs, task_id=f"{str(threading.get_ident())}-{str(uuid.uuid4())}")
                    self.celery_result = return_value
                else:
                    return_value = function(*args, **kwargs)
                    if (not hasattr(self, 'is_inner_calculation') or
                            not self.is_inner_calculation):
                        self.is_calculated = True
                        self.calculate = False
                        self.dont_update = True
                        self.save()
                        self.dont_update = False
                        update_calculation_status(self)

                return return_value
            except Exception as e:
                self.is_calculated = False
                self.calculate = False
                self.dont_update = True
                self.save()
                self.dont_update = False
                update_calculation_status(self)
                raise e

        return wrap
