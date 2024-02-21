import json

import asyncio
import os
from urllib.parse import parse_qs

import requests
from channels.generic.websocket import AsyncWebsocketConsumer


class MonitoringConsumer(AsyncWebsocketConsumer):
    active_consumers = set()
    async def connect(self):
        query_string = parse_qs(self.scope['query_string'].decode())
        self.token = query_string.get('token', [None])[0]
        await self.accept()
        self.active_consumers.add(self)

        if os.getenv("DEPLOYMENT_ENVIRONMENT"):
            # Start sending messages every second
            asyncio.create_task(self.send_messages_periodically())

    async def disconnect(self, close_code):
        await super().disconnect(close_code)

    async def receive(self, text_data):
        # Handle receiving message from WebSocket
        pass

    async def send_messages_periodically(self):
        while True:
            await asyncio.sleep(1)  # Wait for one second
            response = requests.get(
                f"https://{os.getenv('DOMAIN_BASE')}/api/monitoring?resource_identifier={os.getenv('INSTANCE_RESOURCE_IDENTIFIER')}",
                verify=False,
                headers={"Authorization": f"Bearer {self.token}"})
            await self.send(text_data=json.dumps(json.loads(response.content.decode("utf-8"))))


    @classmethod
    async def disconnect_all(cls):
        for consumer in cls.active_consumers.copy():
            await consumer.disconnect(None)
