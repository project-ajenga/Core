import hashlib
import imghdr

import aiofiles
import aiohttp
from ajenga.message import Image, Voice

from . import ensure_file_path


def gen_image_filename(image: Image) -> str:
    assert image.content
    md5 = hashlib.md5(image.content).hexdigest()
    return f'{md5}.{imghdr.what(None, h=image.content)}'


async def save_image(pl, image: Image, dtype, *paths) -> Image:
    assert image.url
    async with aiohttp.request("GET", image.url) as resp:
        content = await resp.content.read()
        image.content = content

    filename = gen_image_filename(image)

    async with aiofiles.open(ensure_file_path(pl, dtype, *paths, filename),
                             'wb+') as f:
        await f.write(content)

    saved_image = Image(url=ensure_file_path(pl,
                                             dtype,
                                             *paths,
                                             filename,
                                             as_url=True),
                        content=content)
    return saved_image


def gen_voice_filename(voice: Voice) -> str:
    assert voice.content
    md5 = hashlib.md5(voice.content).hexdigest()
    return f'{md5}.amr'


async def save_voice(pl, voice: Voice, dtype, *paths) -> Voice:
    assert voice.url
    async with aiohttp.request("GET", voice.url) as resp:
        content = await resp.content.read()
        voice.content = content

    filename = gen_voice_filename(voice)

    async with aiofiles.open(ensure_file_path(pl, dtype, *paths, filename),
                             'wb+') as f:
        await f.write(content)

    saved_voice = Voice(url=ensure_file_path(pl,
                                             dtype,
                                             *paths,
                                             filename,
                                             as_url=True),
                        content=content)
    return saved_voice
