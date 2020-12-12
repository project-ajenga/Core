from io import BytesIO
from ajenga.typing import Any

try:
    from PIL.Image import Image as PILImage
except ImportError:
    class PILImage:
        pass


from ajenga.message import *


class Builder:
    def __init__(self):
        self._chain: List[MessageElement] = []

    def __bool__(self):
        return bool(self._chain)

    def build(self, *, lnewline=False, strip=True) -> MessageChain:
        if lnewline:
            if self._chain:
                head = self._chain[0]
                if isinstance(head, Plain):
                    head.text = '\n' + head.text.lstrip()
                else:
                    self._chain.insert(0, Plain('\n'))
            else:
                self._chain.insert(0, Plain('\n'))
        if strip and self._chain:
            tail = self._chain[-1]
            if isinstance(tail, Plain):
                tail.text = tail.text.rstrip()
        return MessageChain(self._chain)

    def append(self,
               element,
               *,
               eol: bool = True,
               image_format: str = 'png',
               ):
        if isinstance(element, str):
            element = Plain(element)
        if isinstance(element, Plain):
            if self._chain:
                tail = self._chain[-1]
                if isinstance(tail, Plain):
                    tail.text += element.text
                else:
                    self._chain.append(element)
            else:
                self._chain.append(element)
            if eol:
                self.append('\n', eol=False)
        elif isinstance(element, MessageElement):
            self._chain.append(element)
        elif isinstance(element, PILImage):
            with BytesIO() as buf:
                element.save(buf, format=image_format)
                self._chain.append(Image(content=buf.getvalue()))
        return self

    def extend(self, elements: Iterable[Any], *, eol: bool = True):
        for element in elements:
            self.append(element, eol=False)
        if self._chain and isinstance(self._chain[-1], Plain) and eol:
            self.newline()
        return self

    def lines(self, elements: Iterable[MessageElement_T], *, eol: bool = True):
        for element in elements:
            self.append(element, eol=eol)
        return self

    def newline(self):
        self.append('\n', eol=False)
        return self
