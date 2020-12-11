import hashlib
import imghdr

import aiofiles
import aiohttp

from ajenga.message import Image
from . import ensure_file_path


def gen_image_filename(image: Image) -> str:
    md5 = hashlib.md5(image.content).hexdigest()
    return f'{md5}.{imghdr.what(None, h=image.content)}'


async def save_image(pl, image: Image, dtype, *paths) -> Image:
    async with aiohttp.request("GET", image.url) as resp:
        content = await resp.content.read()
        image.content = content

    filename = gen_image_filename(image)

    async with aiofiles.open(ensure_file_path(pl, dtype, *paths, filename), 'wb+') as f:
        await f.write(content)

    saved_image = Image(url=ensure_file_path(pl, dtype, *paths, filename, as_url=True), content=content)
    return saved_image
