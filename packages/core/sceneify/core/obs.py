from typing import Dict
from simpleobsws import WebSocketClient, IdentificationParameters, Request
from sceneify.core.scene import Scene

class OBS:    
    inputs: Dict[str, Dict] = {}
    scenes: Dict[str, Scene] = {}

    def __init__(self):
        pass

    async def connect(self, url: str, password: str = ""):
        self.socket = WebSocketClient(
            url, password, IdentificationParameters(eventSubscriptions=4 | 8 | 32 | 128)
        )
        
        await self.socket.connect()
        await self.socket.wait_until_identified()

    async def call(self, requestType: str, requestData: Dict[str, any]):
        resp = await self.socket.call(Request(requestType, requestData))
        return resp.responseData