import asyncio
from functools import wraps

from . import argparse


def max_instances(number, ignore=False, ignore_func=None):
    def deco(func):
        _sem = asyncio.Semaphore(number)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            if ignore and _sem.locked():
                return await ignore_func(*args, **kwargs) if ignore_func else None
            async with _sem:
                return await func(*args, **kwargs)

        return wrapper

    return deco
