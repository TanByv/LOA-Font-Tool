"""FontMap.xml parsing / generation."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from xml.sax.saxutils import quoteattr

_ATTR = {
    "Key": "key",
    "File": "file",
    "SizeCorrectionRatio": "size_correction",
    "LeadingCorrection": "leading_correction",
}


@dataclass
class FontItem:
    key: str
    file: str
    size_correction: str = ""
    leading_correction: str = ""
    extra: dict = field(default_factory=dict)  # unknown attributes are preserved


# The values the old tool shipped with (English/Spanish layout).
LEGACY_FONT = "ExuberanceF-Regular.ttf"
LEGACY_DEFAULTS = [
    FontItem("$YG760", LEGACY_FONT),
    FontItem("$YG760_12pt", LEGACY_FONT, "120"),
    FontItem("$YG330", LEGACY_FONT),
    FontItem("$YoonGasiIIM", LEGACY_FONT, "", "-200"),
    FontItem("$YoonGasiIIM_Small2pt", LEGACY_FONT, "120", "-200"),
]


def parse(data: bytes) -> list[FontItem]:
    root = ET.fromstring(data)
    if root.tag != "FontMap":
        raise ValueError(f"Root element is <{root.tag}>, expected <FontMap>")
    items = []
    for el in root.findall("Item"):
        item = FontItem("", "")
        for attr, value in el.attrib.items():
            if attr in _ATTR:
                setattr(item, _ATTR[attr], value)
            else:
                item.extra[attr] = value
        items.append(item)
    return items


def _num(text: str) -> bool:
    try:
        float(text)
        return True
    except ValueError:
        return False


def validate(items: list[FontItem]) -> None:
    if not items:
        raise ValueError("FontMap has no rows.")
    seen = set()
    for it in items:
        if not it.key.strip():
            raise ValueError("A FontMap row has an empty Key.")
        if not it.file.strip():
            raise ValueError(f"Row {it.key}: File is empty.")
        if it.key in seen:
            raise ValueError(f"Duplicate Key: {it.key}")
        seen.add(it.key)
        for label, val in (
            ("Size correction", it.size_correction),
            ("Leading correction", it.leading_correction),
        ):
            if val.strip() and not _num(val.strip()):
                raise ValueError(f"Row {it.key}: {label} '{val}' is not a number.")


def build(items: list[FontItem]) -> str:
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<FontMap>"]
    for it in items:
        attrs = [("Key", it.key.strip()), ("File", it.file.strip())]
        if it.size_correction.strip():
            attrs.append(("SizeCorrectionRatio", it.size_correction.strip()))
        if it.leading_correction.strip():
            attrs.append(("LeadingCorrection", it.leading_correction.strip()))
        attrs += list(it.extra.items())
        lines.append(
            "    <Item " + " ".join(f"{k}={quoteattr(v)}" for k, v in attrs) + " />"
        )
    lines.append("</FontMap>")
    return "\n".join(lines) + "\n"
