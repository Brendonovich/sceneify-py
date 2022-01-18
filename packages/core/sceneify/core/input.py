from asyncio import gather
from typing import Any, Dict
from sceneify.core.scene import Scene
from sceneify.core.source import Source


class Input(Source):
    def __init__(
        self,
        name: str,
        kind: str,
        settings: Dict[str, Any] = {},
        filters: Dict[str, Dict] = {},
    ):
        super().__init__(name, kind, filters)
        self.settings = settings

    async def set_settings(self, settings: Dict[str, Any]):
        await self.obs.call(
            "SetInputSettings", {"inputName": self.name, "inputSettings": settings}
        )

        self.settings.update(settings)

    async def fetch_exists(self) -> bool:
        settings = await self.obs.call(
            "GetSourcePrivateSettings", {"sourceName": self.name}
        )
        
        if settings is None:
            return False

        input = await self.obs.call("GetInputSettings", {"inputName": self.name})
        
        if input is None:
            raise Exception(
                f"Failed to initialize input {self.name}: Scene with this name already exists."
            )

        return True

    async def create_first_scene_item(self, scene: Scene) -> int:
        resp = await self.obs.call(
            "CreateInput",
            {
                "inputName": self.name,
                "inputKind": self.kind,
                "sceneName": scene.name,
                "inputSettings": self.settings,
            },
        )

        self.obs.inputs[self.name] = self

        return resp["sceneItemId"]

    async def fetch_properties(self):
        args = {"inputName": self.name}

        [mutedResp, volumeResp, syncResp, monitorResp] = await gather(
            *list(
                map(
                    lambda r: self.obs.call(r, args),
                    [
                        "GetInputMute",
                        "GetInputVolume",
                        "GetInputAudioSyncOffset",
                        "GetInputAudioMonitorType",
                    ],
                )
            )
        )

        self.muted = mutedResp["inputMuted"]
        self.volume = {
            "db": volumeResp["inputVolumeDb"],
            "mul": volumeResp["inputVolumeMul"],
        }
        self.audio_sync_offset = syncResp["inputAudioSyncOffset"]
        self.audio_monitor_type = monitorResp["monitorType"]

    async def set_muted(self, muted: bool):
        await self.obs.call(
            "SetInputMute", {"inputName": self.name, "inputMuted": muted}
        )

        self.muted = muted

    async def toggle_muted(self):
        resp = await self.obs.call("ToggleInputMute", {"inputName": self.name})

        self.muted = resp["inputMuted"]

        return self.muted

    async def setVolume(self, db: float = None, mul: float = None):
        await self.obs.call(
            "SetInputVolume",
            {
                "inputName": self.name,
                "inputVolumeDb": db,
                "inputVolumeMul": mul,
            },
        )

        resp = await self.obs.call("GetInputVolume", {"inputName": self.name})

        self.volume = {"db": resp["inputVolumeDb"], "mul": resp["inputVolumeMul"]}

    async def set_audio_sync_offset(self, offset: float):
        await self.obs.call(
            "SetInputAudioSyncOffset",
            {"inputName": self.name, "inputAudioSyncOffset": offset},
        )

        self.audio_sync_offset = offset

    async def set_audio_monitor_type(self, type: str):
        await self.obs.call(
            "SetInputAudioMonitorType",
            {"inputName": self.name, "monitorType": type},
        )

        self.audio_monitor_type = type
