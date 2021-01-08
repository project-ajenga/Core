import re
from ajenga.typing import Tuple, ClassVar, Iterable


class StructCodeMeta(type):
    _meta_type_map = {}
    _STR_TYPE = "default:str"
    _LIST_TYPE = "default:list"

    def __new__(mcls, name, bases, attrs):
        _t = super().__new__(mcls, name, bases, attrs)
        _st = attrs.get('__struct_type__')
        if _st is None:
            pass
        elif isinstance(_st, Tuple):
            for _stt in _st:
                mcls._meta_type_map[_stt] = _t
        else:
            mcls._meta_type_map[_st] = _t

        return _t


class AbsStructCode:
    def encode(self) -> str:
        raise NotImplementedError

    @classmethod
    def decode_it(cls, *args, **kwargs):
        raise NotImplementedError


class StructCode(AbsStructCode, metaclass=StructCodeMeta):
    __struct_type__ = None
    __struct_fields__ = ()

    def encode(self) -> str:
        if not self.__struct_type__:
            return ""
        d = {key: getattr(self, key) for key in self.__struct_fields__}
        return f"[{self.__struct_type__},{','.join(f'{key}={escape(str(value))}' for key, value in sorted(d.items()))}]"

    @classmethod
    def _decode(cls, s: str):
        def _iter_message(msg: str) -> Iterable[Tuple[str, str]]:
            text_begin = 0
            for code in re.finditer(
                    r"\[(?P<type>[a-zA-Z0-9-_:.]+)"
                    r"(?P<params>"
                    r"(?:,[a-zA-Z0-9-_.]+=[^,\]]+)*"
                    r"),?\]", msg):
                yield cls._STR_TYPE, msg[text_begin:code.start()]
                text_begin = code.end()
                yield code.group("type"), code.group("params").lstrip(",")
            yield cls._STR_TYPE, msg[text_begin:]

        for type_, data in _iter_message(s):
            if type_ == cls._STR_TYPE:
                if data:
                    # only yield non-empty text segment
                    yield cls._meta_type_map[type_].decode_it(unescape(data))
            else:
                data = {
                    k: unescape(v) for k, v in map(
                        lambda x: x.split("=", maxsplit=1),
                        filter(lambda x: x, (
                            x.lstrip() for x in data.split(","))))
                }
                yield cls._meta_type_map[type_].decode_it(**data)

    @classmethod
    def decode(cls, s: str):
        return cls._meta_type_map[cls._LIST_TYPE].decode_it(list(cls._decode(s)))


def escape(s: str, *, escape_comma: bool = True) -> str:
    s = s.replace("&", "&amp;") \
        .replace("[", "&#91;") \
        .replace("]", "&#93;")
    if escape_comma:
        s = s.replace(",", "&#44;")
    return s


def unescape(s: str) -> str:
    return s.replace("&#44;", ",") \
        .replace("&#91;", "[") \
        .replace("&#93;", "]") \
        .replace("&amp;", "&")
