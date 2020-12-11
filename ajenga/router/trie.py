from typing import AsyncIterable
from typing import Callable
from typing import Dict
from typing import Hashable
from typing import Iterable
from typing import Union
from typing import final

import pygtrie

from ajenga.routing.exceptions import RouteException
from ajenga.routing.exceptions import RouteInternalException
from ajenga.routing.models import AbsNode
from ajenga.routing.models import Node
from ajenga.routing.models import NonterminalNode
from ajenga.routing.models import TerminalNode
from ajenga.routing.keyfunc import KeyFunction
from ajenga.routing.keyfunc import KeyFunctionImpl
from ajenga.routing.std import first_argument
from ajenga.routing.keystore import KeyStore


class AbsTrieNonterminalNode(NonterminalNode, AbsNode):
    _successors: pygtrie.CharTrie
    _empty: bool

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._successors = pygtrie.CharTrie()
        self._empty = True

    async def route(self, *args, **kwargs) -> AsyncIterable[TerminalNode]:
        yield ...
        raise NotImplementedError

    def new(self) -> "AbsTrieNonterminalNode":
        return type(self)()

    def copy(self, node_map: Dict[Node, Node] = ...) -> "AbsTrieNonterminalNode":
        ret = self.new()
        if node_map is ...:
            node_map = {}
        for key, nodes in self._successors.items():
            if not nodes:
                ret.add_key(key)
            for node in nodes:
                ret._add_successor(key, node_map.setdefault(node, node.copy(node_map=node_map)))
        return ret

    @property
    def empty(self) -> bool:
        return self._empty

    def clear(self):
        self.__init__()

    @property
    def successors(self) -> Iterable[Node]:
        return set(node for nodes in self._successors.values() for node in nodes)

    def add_key(self, key):
        if not isinstance(key, Hashable):
            raise ValueError(f"Cannot add {type(key)} to {type(self)} as key of transition")
        if key not in self._successors:
            self._successors[key] = set()

    def add_successor(self, node):
        for key in self._successors:
            self._add_successor(key, node)

    def remove_successor(self, node):
        removed_keys = set()
        for key, nodes in self._successors.items():
            if node in nodes:
                nodes.remove(node)
            if not nodes:
                removed_keys.add(key)
        for key in removed_keys:
            del self._successors[key]

    def _add_successor(self, key, node: Node):
        self._empty = False
        if key not in self._successors:
            self._successors[key] = {node}
            node.add_predecessor((self, key))
        else:
            for u in self._successors[key]:
                if isinstance(u, NonterminalNode) and u == node:
                    u |= node
                    break
            else:
                self._successors[key].add(node)
                node.add_predecessor((self, key))

    def __ior__(self, other):
        if isinstance(other, AbsTrieNonterminalNode):
            for key, nodes in other._successors.items():
                if not nodes:
                    self.add_key(key)
                for node in nodes:
                    self._add_successor(key, node)
            return self
        else:
            raise ValueError(f"Cannot apply operator ior between {type(self)} and {type(other)}")

    def debug_fmt(self, indent=1, verbose=False) -> str:
        out_str = ''
        for key, value in self._successors.items():
            prefix = f'{key}: '
            inner_str = '\n'.join(node.debug_fmt(indent=2) for node in value)
            inner_str = '\n'.join(map(lambda x: f'{" ":{indent + 2}}' + x, inner_str.split('\n')))
            out_str += f'{" ":{indent + 2}}{prefix}[ \n{inner_str} \n{" ":{indent + 2}}]' + '\n'
        if verbose:
            return f'{" ":{indent}}<{type(self).__name__} : \n{out_str}{" ":{indent}}>'
        else:
            return f'{" ":{indent}}<{type(self).__name__} {str(self)}: \n{out_str}{" ":{indent}}>'


@final
class PrefixNode(AbsTrieNonterminalNode):
    def __init__(self, value=..., *values,
                 key: Union[KeyFunction[str], Callable[..., str]] = first_argument,
                 key_id=None):
        super().__init__()
        if isinstance(key, KeyFunction):
            self._key = key
        else:
            self._key = KeyFunctionImpl(key, id_=key_id)
        if value is not ...:
            self.add_key(value)
        for value_ in values:
            self.add_key(value_)

    async def route(self, args, store: KeyStore) -> AsyncIterable[TerminalNode]:
        try:
            key = await store(self._key, args, store)
        except RouteException as e:
            yield e
            return
        except Exception as e:
            yield RouteInternalException(e)
            return

        if not isinstance(key, str):
            return

        # pair = self._successors.longest_prefix(key)
        for pair in self._successors.prefixes(key):
            for node in pair.value:
                if isinstance(node, TerminalNode):
                    yield node
                elif isinstance(node, NonterminalNode):
                    async for terminal in node.route(args, store):
                        yield terminal

    def new(self) -> "PrefixNode":
        return PrefixNode(key=self._key)

    @property
    def __id__(self) -> Hashable:
        return super(PrefixNode, self).__id__, self._key.__id__
