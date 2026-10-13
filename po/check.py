#!/usr/bin/env python3
"""Checks that a catalog po/<domain>/<lang>.po translates exactly the _("…") strings of the source file
named after its domain, in the current directory (ryzenctl, ryzen-control): a missing or fuzzy entry would
show up in English, an unused one is left over from a changed string. Standard library only, like msgfmt.py.

usage: check.py po/<domain>/<lang>.po…
"""
import ast
import os
import sys

from msgfmt import parse


def problems(po):
    src = os.path.basename(os.path.dirname(po))
    ids = set()
    for n in ast.walk(ast.parse(open(src, encoding="utf-8").read(), src)):
        if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "_":
            if n.args and isinstance(n.args[0], ast.Constant):
                ids.add(n.args[0].value)
            else:
                yield "%s:%d: _() of a non-literal string cannot be checked" % (src, n.lineno)
    cat = set(parse(po)) - {""}   # parse() leaves out untranslated and fuzzy entries; "" is the header
    for s in sorted(ids - cat):
        yield "%s: untranslated: %r" % (po, s)
    for s in sorted(cat - ids):
        yield "%s: unused: %r" % (po, s)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    bad = [p for po in sys.argv[1:] for p in problems(po)]
    if bad:
        sys.exit("\n".join(bad))


if __name__ == "__main__":
    main()
