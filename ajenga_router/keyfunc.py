from abc import ABC
from typing import Callable
from typing import Generic
from typing import Hashable
from typing import TypeVar
from typing import Union

from .utils import wrap_function

T = TypeVar('T')


class KeyFunction(ABC, Generic[T]):
    def __init__(self, id_=None):
        self.___id___ = id_

    async def __call__(self, *args, **kwargs) -> T:
        raise NotImplementedError

    @property
    def key(self) -> "Union[Hashable, KeyFunction]":
        return self

    @property
    def __id__(self) -> Hashable:
        return self.___id___ or id(self)

    def __hash__(self):
        return self.__id__.__hash__()

    def __eq__(self, other):
        return isinstance(other, KeyFunction) and self.__id__ == other.__id__


class KeyFunctionImpl(KeyFunction[T]):
    def __init__(self, func: Callable[..., T], *, key=None, id_=None):
        super().__init__(id_)
        self._func = wrap_function(func)
        self._key = key

    async def __call__(self, *args, **kwargs) -> T:
        return await self._func(*args, **kwargs)

    @property
    def key(self) -> "Union[Hashable, KeyFunction]":
        return self._key or self

    @property
    def __id__(self) -> Hashable:
        return self.___id___ or id(self._func)

    def __str__(self):
        return f'<{type(self).__name__}: {self._func}>'


class PredicateFunction(KeyFunction[bool]):
    def __init__(self, func: Callable[..., bool], id_=None, notation=None):
        super().__init__(id_)
        self._func = wrap_function(func)
        self._notation = notation

    async def __call__(self, *args, **kwargs) -> T:
        return await self._func(*args, **kwargs)

    @property
    def __id__(self) -> Hashable:
        return self.___id___ or id(self._func)

    # def __str__(self):
    #     if self._notation:
    #         return f'<{type(self).__name__}: {self._func} with {self._notation}>'
    #     else:
    #         return f'<{type(self).__name__}: {self._func}>'


KeyFunction_T = Union[KeyFunction[T], Callable[..., T]]
PredicateFunction_T = KeyFunction_T[bool]

first_argument = KeyFunctionImpl(lambda _x_: _x_)
