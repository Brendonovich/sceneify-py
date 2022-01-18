from sceneify.core import __version__
from sceneify.core import Scene, OBS, Input

# def test_version():
#     assert __version__ == "0.1.0"


async def main():
    obs = OBS()
    await obs.connect("ws://localhost:4444")

    scene = Scene(
        name="Main",
        items={
            "test": {
                "source": Input(
                    name="Color",
                    kind="color_source_v3",
                    settings={"width": 200, "height": 500, "color": 0xFFFFFFFF},
                ),
                "positionX": 200
            }
        },
    )

    await scene.create(obs)

