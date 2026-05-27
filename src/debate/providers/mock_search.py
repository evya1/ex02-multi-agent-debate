"""
MockSearchProvider — deterministic fake search results for offline tests.

Returns a fixed list of SearchResult objects so tests never hit DuckDuckGo.
"""
from __future__ import annotations

from debate.providers.base import AbstractSearchProvider, SearchResult

_DEFAULT_RESULTS = [
    SearchResult(
        source="Mock Journal",
        quote="Studies confirm AI benefits in healthcare.",
        url="https://example.com/1",
    ),
    SearchResult(
        source="Mock Times",
        quote="Experts warn of AI safety risks.",
        url="https://example.com/2",
    ),
]


class MockSearchProvider(AbstractSearchProvider):
    """Offline-safe search provider for tests."""

    def __init__(self, results: list[SearchResult] | None = None) -> None:
        self._results = results or _DEFAULT_RESULTS
        self.queries: list[str] = []        # record every query for assertions

    def name(self) -> str:
        return "mock_search"

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        self.queries.append(query)
        return self._results[:max_results]
