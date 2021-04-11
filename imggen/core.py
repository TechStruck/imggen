import asyncio
import functools
import io
import os
import pathlib
import threading
from collections.abc import MutableMapping
from typing import Any, Callable, Dict, Optional, Tuple, Union

from PIL import Image, ImageDraw, ImageFont

ImageCacheDict = Dict[str, Image.Image]
FontCacheDict = Dict[str, bytes]
ImageType = Union[Image.Image, bytes, io.BytesIO, str]

PathType = Union[str, pathlib.Path]


class AssetCache(MutableMapping):
    def __init__(self, *, cache_dict: Dict, basepath: PathType):
        self.cache_dict = cache_dict
        self.lock = threading.Lock()

        if isinstance(basepath, pathlib.Path):
            self.basepath = basepath
        else:
            self.basepath = pathlib.Path(basepath)

    def __setitem__(self, key: str, value) -> None:
        with self.lock:
            self.cache_dict[key] = value

    def __delitem__(self, key: str) -> None:
        with self.lock:
            del self.cache_dict[key]

    def __iter__(self):
        return self.cache_dict.__iter__()

    def __len__(self):
        return len(self.cache_dict)


class ImageCache(AssetCache):
    def __init__(self, *, cache_dict: ImageCacheDict, basepath: PathType):
        super().__init__(cache_dict=cache_dict, basepath=basepath)

    def __getitem__(self, key: str) -> Image.Image:
        with self.lock:
            # In cache
            if key in self.cache_dict:
                return self.cache_dict[key]

        # Load and populate cache
        img = Image.open(self.basepath / key)
        self[key] = img

        return img


class FontCache(AssetCache):
    def __init__(self, *, cache_dict: FontCacheDict, basepath: PathType):
        super().__init__(cache_dict=cache_dict, basepath=basepath)

    def __getitem__(self, key: Tuple[str, int]) -> ImageFont.FreeTypeFont:
        filename, size = key

        with self.lock:
            if filename in self.cache_dict:
                return ImageFont.truetype(
                    io.BytesIO(self.cache_dict[filename]), size=size
                )

        with open(self.basepath / filename, "rb") as f:
            fontbytes = f.read()

        font = ImageFont.truetype(io.BytesIO(fontbytes), size=size)
        self.cache_dict[filename] = fontbytes

        return font


def generator(func: Callable):
    func.__image_generator__ = True
    return func


class Generator:
    def __init__(self, func, *, gen: "BaseImageGenerator"):
        self.func = func
        self.gen = gen

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if self.gen.async_mode:
            return self.gen.loop.run_in_executor(
                None, functools.partial(self.func, *args, **kwargs)
            )
        return self.func(*args, **kwargs)


class BaseImageGenerator:
    def __new__(cls, *args, **kwargs) -> Any:
        self = super().__new__(cls)
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if getattr(attr, "__image_generator__", False):
                setattr(self, attr_name, Generator(attr, gen=self))

        return self

    def __init__(
        self,
        *,
        async_mode: bool = False,
        image_cache: ImageCacheDict = {},
        font_cache: FontCacheDict = {},
        image_basepath: Union[str, pathlib.Path],
        font_basepath: Union[str, pathlib.Path],
        loop: Optional[asyncio.BaseEventLoop] = None
    ):
        self.async_mode = async_mode
        self.image_cache = ImageCache(
            cache_dict=image_cache.copy(), basepath=image_basepath
        )
        self.font_cache = FontCache(
            cache_dict=font_cache.copy(), basepath=font_basepath
        )
        self.loop = loop
        if async_mode and loop is None:
            self.loop = asyncio.get_event_loop()

    def convert_to_image(self, image: ImageType) -> Image.Image:
        # Conversions
        if isinstance(image, str):
            image = Image.open(image)
        if isinstance(image, bytes):
            image = io.BytesIO(image)
        if isinstance(image, io.BytesIO):
            image = Image.open(image)
        if not isinstance(image, Image.Image):
            raise TypeError("Invalid type received for image")
        return image

    def image_to_bytesio(self, image: Image.Image, format: str = "JPEG"):
        b = io.BytesIO()
        image.save(b, format=format)
        b.seek(0)
        return b

    def paste(
        self,
        basename: str,
        image: ImageType,
        coords: Tuple[int, int],
        *,
        format="JPEG",
        resize: Tuple[int, int] = None
    ):
        base = self.image_cache[basename]
        image = self.convert_to_image(image)

        if resize:
            image = image.resize(resize)
        base.paste(image, coords)

        return self.image_to_bytesio(base, format=format)

    def writetext(
        self,
        imagename: str,
        *,
        fontname: str,
        size: int,
        center: Tuple[int, int],
        text: str,
        fill: Tuple[int, int, int] = (0, 0, 0),
        format: str = "JPEG"
    ):
        image = self.image_cache[imagename]

        font = self.font_cache[fontname, size]
        xy = (center[0] - font.getlength(text) // 2, center[1] - size // 2)

        draw = ImageDraw.Draw(image)
        draw.text(xy, text, fill=fill, font=font)

        return self.image_to_bytesio(image, format=format)
