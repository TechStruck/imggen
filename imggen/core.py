import asyncio
import functools
import io
import multiprocessing
import pathlib
import threading
from collections.abc import MutableMapping
from concurrent.futures import Executor, ProcessPoolExecutor
from contextlib import AbstractContextManager
from typing import Any, Callable, Dict, Optional, Tuple, Type, Union, overload

from PIL import Image, ImageDraw, ImageFont

ImageCacheDict = Dict[str, Image.Image]
FontCacheDict = Dict[str, bytes]
ImageType = Union[Image.Image, bytes, io.BytesIO, str]

PathType = Union[str, pathlib.Path]


class AssetCache(MutableMapping):
    def __init__(
        self, *, cache_dict: Dict, basepath: PathType, lock: AbstractContextManager
    ):
        self.cache_dict = cache_dict
        self.lock = lock

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
    def __init__(
        self,
        *,
        cache_dict: ImageCacheDict,
        basepath: PathType,
        lock: AbstractContextManager,
    ):
        super().__init__(cache_dict=cache_dict, basepath=basepath, lock=lock)

    def __getitem__(self, key: str) -> Image.Image:
        with self.lock:
            # In cache
            if key in self.cache_dict:
                return self.cache_dict[key].copy()

        # Load and populate cache
        img = Image.open(self.basepath / key)
        self[key] = img

        return img.copy()


class FontCache(AssetCache):
    def __init__(
        self,
        *,
        cache_dict: FontCacheDict,
        basepath: PathType,
        lock: AbstractContextManager,
    ):
        super().__init__(cache_dict=cache_dict, basepath=basepath, lock=lock)

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
                self.gen.executor, functools.partial(self.func, *args, **kwargs)
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
        loop: Optional[asyncio.BaseEventLoop] = None,
        executor: Optional[Executor] = None,
    ):
        self.loop = loop
        self.executor = executor
        self.lock_type = (
            multiprocessing.Lock
            if isinstance(executor, ProcessPoolExecutor)
            else threading.Lock
        )
        self.async_mode = async_mode
        self.image_cache = ImageCache(
            cache_dict=image_cache.copy(),
            basepath=image_basepath,
            lock=self.lock_type(),
        )
        self.font_cache = FontCache(
            cache_dict=font_cache.copy(), basepath=font_basepath, lock=self.lock_type()
        )
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
        resize: Tuple[int, int] = None,
    ):
        base = self.image_cache[basename]
        image = self.convert_to_image(image)

        if resize:
            image = image.resize(resize)
        base.paste(image, coords)

        return self.image_to_bytesio(base, format=format)

    @overload
    def writetext(
        self,
        image: Union[Image.Image, str],
        *,
        fontname: str,
        size: int,
        center: Tuple[int, int],
        text: str,
        fill: Tuple[int, int, int] = (0, 0, 0),
        format: str = "JPEG",
        return_type: Type[io.BytesIO] = io.BytesIO,
    ) -> io.BytesIO:
        ...

    @overload
    def writetext(
        self,
        image: Union[Image.Image, str],
        *,
        fontname: str,
        size: int,
        center: Tuple[int, int],
        text: str,
        fill: Tuple[int, int, int] = (0, 0, 0),
        format: str = "JPEG",
        return_type: Type[bytes] = bytes,
    ) -> bytes:
        ...

    @overload
    def writetext(
        self,
        image: Union[Image.Image, str],
        *,
        fontname: str,
        size: int,
        center: Tuple[int, int],
        text: str,
        fill: Tuple[int, int, int] = (0, 0, 0),
        format: str = "JPEG",
        return_type: Type[Image.Image] = Image.Image,
    ) -> Image.Image:
        ...

    def writetext(
        self,
        image: Union[Image.Image, str],
        *,
        fontname: str,
        size: int,
        center: Tuple[int, int],
        text: str,
        fill: Tuple[int, int, int] = (0, 0, 0),
        format: str = "JPEG",
        return_type: Type[Union[io.BytesIO, Image.Image, bytes]] = io.BytesIO,
    ) -> Union[io.BytesIO, Image.Image, bytes]:
        if isinstance(image, str):
            image = self.image_cache[image]
        text = text.strip()

        font = self.font_cache[fontname, size]
        length = max([font.getlength(t) for t in text.split("\n")])
        height = size * len(text.split("\n"))
        xy = (center[0] - length // 2, center[1] - height // 2)

        draw = ImageDraw.Draw(image)
        draw.text(xy, text, fill=fill, font=font, align="center")

        if issubclass(return_type, Image.Image):
            return image

        if issubclass(return_type, io.BytesIO):
            return self.image_to_bytesio(image, format=format)

        if issubclass(return_type, bytes):
            return self.image_to_bytesio(image, format=format).read()

        raise RuntimeError(f"Unknown return_type {return_type.__name__}")
