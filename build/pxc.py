# -*- coding: utf-8 -*-
"""Pixel Composer 工程文件（``.pxc``）容器编解码 —— 维护者侧工具。

为什么需要它
------------
「入门指南」里的教程页与示例工程都是 ``.pxc`` 文件。教程文字并不在图片里，
而是存在工程内部的**文本节点**上，所以要汉化就必须能安全地读写这个容器。

容器格式（游戏 1.22 实测，``PXCX``）
------------------------------------
::

    +--------+--------+-------------------------------+---------------------------+
    | "PXCX" | u32 LE | 若干分块 (tag + u32 LE + 载荷) | zlib 流（主数据）          |
    +--------+--------+-------------------------------+---------------------------+
      0..3     4..7              8 .. data_off                    data_off ..

* ``bytes[4:8]`` 是 **u32 LE 的 data_off** —— 主数据（zlib）的起始偏移。
  注意它**不是**某个分块的长度，这一点很容易看错：偏移 8 处紧跟的 ``THMB``
  分块自带自己的长度字段，与 ``PXCX`` 头部的这个数字无关。
* 分块实见两种：

  - ``THMB`` —— 欢迎页的缩略图（zlib 后的 RGBA 图，256×192）
  - ``META`` —— 4 字节 + 版本串 + ``\\0``，例如 ``1.22.10.2``

* 主数据解压后是 JSON 文本，**后面可能还跟着几个字节**（实测多出一个换行）。
  这里用 ``raw_decode`` 只取 JSON 对象本身，把尾巴原样保存并写回，
  避免擅自裁掉游戏自己写的东西。

写回策略
--------
只改 JSON 内容，``THMB`` / ``META`` 分块与尾巴字节**原样保留**，
重新压缩后修正头部偏移。这样缩略图与版本串绝不会被我们弄坏。

顺带支持**旧格式**（未压缩的纯 JSON，旧社区汉化包用的就是它）以便读取比对；
``write_bytes()`` 输出的一律是新格式。
"""
import json
import struct
import zlib

MAGIC = b"PXCX"
DEFAULT_LEVEL = 9

#: 需要翻译的节点类型 —— 只有这两类节点的 ``inputs[].r.d`` 是"给人看的文本"。
#: 其它节点里同样存在 ``r.d``，但内容是调色曲线 JSON / 文件路径 / 文件名，
#: 翻译它们会直接弄坏工程（见 build/translate_welcome.py 的说明）。
TEXT_NODE_TYPES = ("Node_Display_Text", "Node_Slideshow")


class PxcError(Exception):
    """容器结构异常（魔数不对、分块越界、主数据无法解压等）。"""


class Pxc:
    """一个 ``.pxc`` 工程：分块原样保存 + 可读写的 JSON 主数据。"""

    def __init__(self, chunks, data, suffix=b"", fmt="pxcx"):
        #: [(tag:str, payload:bytes), ...] 原样保留
        self.chunks = chunks
        #: 主数据（已解析的 JSON 对象）
        self.data = data
        #: JSON 之后的尾巴字节（实测是换行）
        self.suffix = suffix
        #: "pxcx"（新格式容器）或 "json"（旧格式）
        self.fmt = fmt

    # ------------------------------------------------------------------
    # 读取
    # ------------------------------------------------------------------
    @classmethod
    def from_bytes(cls, raw):
        if raw[:4] == MAGIC:
            return cls._from_pxcx(raw)
        return cls._from_plain_json(raw)

    @classmethod
    def read(cls, path):
        with open(path, "rb") as f:
            return cls.from_bytes(f.read())

    @classmethod
    def _from_pxcx(cls, raw):
        if len(raw) < 8:
            raise PxcError("文件太短，不是有效的 pxc 容器")
        data_off = struct.unpack_from("<I", raw, 4)[0]
        if not (8 <= data_off <= len(raw)):
            raise PxcError(f"主数据偏移非法：{data_off}（文件长 {len(raw)}）")
        chunks = []
        off = 8
        while off < data_off:
            if off + 8 > data_off:
                raise PxcError(f"分块头越界 @{off}")
            tag = raw[off:off + 4].decode("ascii", "replace")
            size = struct.unpack_from("<I", raw, off + 4)[0]
            end = off + 8 + size
            if end > data_off:
                raise PxcError(f"分块 {tag!r} 长度越界：{size} @{off}")
            chunks.append((tag, raw[off + 8:end]))
            off = end
        if off != data_off:
            raise PxcError(f"分块区未对齐：解析到 {off}，头部声明 {data_off}")
        try:
            plain = zlib.decompress(raw[data_off:])
        except Exception as e:
            raise PxcError(f"主数据解压失败：{e}")
        obj, end = cls._decode_json(plain)
        return cls(chunks, obj, plain[end:], "pxcx")

    @classmethod
    def _from_plain_json(cls, raw):
        obj, end = cls._decode_json(raw)
        return cls([], obj, raw[end:], "json")

    @staticmethod
    def _decode_json(buf):
        for enc in ("utf-8-sig", "utf-8"):
            try:
                text = buf.decode(enc)
            except UnicodeDecodeError:
                continue
            try:
                obj, end = json.JSONDecoder().raw_decode(text)
            except ValueError as e:
                raise PxcError(f"主数据不是合法 JSON：{e}")
            # 把"字符位置"换回"字节位置"，尾巴才能原样保留
            consumed_bytes = len(text[:end].encode(enc))
            return obj, consumed_bytes
        raise PxcError("主数据不是 UTF-8 文本")

    # ------------------------------------------------------------------
    # 写出
    # ------------------------------------------------------------------
    def to_bytes(self, level=DEFAULT_LEVEL):
        """打包成新格式容器字节。"""
        payload = json.dumps(self.data, ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8") + self.suffix
        blob = zlib.compress(payload, level)
        head = bytearray(MAGIC)
        head += b"\x00\x00\x00\x00"          # data_off 占位，最后回填
        for tag, body in self.chunks:
            head += tag.encode("ascii")
            head += struct.pack("<I", len(body))
            head += body
        struct.pack_into("<I", head, 4, len(head))
        return bytes(head) + blob

    def write(self, path, level=DEFAULT_LEVEL):
        with open(path, "wb") as f:
            f.write(self.to_bytes(level))

    # ------------------------------------------------------------------
    # 文本节点遍历
    # ------------------------------------------------------------------
    def text_nodes(self):
        """产出 (node, input_dict)，仅限 TEXT_NODE_TYPES 且 ``r.d`` 是字符串的项。

        原地修改 ``input_dict["r"]["d"]`` 即可生效（``input_dict`` 是引用）。
        """
        for node in self.data.get("nodes") or []:
            if not isinstance(node, dict) or node.get("type") not in TEXT_NODE_TYPES:
                continue
            for inp in node.get("inputs") or []:
                if not isinstance(inp, dict):
                    continue
                r = inp.get("r")
                if isinstance(r, dict) and isinstance(r.get("d"), str):
                    yield node, inp


def node_span(node):
    """节点的可读定位（报错时用）：type@(x, y)。"""
    try:
        return "%s@(%s,%s)" % (node.get("type"), node.get("x"), node.get("y"))
    except Exception:
        return str(node.get("type"))
