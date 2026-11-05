"""Build the index locally (map -> shuffle/sort -> reduce) and load it back.

  python index.py 20_newsgroups index.tsv

Runs the exact same mapper and reducer code that Hadoop streaming runs.
"""

import json
import sys
from pathlib import Path

from mapper import doc_id_from_path, map_document
from reducer import reduce_sorted


def build(corpus_dir, out_path):
    # Map
    pairs = []
    for path in sorted(p for p in Path(corpus_dir).rglob("*") if p.is_file() and not p.name.startswith(".")):
        with open(path, encoding="latin-1") as f:
            pairs += map_document(doc_id_from_path(str(path)), f)
    # Shuffle & sort (Hadoop sorts mapper output by key between the phases)
    pairs.sort(key=lambda t: (t[0], t[1], t[2]))
    # Reduce
    lines = (f"{t}\t{d}\t{p}" for t, d, p in pairs)
    with open(out_path, "w") as out:
        for term, postings in reduce_sorted(lines):
            out.write(f"{term}\t{json.dumps(postings, separators=(',', ':'))}\n")


def load(path):
    index = {}
    with open(path) as f:
        for line in f:
            term, postings = line.rstrip("\n").split("\t", 1)
            index[term] = json.loads(postings)
    return index


if __name__ == "__main__":
    corpus, out = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "index.tsv"
    build(corpus, out)
    idx = load(out)
    docs = {d for p in idx.values() for d in p}
    print(f"Indexed {len(docs)} documents, {len(idx)} terms -> {out}")
