from __future__ import annotations
from typing import TYPE_CHECKING, Dict, List
from sceneify.core.scene_item import SceneItem
from sceneify.core.source import Source
from asyncio import gather

if TYPE_CHECKING:
    from sceneify.core.obs import OBS


class Scene(Source):
    _items_schema: Dict[str, Dict]

    items: List[SceneItem] = []

    def __init__(
        self,
        name: str,
        items: Dict[str, Dict],
        filters: Dict[str, Dict] = {},
    ):
        super().__init__(kind="scene", name=name, filters=filters)
        self._items_schema = items

    async def create(self, obs: OBS):
        if self.exists:
            return self

        await self.initialize(obs)

        if not self.exists:
            await obs.call(
                "CreateScene",
                {
                    "sceneName": self.name,
                },
            )
            await self.push_refs()

        self._exists = True

        obs.scenes[self.name] = self

        for ref in self._items_schema:
            await self.create_item(ref, self._items_schema[ref])

        await self._set_private_settings({"SIMPLE_OBS_LINKED": False})

        return self

    async def link(self, obs: OBS, options: Dict = {}):
        self.obs = obs

        if self.initialized:
            raise Exception(
                f"Failed to link scene {self.name}: Scene is already initialized"
            )

        scene_items = []

        resp = await obs.call(
            "GetSceneItemList",
            {
                "sceneName": self.name,
            },
        )

        if resp is None:
            raise Exception(f"Failed to link scene {self.name}: Scene does not exist")

        scene_items = resp["sceneItems"]

        self._exists = True

        multiple_item_sources = [], no_item_sources = []

        for ref in self._items_schema:
            item_schema = self._items_schema[ref]

            source_items = next(
                i for i in scene_items if i["sourceName"] == item_schema.source.name
            )

            if len(source_items) == 0:
                no_item_sources.append(item_schema["source"])
            elif len(source_items > 1):
                multiple_item_sources.append(item_schema["source"])

        if len(multiple_item_sources) > 0 or len(no_item_sources) > 0:
            multiple_item_errors = (
                ""
                if len(multiple_item_sources) == 0
                else f"""Scene contains multiple items of sources {", ".join(map(lambda x: f"'{x.name}'", multiple_item_sources))}. """
            )
            no_item_errors = (
                ""
                if len(no_item_sources == 0)
                else f"""Scene contains no items of sources {", ".join(map(lambda x: f"'{x.name}'", no_item_sources))}. """
            )

            raise Exception(
                f"""Failed to link scene {self.name}:{multiple_item_errors}{no_item_errors}"""
            )

        # TODO: Gather into many coroutines
        for ref, schema in self._items_schema.items():
            source: Source = schema.pop("source")
            schema_item = next(
                i for i in scene_items if i["sourceName"] == schema["source"].name
            )

            item = source.link_item(self, schema_item["sceneItemId"], ref)

            self.items.append(item)

            await item.fetch_properties()

            option_requests = []
            if options.get("set_properties", False):
                option_requests.append(item.set_transform(schema))
            if options.get(
                "set_source_settings", False
            ):  # and isinstance(source, Input):
                option_requests.append(source.set_settings(source.settings))

            await gather(*option_requests)

        await self._set_private_settings({"SIMPLE_OBS_LINKED": True})

    async def create_item(self, ref: str, schema: Dict):
        source: Source = schema.pop("source")

        await source.initialize(self.obs)

        item = await source.create_scene_item(ref, self)

        if len(schema) != 0:
            await item.set_transform(schema)

        await item.fetch_properties()

        self.items.append(item)

        return item

    def item(self, ref: str):
        return next((x for x in self.items if x.ref == ref), None)

    async def create_first_scene_item(self, scene: Scene) -> int:
        await self.create(scene.obs)

        resp = await self.obs.call(
            "CreateSceneItem",
            {
                "sceneName": scene.name,
                "sourceName": self.name,
            },
        )

        self.obs.scenes[self.name] = self

        return resp["sceneItemId"]

    async def fetch_exists(self) -> bool:
        resp = await self.obs.call(
            "GetSourcePrivateSettings", {"sourceName": self.name}
        )
        if resp is None:
            return False

        input = await self.obs.call("GetInputSettings", {"inputName": self.name})

        if input is not None:
            raise Exception(
                f"Failed to initialize scene {self.name}: Input of kind {input['inputKind']} already exists."
            )

        return True

    async def make_current_scene(self, preview=False):
        await self.obs.call(
            "SetCurrentPreviewScene" if preview else "SetCurrentScene",
            {"sceneName": self.name},
        )
