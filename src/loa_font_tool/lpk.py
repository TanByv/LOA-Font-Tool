"""Core LPK handling: QuickBMS wrapper, archive listing and entry replacement.

Entries are always located by their *path inside the archive* (never by a
hard-coded index), so the tool keeps working when the game adds or reorders files.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path


class LpkError(RuntimeError):
    pass


# (KEY, BASE) pairs per game client, taken from the extract/repack scripts.
PROFILES = {
    "Steam (Global)": (
        "83657ea6ffa1e671375c689a2e99a598",
        "1069d88738c5c75f82b44a1f0a382768",
    ),
    "Russia": ("a7f33db20dfb711a16d5d3dd3d4cef4d", "ee36ace0d87a9eaea565e6884a058b63"),
    "Japan": ("c66e7c755883b5a92227b6c1c71c1d94", "51f912aba46f144bba8c3d6dcbf34728"),
    "Taiwan": ("2d7ea2e4d31c53913fd2995ca031f777", "53f421141b5159fc5851ce2fd29c9e28"),
    "Korea": ("287f1d85be26e55a1d994e9e1bfd0df1", "6ce3db2fbe338fba87edf2abf6453bfa"),
    "China": ("a2e587d2fac8d6836cad3fd144f0cf2b", "c7db380e7d8d9e4771c7eaf5b1f3a78b"),
}
DEFAULT_PROFILE = "Steam (Global)"

# Marker the packer writes over the first 4 chars of a replaced entry's file name.
REPLACED_PREFIX = "1_1_"

EXTRACT_SCRIPT = r"""
string KEY = "@KEY@"
string BASE = "@BASE@"
quickbmsver "0.12 -64"
math ENTRY = 528
string BASE h BASE

get FILES long
encryption blowfish KEY
xmath SIZE "ENTRY * FILES"
log MEMORY_FILE 4 SIZE
encryption "" ""
math MEM = -1

xmath OFFSET "SIZE + 8"
for i = 0 < FILES
	get NAMEZ long MEM
	getdstring NAME NAMEZ MEM
	padding ENTRY MEM
	goto -16 MEM SEEK_CUR
	get DUMMY_OFFSET long MEM
	get SIZE long MEM
	get ENSIZE long MEM
	get ZSIZE long MEM
	if ZSIZE != 0
		encryption blowfish KEY
		clog NAME OFFSET ZSIZE SIZE 0 ENSIZE
	else
		log MEMORY_FILE3 OFFSET ENSIZE
		callfunction decrypt 1
	endif
	encryption "" ""
	math OFFSET + ENSIZE
next i

startfunction decrypt
	log MEMORY_FILE2 0 0
	string TMP_NAME = NAME
	string TMP_NAME ! "_"
	string TMP_NAME % "."
	set TMP_NAME to_unicode TMP_NAME
	encryption md5 TMP_NAME
	encryption "" ""
	string MD = QUICKBMS_HASH

	for x = 0 < 16
		xmath TMP "15 - x"
		getvarchr K BASE x
		getvarchr M MD TMP
		math K ^ M
		putvarchr MEMORY_FILE2 x K
	next x

	getdstring AES_KEY 16 MEMORY_FILE2
	string AES_KEY 0b AES_KEY
	string AES_KEY l AES_KEY
	encryption sha256 AES_KEY
	encryption "" ""
	string AES_KEY 0= QUICKBMS_HASH

	math CUR_OFF = 0
	math BLOCK = 1024

	for CUR_OFF = CUR_OFF < ENSIZE
		append
		encryption aes_256_cbc AES_KEY "" 0 32
		log NAME CUR_OFF BLOCK MEMORY_FILE3
		encryption "" ""
		append
		math CUR_OFF + BLOCK
	next
endfunction
"""

# Packs the input file over entry number @TARGET_INDEX@ (the old entry is renamed
# and a new one is appended). Output: <ARCHIVE stem>_mod.lpk
PACK_SCRIPT = r"""
string ARCHIVE = "@ARCHIVE@"
string KEY = "@KEY@"
string BASE = "@BASE@"
quickbmsver "0.12 -64"
get FILE_NAME filename
open FDSE ARCHIVE 1
math ENTRY = 528
string BASE h BASE
get FILES long 1
xmath SIZE "FILES * ENTRY"
encryption blowfish KEY
log MEMORY_FILE 4 SIZE 1
encryption "" ""
math MEM = -1
math TARGET_INDEX = @TARGET_INDEX@
math COUNT = 0
for i = 0 < FILES
	get NAMEZ long MEM
	getdstring NAME NAMEZ MEM
	padding ENTRY MEM
	string NAME ! "\"
	if i == TARGET_INDEX
		math COUNT = i
		padding ENTRY MEM
		goto -4 MEM SEEK_CUR
		get ENC long MEM
		print "Targeting file: %NAME%"
		break
	endif
next i
if COUNT != TARGET_INDEX
	print "Failed to find target file in the archive!"
	cleanexit
