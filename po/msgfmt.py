#!/usr/bin/env python3
"""Minimal .po → .mo compiler (standard library only), so that building and installing the
translations needs neither GNU gettext nor Babel.

usage: msgfmt.py INPUT.po OUTPUT.mo

Supports what our catalogs use: plain msgid/msgstr pairs (multi-line string continuation,
C escapes), msgctxt (stored as ctxt\\x04id), comments. msgid_plural is rejected on purpose
(we do not use plurals; add support here if a catalog ever needs them). Untranslated and
fuzzy entries are skipped, like GNU msgfmt does.
"""
import ast
import struct
import sys


def parse(path):
    entries, cur, key, fuzzy = {}, {}, None, False
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    lines.append("")   # flushes the last entry

    def flush():
        nonlocal cur, fuzzy
        if "msgid" in cur and "msgstr" in cur and not fuzzy:
            msgid = cur["msgid"]
            if "msgctxt" in cur:
                msgid = cur["msgctxt"] + "\x04" + msgid
            if cur["msgstr"] or msgid == "":
                entries[msgid] = cur["msgstr"]
        cur, fuzzy = {}, False

    for n, line in enumerate(lines, 1):
        s = line.strip()
        if not s:
            flush()
            continue
        if s.startswith("#"):
            if s.startswith("#,") and "fuzzy" in s:
                fuzzy = True
            continue
        if s.startswith('"'):
            if key is None:
                sys.exit("%s:%d: string continuation without a keyword" % (path, n))
            cur[key] += ast.literal_eval(s)   # PO strings use the same escapes as C/Python
            continue
        word, _, rest = s.partition(" ")
        if word == "msgid_plural" or word.startswith("msgstr["):
            sys.exit("%s:%d: plural forms are not supported" % (path, n))
        if word not in ("msgid", "msgstr", "msgctxt"):
            sys.exit("%s:%d: unexpected keyword %r" % (path, n, word))
        key = word
        cur[key] = ast.literal_eval(rest.strip())
    return entries


def write_mo(entries, path):
    # Keys sorted by their UTF-8 bytes, as GNU msgfmt does (gettext bisects on the original table).
    items = sorted((k.encode("utf-8"), v.encode("utf-8")) for k, v in entries.items())
    n = len(items)
    header_size = 7 * 4
    table_size = n * 8
    ids_offset = header_size + 2 * table_size
    ids, strs, id_table, str_table = b"", b"", b"", b""
    for k, v in items:
        id_table += struct.pack("<II", len(k), ids_offset + len(ids))
        ids += k + b"\0"
    strs_offset = ids_offset + len(ids)
    for k, v in items:
        str_table += struct.pack("<II", len(v), strs_offset + len(strs))
        strs += v + b"\0"
    header = struct.pack("<7I", 0x950412DE, 0, n, header_size, header_size + table_size, 0, 0)
    with open(path, "wb") as f:
        f.write(header + id_table + str_table + ids + strs)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    entries = parse(sys.argv[1])
    if "" not in entries or "charset=UTF-8" not in entries[""]:
        sys.exit("%s: the header entry must declare charset=UTF-8" % sys.argv[1])
    write_mo(entries, sys.argv[2])


if __name__ == "__main__":
    main()
