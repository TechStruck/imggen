import os
import pathlib

from .core import BaseImageGenerator, ImageCacheDict, ImageType, generator


class MemeGenerator(BaseImageGenerator):
    def __init__(self, async_mode: bool = False, image_cache: ImageCacheDict = {}):
        path = pathlib.Path(os.path.abspath(__file__)).parent / "images/meme/"
        super().__init__(
            basepath=path,
            image_cache=image_cache,
            async_mode=async_mode,
        )

    @generator
    def wanted(self, pfpdata: ImageType):
        return self.paste("wanted.jpg", pfpdata, (269, 451), resize=(395, 395))
