from claude_retriever.searcher.types import *
from dataclasses import dataclass

@dataclass
class SearchResult:
    """
    A single search result.
    """
    content: str
    score: float
