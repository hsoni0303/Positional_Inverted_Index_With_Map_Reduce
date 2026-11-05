import os
import subprocess
import sys
from pathlib import Path

import pytest

from index import build, load
from query import Query, f_and, f_or, phrase

ROOT = Path(__file__).parent.parent


@pytest.fixture
def corpus(tmp_path):
    docs = {
        "space/1": "NASA launched the space shuttle into orbit.",
        "space/2": "The shuttle program ended; space exploration continues.",
        "graphics/1": "Rendering a shuttle model in 3D graphics.",
    }
    for doc_id, text in docs.items():
        p = tmp_path / "corpus" / doc_id
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    build(tmp_path / "corpus", tmp_path / "index.tsv")
    return load(tmp_path / "index.tsv")


def test_positions_are_per_document(corpus):
    # stopwords removed: nasa(0) launched(1) space(2) shuttle(3) orbit(4)
    assert corpus["shuttle"]["space/1"] == [3]
    assert corpus["shuttle"]["space/2"] == [0]  # not leaked from other docs


def test_merge_operators():
    assert f_and([1, 3, 5, 7], [3, 4, 7]) == [3, 7]
    assert f_or([1, 3], [2, 3]) == [1, 2, 3]


def test_phrase_requires_adjacency(corpus):
    assert phrase(corpus, ["space", "shuttle"]) == ["space/1"]
    assert phrase(corpus, ["shuttle", "space"]) == []


def test_boolean_queries(corpus):
    q = Query(corpus)
    assert q("shuttle") == ["graphics/1", "space/1", "space/2"]
    assert q("shuttle AND NOT graphics") == ["space/1", "space/2"]
    assert q('"space shuttle" OR rendering') == ["graphics/1", "space/1"]
    assert q("(orbit OR exploration) shuttle") == ["space/1", "space/2"]
    assert q("Shuttles") == q("shuttle")  # normalized like the index


def test_syntax_errors(corpus):
    q = Query(corpus)
    for bad in ["(shuttle", "shuttle AND", "shuttle )"]:
        with pytest.raises(SyntaxError):
            q(bad)


def test_streaming_scripts_match_local_build(corpus, tmp_path):
    """mapper.py | sort | reducer.py (as Hadoop runs them) == local build."""
    mapped = ""
    for f in sorted((tmp_path / "corpus").rglob("*")):
        if f.is_file():
            mapped += subprocess.run(
                [sys.executable, str(ROOT / "mapper.py")], input=f.read_text(),
                capture_output=True, text=True, cwd=ROOT, check=True,
                env={**os.environ, "map_input_file": str(f)},
            ).stdout
    shuffled = "".join(sorted(mapped.splitlines(keepends=True),
                              key=lambda l: (l.split("\t")[0], l.split("\t")[1], int(l.split("\t")[2]))))
    reduced = subprocess.run([sys.executable, str(ROOT / "reducer.py")], input=shuffled,
                             capture_output=True, text=True, cwd=ROOT, check=True).stdout
    assert reduced == (tmp_path / "index.tsv").read_text()
