import os

from ProcessAdminRestApi.calculated_model_updates.update_handler import CalculatedModelUpdateHandler
from django.dispatch import receiver

from django.db.models.signals import post_save
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@receiver(post_save)
def calculation_logs(sender, instance, created, **kwargs):
    from generic_app.submodels.CalculationLog import CalculationLog
    from generic_app.submodels.UserChangeLog import UserChangeLog

    if created and (sender == CalculationLog or sender == UserChangeLog):
        channel_layer = get_channel_layer()
        message = {
            'type': 'calculation_log_real_time', # This is the correct naming convention
            'payload': get_model_data(instance.calculationId)
        }
        async_to_sync(channel_layer.group_send)(f'{instance.calculationId}', message)
@receiver(post_save)
def send_calculation_notification(sender, instance, created, **kwargs):
    from generic_app.submodels.CalculationLog import CalculationLog
    # from generic_app.submodels.Notifications import Notifications
    if created and sender == CalculationLog and instance.is_notification:
        channel_layer = get_channel_layer()
        message = {
            'type': 'calculation_log_created', # This is the correct naming convention
            'payload': {
                'id': instance.id,
                'message': instance.message,
            }
        }
        # notification = Notifications(message=instance.message, timestamp=datetime.now())
        # notification.save()
        async_to_sync(channel_layer.group_send)(f'calculation_logs_{os.getenv("DOMAIN_HOSTED", "localhost")}', message)

# @receiver(post_save)
# def send_notification(sender, instance, created, **kwargs):
#     from generic_app.submodels.Notifications import Notifications
#
#     if created and sender == Notifications:
#         channel_layer = get_channel_layer()
#         message = {
#             'type': 'notifications',  # This is the correct naming convention
#             'payload': Notifications.objects.values()
#         }
#         async_to_sync(channel_layer.group_send)(f'notifications_{os.getenv("DOMAIN_HOSTED", "localhost")}', message)

def update_calculation_status(instance):
        # from generic_app.submodels.Notifications import Notifications
        channel_layer = get_channel_layer()
        message = {
            'type': 'calculation_is_completed', # This is the correct naming convention
            'payload': {
                'record': str(instance),
            }
        }
        # notification = Notifications(message="Calculation is finished", timestamp=datetime.now())
        # notification.save()
        async_to_sync(channel_layer.group_send)(f'update_calculation_status_{os.getenv("DOMAIN_HOSTED", "localhost")}', message)

def get_model_data(calculationId):
    from generic_app.submodels.CalculationLog import CalculationLog
    from generic_app.submodels.UserChangeLog import UserChangeLog
    messages = ''
    queryset_ucl = UserChangeLog.objects.filter(calculationId=str(calculationId))
    for message in queryset_ucl:
        messages += str(message.timestamp) + ' ' + str(message.message) + '\n'
    queryset_calc = CalculationLog.objects.filter(calculationId=str(calculationId))
    for message in queryset_calc:
        messages += str(message.timestamp) + ' ' + str(message.message) + '\n'
    return messages

def do_post_save(sender, **kwargs):
    CalculatedModelUpdateHandler.register_save(kwargs['instance'])

from django.dispatch import Signal

custom_post_save = Signal()

