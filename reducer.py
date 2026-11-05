#!/usr/bin/env python3
"""Hadoop-streaming reducer: group sorted mapper output into positional postings.

Input (sorted by term):  term \\t doc_id \\t position
Output:                  term \\t {"doc_id": [pos, ...], ...}   (JSON, sorted)

Hadoop guarantees all lines for a term arrive contiguously, so only one
term's postings are held in memory at a time.
"""

import json
import sys
from itertools import groupby


def reduce_sorted(lines):
    rows = (line.rstrip("\n").split("\t") for line in lines if line.strip())
    for term, group in groupby(rows, key=lambda r: r[0]):
        postings = {}
        for _, doc, pos in group:
            postings.setdefault(doc, []).append(int(pos))
        yield term, {doc: sorted(p) for doc, p in sorted(postings.items())}


if __name__ == "__main__":
    for term, postings in reduce_sorted(sys.stdin):
        print(f"{term}\t{json.dumps(postings, separators=(',', ':'))}")
