import os
import pathlib

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
    ):
        image_path = pathlib.Path(os.path.abspath(__file__)).parent / "images/meme/"
        font_path = pathlib.Path(os.path.abspath(__file__)).parent / "fonts/"

        super().__init__(
            image_basepath=image_path,
            font_basepath=font_path,
            image_cache=image_cache,
            font_cache=font_cache,
            async_mode=async_mode,
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
        # return self.writetext("worthless.jpg", fontname="ani.ttf", size=100, center=( 423, 678), text=text)
