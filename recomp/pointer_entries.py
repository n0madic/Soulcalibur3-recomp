#!/usr/bin/env python3
"""Emit a top-level TOML `entry_points` array with code addresses that are only reachable through
data pointers (vtables, callback tables) and are not in the recompiler's function table.

Without them the recompiled game dies on the first indirect call to such an address
("guest-branch:missing-target ... kind=IndirectCall").

Usage: pointer_entries.py <elf> <register_functions.cpp>   (prints TOML to stdout)
"""
import re
import struct
import sys


def main() -> None:
    elf_path, reg_path = sys.argv[1], sys.argv[2]
    with open(reg_path) as f:
        known = {int(m, 16) for m in re.findall(r"// 0x([0-9a-f]+)\n", f.read())}
    with open(elf_path, "rb") as f:
        d = f.read()

    # ELF32 LE program headers.
    phoff = struct.unpack_from("<I", d, 28)[0]
    phentsize, phnum = struct.unpack_from("<HH", d, 42)
    segs = []
    for i in range(phnum):
        p_type, off, vaddr, _paddr, filesz, _memsz, flags, _align = struct.unpack_from(
            "<IIIIIIII", d, phoff + i * phentsize
        )
        if p_type == 1:
            segs.append((off, vaddr, filesz, flags))

    code_lo = min(v for _, v, _, fl in segs if fl & 1)  # executable segment
    code_hi = max(v + s for _, v, s, fl in segs if fl & 1)

    targets = set()
    for off, vaddr, filesz, flags in segs:
        if flags & 1:  # skip the code segment: only data words are of interest
            continue
        for i in range(0, filesz - 3, 4):
            w = struct.unpack_from("<I", d, off + i)[0]
            if code_lo <= w < code_hi and w % 4 == 0 and w not in known:
                targets.add(w)

    print("entry_points = [")
    for t in sorted(targets):
        print(f'  "ptr_{t:08X}@0x{t:08X}",')
    print("]")
    print(f"# {len(targets)} data-pointer entry points", file=sys.stderr)


if __name__ == "__main__":
    main()
