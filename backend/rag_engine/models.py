from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DocumentIndexMetadata:
    doc_id: int
    owner_id: int
    department_id: int
    scope: str
    tags: str = ""
    session_id: Optional[int] = None

    def as_chroma_metadata(self, chunk_strategy: str) -> dict:
        return {
            "doc_id": self.doc_id,
            "owner_id": self.owner_id,
            "department_id": self.department_id,
            "scope": self.scope,
            "tags": self.tags or "",
            "session_id": self.session_id,
            "chunk_strategy": chunk_strategy,
        }


@dataclass(frozen=True)
class SearchResult:
    context: str
    sources: list[str]

