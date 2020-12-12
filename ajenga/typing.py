from typing import (Any, AnyStr, AsyncIterable, Awaitable, Callable, Collection, Container, Coroutine,
                    Dict, Generic, Hashable, Iterable, List, Mapping, OrderedDict, Pattern, Optional,
                    Set, Tuple, Type, TypeVar, TYPE_CHECKING, Union)

try:
    from typing import final
except ImportError:
    def final(x):
        return x
