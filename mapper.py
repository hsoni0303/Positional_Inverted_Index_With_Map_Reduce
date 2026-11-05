#!/usr/bin/env python3
"""Hadoop-streaming mapper: emit `term \\t doc_id \\t position` for every term."""

import os
import sys

from text import normalize


def map_document(doc_id, lines, start=0):
    """Yield (term, doc_id, position); positions continue across lines."""
    pos = start
    for line in lines:
        for term in normalize(line):
            yield term, doc_id, pos
            pos += 1


def doc_id_from_path(path):
    """'.../20_newsgroups/sci.space/59873' -> 'sci.space/59873'."""
    parent, name = os.path.split(path)
    return f"{os.path.basename(parent)}/{name}"


if __name__ == "__main__":
    # Hadoop exposes the current input file via an env var (name differs by version).
    path = os.environ.get("mapreduce_map_input_file") or os.environ.get("map_input_file", "stdin")
    for term, doc, pos in map_document(doc_id_from_path(path), sys.stdin):
        print(f"{term}\t{doc}\t{pos}")
