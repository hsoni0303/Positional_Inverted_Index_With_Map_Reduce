"""Shared text normalization for indexing and querying (must be identical for both)."""

import re

import nltk


def _ensure(resource, path):
    try:
        nltk.data.find(path)
    except LookupError:
        nltk.download(resource, quiet=True)


_ensure("stopwords", "corpora/stopwords")
_ensure("wordnet", "corpora/wordnet")

from nltk.corpus import stopwords  # noqa: E402
from nltk.stem import WordNetLemmatizer  # noqa: E402

STOP_WORDS = set(stopwords.words("english"))
_lemmatize = WordNetLemmatizer().lemmatize
_WORD = re.compile(r"[a-z]+")


def normalize(text):
    """Lowercase, keep alphabetic tokens, drop stopwords, lemmatize.

    Positions in the index are offsets into this list, so phrase queries
    match on adjacency after stopword removal ("state of the art" ~ "state art").
    """
    return [_lemmatize(t) for t in _WORD.findall(text.lower()) if t not in STOP_WORDS]
