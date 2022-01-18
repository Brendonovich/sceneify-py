from __future__ import annotations
from asyncio import gather
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from sceneify.core.source import Source
    from sceneify.core.scene import Scene

class SceneItem:
    def __init__(self, source: Source, scene: Scene, id: int, ref: str):
        self.source = source
        self.scene = scene
        self.id = id
        self.ref = ref
        self.transform = {
            "positionX": 0,
            "positionY": 0,
            "rotation": 0,
            "scaleX": 1,
            "scaleY": 1,
            "cropTop": 0,
            "cropBottom": 0,
            "cropLeft": 0,
            "cropRight": 0,
            "alignment": 0,
            "boundsAlignment": 0,
            "sourceWidth": 0,
            "sourceHeight": 0,
            "width": 0,
            "height": 0,
            "boundsWidth": 0,
            "boundsHeight": 0,
            "boundsType": "OBS_MONITORING_TYPE_NONE",
        }

    async def fetch_properties(self):
        args = {
            "sceneName": self.scene.name,
            "sceneItemId": self.id,
        }

        [transformResp, enabledResp, lockedResp] = await gather(
            *[
                self.source.obs.call("GetSceneItemTransform", args),
                self.source.obs.call("GetSceneItemEnabled", args),
                self.source.obs.call("GetSceneItemLocked", args),
            ]
        )

        self.transform = transformResp["sceneItemTransform"]
        self.enabled = enabledResp["sceneItemEnabled"]
        self.locked = lockedResp["sceneItemLocked"]

    async def set_transform(self, transform: Dict):
        await self.source.obs.call(
            "SetSceneItemTransform",
            {
                "sceneName": self.scene.name,
                "sceneItemId": self.id,
                "sceneItemTransform": transform,
            },
        )

        self.transform.update(transform)

        self.update_size_from_source()

    async def set_enabled(self, enabled: bool):
        await self.source.obs.call(
            "SetSceneItemEnabled",
            {
                "sceneName": self.scene.name,
                "sceneItemId": self.id,
                "sceneItemEnabled": enabled,
            },
        )

        self.enabled = enabled

    async def set_locked(self, locked: bool):
        await self.source.obs.call(
            "SetSceneItemLocked",
            {
                "sceneName": self.scene.name,
                "sceneItemId": self.id,
                "sceneItemLocked": locked,
            },
        )

        self.locked = locked

    def update_size_from_source(
        self, source_width: float = None, source_height: float = None
    ):
        self.transform["sourceWidth"] = source_width or self.transform["sourceWidth"]
        self.transform["sourceHeight"] = source_height or self.transform["sourceHeight"]

        self.transform["width"] = (
            self.transform["scaleX"] * self.transform["sourceWidth"]
        )
        self.transform["height"] = (
            self.transform["scaleY"] * self.transform["sourceHeight"]
        )

    async def remove(self):
        await self.source.obs.call(
            "RemoveSceneItem",
            {
                "sceneName": self.scene.name,
                "sceneItemId": self.id,
            },
        )

        self.source.item_instances.remove(self)
        self.scene.items.remove(self)