endif
xmath INFO_OFF "COUNT * ENTRY"
log MEMORY_FILE2 INFO_OFF ENTRY MEM
goto INFO_OFF MEM
findloc OFFSET string NAME MEM ""
putvarchr MEMORY_FILE OFFSET 0x5F315F31 long
math FILES + 1
append -1
	put FILES long MEM
append
append
	log MEMORY_FILE 0 ENTRY MEMORY_FILE2
append
get MODSIZE asize
get SIZE asize MEM
xmath INFO_OFF "SIZE - 12"
if ENC = 0
	xmath CHECK "MODSIZE % 1024"
	if CHECK > 0
		print "\nDatabase should be aligned to size multiple of 1024!"
		cleanexit
	endif
	putvarchr MEMORY_FILE INFO_OFF MODSIZE long
	math INFO_OFF + 4
	putvarchr MEMORY_FILE INFO_OFF MODSIZE long
	math INFO_OFF + 4
	putvarchr MEMORY_FILE INFO_OFF 0 long
else
	comtype zlib_compress
	clog MEMORY_FILE5 0 MODSIZE MODSIZE
	get ZSIZE asize MEMORY_FILE5
	math ENSIZE = ZSIZE
	math ENSIZE x 8
	math OFFSET = ZSIZE
	for OFFSET = OFFSET < ENSIZE
		putvarchr MEMORY_FILE5 OFFSET 0
	next OFFSET
	putvarchr MEMORY_FILE INFO_OFF MODSIZE long
	math INFO_OFF + 4
	putvarchr MEMORY_FILE INFO_OFF ENSIZE long
	math INFO_OFF + 4
	putvarchr MEMORY_FILE INFO_OFF ZSIZE long
endif
math INFO_OFF + 4
putvarchr MEMORY_FILE INFO_OFF 0 long
string NAME = ARCHIVE
string NAME % "."
string NAME + "_mod.lpk"
log NAME 0 4 MEM
get FSIZE1 asize 1
xmath OFF "(FILES - 1) * ENTRY + 8"
math FSIZE1 - OFF
append
	encryption blowfish KEY "" 1
	log NAME 4 SIZE MEM
	encryption "" ""
	log NAME OFF FSIZE1 1
	if ENC = 0
		callfunction get_key 1
		math CUR_OFF = 0
		math BLOCK = 1024
		for CUR_OFF = CUR_OFF < MODSIZE
			encryption aes_256_cbc AES_KEY "" 1 32
			log NAME CUR_OFF BLOCK
			encryption "" ""
			math CUR_OFF + BLOCK
		next
	else
		encryption blowfish KEY "" 1
		log NAME 0 ENSIZE MEMORY_FILE5
	endif
append
startfunction get_key
	log MEMORY_FILE10 0 0
	string TMP_NAME = FILE_NAME
	string TMP_NAME ! "_"
	string TMP_NAME % "."
	set TMP_NAME to_unicode TMP_NAME
	encryption md5 TMP_NAME
	encryption "" ""
	string MD = QUICKBMS_HASH
	for x = 0 < 16
		xmath TMP "15 - x"
		getvarchr K BASE x
		getvarchr M MD TMP
		math K ^ M
		putvarchr MEMORY_FILE10 x K
	next x
	getdstring AES_KEY 16 MEMORY_FILE10
	string AES_KEY 0b AES_KEY
	string AES_KEY l AES_KEY
	encryption sha256 AES_KEY
	encryption "" ""
	string AES_KEY 0= QUICKBMS_HASH
