"""Run with:  python -m unittest loa_font_tool.test_core  (no QuickBMS or GUI needed)"""

import unittest

from . import fontmap, lpk

OLD = """
  offset           filesize   filename
--------------------------------------
  00000000000037b8 2893776    Binaries\\Fonts\\BMKkubulimTTF.ttf
  0000000000a27ea8 566        Binaries\\Fonts\\Chinese\\FontMap.xml
  0000000000a27f80 54964      Binaries\\Fonts\\English\\ExuberanceF-Regular.ttf
  0000000000a2ee10 622        Binaries\\Fonts\\English\\FontMap.xml
- 4 files found in 0 seconds
"""
MODDED_TAIL = """
  0000000000a282c8 566        Binaries\\Fonts\\Chinese\\1_1_Map.xml
  0000000001dd9b18 479        Binaries\\Fonts\\English\\FontMap.xml
- 2 files found in 0 seconds
"""


class Core(unittest.TestCase):
    def test_lookup_by_name_not_index(self):
        e = lpk.parse_listing(OLD)
        self.assertEqual(
            lpk.find_entry(e, "Binaries/Fonts/English/FontMap.xml").index, 3
        )
        self.assertEqual(
            lpk.find_entry(e, r"binaries\fonts\english\exuberancef-regular.ttf").index,
            2,
        )
        with self.assertRaises(lpk.LpkError):
            lpk.find_entry(e, r"Binaries\Fonts\English\Nope.ttf")

    def test_modded_detection(self):
        self.assertFalse(lpk.is_modded(lpk.parse_listing(OLD)))
        self.assertTrue(lpk.is_modded(lpk.parse_listing(MODDED_TAIL)))

    def test_count_mismatch(self):
        with self.assertRaises(lpk.LpkError):
            lpk.parse_listing(OLD.replace("4 files", "9 files"))

    def test_fontmap_roundtrip(self):
        xml = fontmap.build(fontmap.LEGACY_DEFAULTS)
        items = fontmap.parse(xml.encode())
        self.assertEqual(len(items), 5)
        self.assertEqual(items[1].size_correction, "120")
        fontmap.validate(items)
        items[0].size_correction = "abc"
        with self.assertRaises(ValueError):
            fontmap.validate(items)

    def test_scripts_fully_substituted(self):
        qb = lpk.QuickBMS("x")
        for tpl in (lpk.EXTRACT_SCRIPT, lpk.PACK_SCRIPT):
            text = (
                tpl.replace("@KEY@", qb.key)
                .replace("@BASE@", qb.base)
                .replace("@ARCHIVE@", "a")
                .replace("@TARGET_INDEX@", "5")
            )
            self.assertNotIn("@", text)


if __name__ == "__main__":
    unittest.main()
