import asyncio
import functools
import io
import os
import pathlib
from collections.abc import MutableMapping
from typing import Any, Callable, Dict, Optional, Tuple, Union

from PIL import Image

ImageCacheDict = Dict[str, Image.Image]
ImageType = Union[Image.Image, bytes, io.BytesIO, str]


class ImageCache(MutableMapping):
    def __init__(
        self, *, cache_dict: ImageCacheDict, basepath: Union[str, pathlib.Path]
    ):
        self.cache_dict = cache_dict

        if isinstance(basepath, pathlib.Path):
            self.basepath = basepath
        else:
            self.basepath = pathlib.Path(basepath)

    def __getitem__(self, key: str) -> Image.Image:
        # In cache
        if key in self.cache_dict:
            return self.cache_dict[key]

        # Load and populate cache
        img = Image.open(self.basepath / key)
        self[key] = img

        return img

    def __setitem__(self, key: str, value: Image.Image) -> None:
        self.cache_dict[key] = value

    def __delitem__(self, key: str) -> None:
        del self.cache_dict[key]

    def __iter__(self):
        return self.cache_dict.__iter__()

    def __len__(self):
        return len(self.cache_dict)


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
        basepath: Union[str, pathlib.Path],
        loop: Optional[asyncio.BaseEventLoop] = None
    ):
        self.async_mode = async_mode
        self.image_cache = ImageCache(cache_dict=image_cache.copy(), basepath=basepath)
        self.loop = loop
        if async_mode and loop is None:
            self.loop = asyncio.get_event_loop()

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
        # Conversions
        if isinstance(image, str):
            image = Image.open(image)
        if isinstance(image, bytes):
            image = io.BytesIO(image)
        if isinstance(image, io.BytesIO):
            image = Image.open(image)
        if not isinstance(image, Image.Image):
            raise TypeError("Invalid type received for image")

        if resize:
            image = image.resize(resize)
        base.paste(image, coords)

        b = io.BytesIO()
        base.save(b, format=format)
        b.seek(0)
        return b