endfunction
"""


# Listing / lookup helpers


@dataclass(frozen=True)
class Entry:
    index: int
    offset: int
    size: int
    name: str

    @property
    def basename(self) -> str:
        return self.name.replace("/", "\\").rsplit("\\", 1)[-1]

    @property
    def folder(self) -> str:
        n = self.name.replace("/", "\\")
        return n.rsplit("\\", 1)[0] if "\\" in n else ""


def norm(path: str) -> str:
    return path.replace("/", "\\").strip("\\").lower()


_LINE = re.compile(r"^\s*([0-9a-fA-F]{16})\s+(\d+)\s+(\S.*?)\s*$")
_COUNT = re.compile(r"(\d+)\s+files?\s+found", re.IGNORECASE)


def parse_listing(text: str) -> list[Entry]:
    entries: list[Entry] = []
    for line in text.splitlines():
        m = _LINE.match(line)
        if m:
            entries.append(
                Entry(len(entries), int(m.group(1), 16), int(m.group(2)), m.group(3))
            )
    m = _COUNT.search(text)
    if m and int(m.group(1)) != len(entries):
        raise LpkError(
            f"Listing mismatch: QuickBMS reports {m.group(1)} files but {len(entries)} were parsed."
        )
    return entries


def find_entry(entries: Sequence[Entry], path: str) -> Entry:
    """Return the entry with this exact path (case-insensitive). If duplicates exist,
    the most recently appended one wins."""
    wanted = norm(path)
    matches = [e for e in entries if norm(e.name) == wanted]
    if matches:
        return matches[-1]
    base = wanted.rsplit("\\", 1)[-1]
    similar = [e.name for e in entries if e.basename.lower() == base][:6]
    hint = ("\nSimilar entries: " + ", ".join(similar)) if similar else ""
    raise LpkError(f"Entry not found in archive: {path}{hint}")


def is_modded(entries: Sequence[Entry]) -> bool:
    return any(e.basename.startswith(REPLACED_PREFIX) for e in entries)


# QuickBMS wrapper

Source = Path | bytes


class QuickBMS:
    def __init__(
        self, exe, profile: str = DEFAULT_PROFILE, log: Callable[[str], None] = print
    ):
        if profile not in PROFILES:
            raise LpkError(f"Unknown key profile: {profile}")
        self.exe = str(exe)
        self.key, self.base = PROFILES[profile]
        self.log = log

    # -- internals ---------------------------------------------------------- #
    def _script(self, template: str, path: Path, **extra) -> Path:
        text = template.replace("@KEY@", self.key).replace("@BASE@", self.base)
        for k, v in extra.items():
            text = text.replace(f"@{k}@", str(v))
        with open(path, "w", encoding="ascii", newline="\n") as f:
            f.write(text.lstrip("\n"))
        return path

    def _run(self, args, cwd: Path) -> str:
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        try:
            p = subprocess.run(
                [str(a) for a in args],
                cwd=str(cwd),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdin=subprocess.DEVNULL,
                timeout=600,
                check=False,
                creationflags=flags,
            )
        except FileNotFoundError:
            raise LpkError(f"QuickBMS executable not found: {self.exe}")
        except subprocess.TimeoutExpired:
            raise LpkError("QuickBMS timed out.")
        out = (p.stdout or "") + "\n" + (p.stderr or "")
        if p.returncode != 0:
            raise LpkError(
                f"QuickBMS exited with code {p.returncode}:\n{out.strip()[-800:]}"
            )
        return out

    # public API
    def list_entries(self, archive: Path) -> list[Entry]:
        with tempfile.TemporaryDirectory(prefix="loa_list_") as td:
            td = Path(td)
            script = self._script(EXTRACT_SCRIPT, td / "extract.bms")
            out = self._run([self.exe, "-l", script, archive, td], td)
        entries = parse_listing(out)
        if not entries:
            raise LpkError(
                "No files found. Wrong key profile or not a valid LPK?\n"
                + out.strip()[-500:]
            )
        return entries

    def extract(self, archive: Path, mask: str, dest: Path) -> list[Path]:
        """Extract entries whose name matches the wildcard `mask` into `dest`."""
        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)
        script = self._script(EXTRACT_SCRIPT, dest / "_extract.bms")
        self._run([self.exe, "-o", "-f", mask, script, archive, dest], dest)
        return [p for p in dest.rglob("*") if p.is_file() and p.name != "_extract.bms"]

    def replace(
        self, source: Path, replacements: Sequence[tuple[str, Source]], dest: Path
    ) -> None:
        """Replace each (archive path, new content) in a copy of `source`; write to `dest`.

        The target index is re-resolved from the current archive before every pass and
        every pass is verified afterwards."""
        with tempfile.TemporaryDirectory(prefix="loa_pack_") as td:
            work = Path(td)
            current = work / "input.lpk"
            shutil.copy2(source, current)

            for n, (entry_path, content) in enumerate(replacements, 1):
                entries = self.list_entries(current)
                target = find_entry(entries, entry_path)
                self.log(
                    f"[{n}/{len(replacements)}] {target.name}  (index {target.index})"
                )

                # Must sit next to input.lpk: PACK_SCRIPT uses `open FDSE ARCHIVE`,
                # which QuickBMS resolves in the replacement file's directory.
                staged = work / target.basename
                if isinstance(content, (bytes, bytearray)):
                    staged.write_bytes(content)
                else:
                    shutil.copy2(content, staged)
                new_size = staged.stat().st_size

                script = self._script(
                    PACK_SCRIPT,
                    work / "pack.bms",
                    ARCHIVE="input.lpk",
                    TARGET_INDEX=target.index,
                )
                out_file = work / "input_mod.lpk"
                out_file.unlink(missing_ok=True)
                out = self._run([self.exe, "-o", script, staged, work], work)
                if re.search(r"Failed to find target|should be aligned", out):
                    raise LpkError(
                        f"Packing failed for {target.name}:\n{out.strip()[-500:]}"
                    )
                if not out_file.exists():
                    raise LpkError(
                        f"QuickBMS produced no output for {target.name}:\n{out.strip()[-500:]}"
                    )
                current.unlink()
                shutil.move(str(out_file), str(current))

                # verify the pass
                after = self.list_entries(current)
                last = after[-1]
                if (
                    len(after) != len(entries) + 1
                    or norm(last.name) != norm(target.name)
                    or last.size != new_size
                ):
                    raise LpkError(
                        f"Verification failed for {target.name}: expected a new last entry of {new_size} bytes, "
                        f"got '{last.name}' ({last.size} bytes). Aborting; nothing was saved."
                    )
                self.log(f"    ok - appended {last.name} ({last.size} bytes)")

            dest = Path(dest)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(current, dest)
