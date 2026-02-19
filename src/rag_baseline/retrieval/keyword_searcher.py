import math
from collections import Counter
from typing import Any


class KeywordSearcher:
    """Keyword-based search using BM25 algorithm for exact term matching"""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.avg_doc_length = 0.0
        self.doc_lengths: dict[str, int] = {}
        self.doc_freqs: dict[str, int] = {}
        self.idf: dict[str, float] = {}
        self.num_docs = 0

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization"""
        return text.lower().split()

    def fit(self, documents: list[dict[str, Any]]) -> None:
        """Build keyword search index from documents"""
        self.num_docs = len(documents)
        total_length = 0

        doc_freqs: dict[str, set[str]] = {}

        for doc in documents:
            doc_id = doc["chunk_id"]
            content = doc["content"]
            tokens = self._tokenize(content)

            self.doc_lengths[doc_id] = len(tokens)
            total_length += len(tokens)

            for token in set(tokens):
                if token not in doc_freqs:
                    doc_freqs[token] = set()
                doc_freqs[token].add(doc_id)

        self.avg_doc_length = total_length / self.num_docs if self.num_docs > 0 else 0

        for term, doc_set in doc_freqs.items():
            self.doc_freqs[term] = len(doc_set)
            self.idf[term] = math.log(
                (self.num_docs - len(doc_set) + 0.5) / (len(doc_set) + 0.5) + 1
            )

    def score(self, query: str, documents: list[dict[str, Any]]) -> dict[str, float]:
        """Score documents against query using keyword matching (BM25)"""
        query_tokens = self._tokenize(query)
        scores: dict[str, float] = {}

        for doc in documents:
            doc_id = doc["chunk_id"]
            content = doc["content"]
            doc_tokens = self._tokenize(content)
            doc_length = self.doc_lengths.get(doc_id, len(doc_tokens))

            score = 0.0
            term_freqs = Counter(doc_tokens)

            for term in query_tokens:
                if term not in self.idf:
                    continue

                tf = term_freqs.get(term, 0)
                idf = self.idf[term]

                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (
                    1 - self.b + self.b * (doc_length / self.avg_doc_length)
                )

                score += idf * (numerator / denominator)

            scores[doc_id] = score

        return scores
