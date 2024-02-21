import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationsConsumer(AsyncWebsocketConsumer):
    active_consumers = set()
    async def connect(self):
        self.host_id = self.scope['url_route']['kwargs']['host']
        await self.channel_layer.group_add(f'notifications_{self.host_id}', self.channel_name)
        await self.accept()
        self.active_consumers.add(self)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(f'notifications_{self.host_id}', self.channel_name)
        await self.send(text_data=json.dumps({
            'status': "Closed"
        }))
        await super().disconnect(close_code)

    async def notifications(self, event):
        payload = event['payload']
        await self.send(text_data=json.dumps({
            'type': 'notifications',
            'payload': payload
        }))
    @classmethod
    async def disconnect_all(cls):
        for consumer in cls.active_consumers.copy():
            await consumer.disconnect(None)
