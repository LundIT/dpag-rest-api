from django.urls import path

from ProcessAdminRestApi.consumers.CalculationNotificationConsumer import CalculationNotificationConsumer
from ProcessAdminRestApi.consumers.BackendHealthConsumer import BackendHealthConsumer
from ProcessAdminRestApi.consumers.CalculationLogConsumer import CalculationLogConsumer
from ProcessAdminRestApi.consumers.MonitoringConsumer import MonitoringConsumer
from ProcessAdminRestApi.consumers.NotificationsConsumer import NotificationsConsumer
from ProcessAdminRestApi.consumers.UpdateCalculationStatusConsumer import UpdateCalculationStatusConsumer

websocket_urlpatterns = [
    path('ws/health', BackendHealthConsumer.as_asgi(),
                 name='backend-health'),
    path('ws/monitoring', MonitoringConsumer.as_asgi(),
         name='monitoring'),
    path('ws/notifications/<str:host>', NotificationsConsumer.as_asgi(),
         name='notifications'),
    path('ws/calculation_logs/<str:calculationId>', CalculationLogConsumer.as_asgi(),
         name='calculation-logs'),
    path('ws/calculation_notifications/<str:host>', CalculationNotificationConsumer.as_asgi(),
         name='calculation-notifications'),
    path('ws/calculation_status_update/<str:host>', UpdateCalculationStatusConsumer.as_asgi(),
         name='calculation-status-update'),

]
