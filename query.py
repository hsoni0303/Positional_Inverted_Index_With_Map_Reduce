"""Boolean + phrase queries over the positional index.

Grammar (NOT > AND > OR; adjacent terms are implicitly ANDed):
    expr   := and ("OR" and)*
    and    := unary (["AND"] unary)*
    unary  := "NOT" unary | "(" expr ")" | '"phrase"' | word

  python query.py index.tsv '"space shuttle" AND (nasa OR orbit) NOT launch'
  python query.py index.tsv          # interactive
"""

import re
import sys

from index import load
from text import normalize


# -- postings algebra (sorted doc-id lists, linear merges) ----------------------

def f_and(a, b):
    i = j = 0
    out = []
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            out.append(a[i])
            i += 1
            j += 1
        elif a[i] < b[j]:
            i += 1
        else:
            j += 1
    return out


def f_or(a, b):
    return sorted(set(a) | set(b))


def f_not(a, universe):
    excluded = set(a)
    return [d for d in universe if d not in excluded]


def phrase(index, terms):
    """Docs where terms appear at consecutive positions (positional intersection)."""
    if not terms or any(t not in index for t in terms):
        return []
    docs = sorted(index[terms[0]])
    for t in terms[1:]:
        docs = f_and(docs, sorted(index[t]))
    hits = []
    for d in docs:
        starts = set(index[terms[0]][d])
        for k, t in enumerate(terms[1:], start=1):
            starts &= {p - k for p in index[t][d]}
        if starts:
            hits.append(d)
    return hits


# -- parser ------------------------------------------------------------------

_TOKEN = re.compile(r'"[^"]*"|\(|\)|[^\s()"]+')


class Query:
    def __init__(self, index):
        self.index = index
        self.universe = sorted({d for p in index.values() for d in p})

    def __call__(self, text):
        self.tokens, self.i = _TOKEN.findall(text), 0
        result = self._or()
        if self.i != len(self.tokens):
            raise SyntaxError(f"unexpected {self.tokens[self.i]!r}")
        return result

    def _peek(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def _next(self):
        self.i += 1
        return self.tokens[self.i - 1]

    def _or(self):
        result = self._and()
        while self._peek() == "OR":
            self._next()
            result = f_or(result, self._and())
        return result

    def _and(self):
        result = self._unary()
        while self._peek() not in (None, "OR", ")"):
            if self._peek() == "AND":
                self._next()
            result = f_and(result, self._unary())
        return result

    def _unary(self):
        tok = self._next() if self._peek() else None
        if tok is None:
            raise SyntaxError("unexpected end of query")
        if tok == "NOT":
            return f_not(self._unary(), self.universe)
        if tok == "(":
            result = self._or()
            if self._peek() != ")":
                raise SyntaxError("missing ')'")
            self._next()
            return result
        if tok.startswith('"'):
            return phrase(self.index, normalize(tok.strip('"')))
        terms = normalize(tok)
        if not terms:  # stopword or punctuation: matches nothing
            return []
        return sorted(self.index.get(terms[0], {}))


if __name__ == "__main__":
    q = Query(load(sys.argv[1] if len(sys.argv) > 1 else "index.tsv"))
    queries = sys.argv[2:] or iter(lambda: input("query> "), "")
    for text in queries:
        try:
            docs = q(text)
            print(f"{len(docs)} docs: {docs}")
        except SyntaxError as e:
            print(f"syntax error: {e}")
