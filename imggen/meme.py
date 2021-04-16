import os
import pathlib
from concurrent.futures import Executor

from PIL import Image

from .core import (
    BaseImageGenerator,
    FontCacheDict,
    ImageCacheDict,
    ImageType,
    generator,
)


class MemeGenerator(BaseImageGenerator):
    def __init__(
        self,
        async_mode: bool = False,
        image_cache: ImageCacheDict = {},
        font_cache: FontCacheDict = {},
        executor: Executor = None,
    ):
        image_path = pathlib.Path(os.path.abspath(__file__)).parent / "images/meme/"
        font_path = pathlib.Path(os.path.abspath(__file__)).parent / "fonts/"

        super().__init__(
            image_basepath=image_path,
            font_basepath=font_path,
            image_cache=image_cache,
            font_cache=font_cache,
            async_mode=async_mode,
            executor=executor,
        )

    @generator
    def wanted(self, pfpdata: ImageType):
        return self.paste("wanted.jpg", pfpdata, (269, 451), resize=(395, 395))

    @generator
    def worthless(self, text: str):
        return self.writetext(
            "worthless.jpg",
            fontname="OpenSans-Light.ttf",
            size=100,
            center=(678, 423),
            text=text,
        )

    @generator
    def sleep(self, text: str):
        return self.writetext(
            "sleep.png",
            fontname="OpenSans-Light.ttf",
            size=65,
            center=(190, 463),
            text=text,
            format="PNG",
        )

    @generator
    def pupil(self, text: str):
        return self.writetext(
            "pupil.jpg",
            fontname="OpenSans-Light.ttf",
            size=40,
            center=(135, 354),
            text=text,
        )

    @generator
    def kidsupset(self, text: str):
        return self.writetext(
            "kids upset.png",
            fontname="OpenSans-Light.ttf",
            size=100,
            center=(932, 452),
            text=text,
        )

    @generator
    def spongebob(self, text: str):
        return self.writetext(
            "spongebob.jpg",
            fontname="OpenSans-Light.ttf",
            size=50,
            center=(145, 183),
            text=text,
        )

    @generator
    def undertaker(self, text1: str, text2: str):
        img = self.writetext(
            "undertaker 1.jpg",
            fontname="OpenSans-Light.ttf",
            size=50,
            center=(348, 444),
            text=text1,
            return_type=Image.Image,
            fill=(255, 255, 255),
        )

        return self.writetext(
            img,
            fontname="OpenSans-Light.ttf",
            size=50,
            center=(549, 176),
            text=text2,
            fill=(355, 355, 355),
        )
