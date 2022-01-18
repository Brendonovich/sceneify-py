from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, Set

if TYPE_CHECKING:
    from sceneify.core.obs import OBS
    from sceneify.core.scene import Scene
from sceneify.core.scene_item import SceneItem

class Source(ABC):
    filters: list = []

    obs: OBS = None
    item_instances: Set[SceneItem] = set()
    refs: Dict[str, Dict[str, int]] = {}

    @property
    def initialized(self):
        return self._initialized

    @property
    def exists(self):
        return self._exists

    def __init__(self, name: str, kind: str, filters: Dict[str, Dict] = {}):
        self._initialized = False
        self._exists = False

        self.name = name
        self.kind = kind
        self.filtersMap = filters or {}

    async def initialize(self, obs: OBS):
        if self.initialized:
            pass

        self.obs = obs

        exists = await self.fetch_exists()
        if exists:
            await self._fetch_refs()

        self._exists = exists
        self._initialized = True

    def link_item(self, scene: Scene, id: int, ref: str):
        self.linked = True
        self._exists = True
        self._initialized = True
        self.obs = scene.obs

        return self.create_scene_item_object(scene, id, ref)

    async def create_scene_item(self, ref: str, scene: Scene):
        if not self.initialized:
            raise Exception(
                f"Cannot create item of source {self.name} as it is not initialized"
            )

        item_id: int
        transform: Dict or None = None

        if self.exists:
            id = self._get_ref(scene.name, ref)
            
            if id is not None:
                try:
                    res = await self.obs.call(
                        "GetSceneItemTransform",
                        {"sceneItemId": id, "sceneName": scene.name},
                    )
                    
                    if res is None:
                        raise Exception()

                    transform = res["sceneItemTransform"]
                    item_id = id
                except:
                    await self._remove_ref(scene.name, ref)

                    res = await self.obs.call(
                        "CreateSceneItem",
                        {
                            "sceneName": scene.name,
                            "sourceName": self.name,
                        },
                    )

                    item_id = res["sceneItemId"]
            else:
                res = await self.obs.call(
                    "CreateSceneItem",
                    {
                        "sceneName": scene.name,
                        "sourceName": self.name,
                    },
                )

                item_id = res["sceneItemId"]
        else:
            item_id = await self.create_first_scene_item(scene)

            self._exists = True

            for filter in self.filters:
                filter.source = self
                filter.settings = filter.initial_settings

        await self._add_ref(scene.name, ref, item_id)
        item = self.create_scene_item_object(scene, item_id, ref)

        if transform is not None:
            item.transform = transform

        return item

    def create_scene_item_object(self, scene: Scene, id: int, ref: str):
        item = SceneItem(self, scene, id, ref)
        self.item_instances.add(item)
        return item

    @abstractmethod
    async def create_first_scene_item(self, scene: Scene) -> int:
        pass

    @abstractmethod
    async def fetch_exists(self) -> bool:
        pass

    async def _set_private_settings(self, settings: Dict):
        await self.obs.call(
            "SetSourcePrivateSettings",
            {
                "sourceName": self.name,
                "sourceSettings": settings,
            },
        )

    def _get_ref(self, scene: str, ref: str) -> int or None:
        return self.refs.get(scene, {}).get(ref, None)

    async def _add_ref(self, scene: str, ref: str, id: int):
        scene_refs = self.refs.get(scene) or {}
        scene_refs[ref] = id
        self.refs[scene] = scene_refs

        await self._send_refs()

    async def _remove_ref(self, scene: str, ref: str):
        self.refs.get(scene, {}).pop(ref, None)

        await self._send_refs()

    def _send_refs(self):
        return self.obs.call(
            "SetSourcePrivateSettings",
            {"sourceName": self.name, "sourceSettings": {"SIMPLE_OBS_REFS": self.refs}},
        )

    async def _fetch_refs(self):
        resp = await self.obs.call(
            "GetSourcePrivateSettings", {"sourceName": self.name}
        ) or {}

        self.refs = resp.get("sourceSettings", {}).get("SIMPLE_OBS_REFS", {})
        
    async def push_refs(self):
        refs = {}

        for item in self.item_instances:
            item: SceneItem = item

            scene_refs = refs.get(item.scene.name) or {}
            scene_refs[item.ref] = item.id
            refs[item.scene.name] = scene_refs

        self.refs = refs
        await self._send_refs()
