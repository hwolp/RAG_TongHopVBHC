from abc import ABC, abstractmethod
from typing import Optional

from langchain_core.documents import Document as LCDocument


class LLMProviderInterface(ABC):
    @abstractmethod
    def generate_answer(self, question: str, context: str, chat_history: str = "") -> str:
        """Generate an answer from a question, retrieved context, and chat history."""


class RetrieverInterface(ABC):
    @abstractmethod
    def search_context_with_filter(
        self,
        query: str,
        user_id: int,
        user_dept_id: int,
        search_scope: str = "personal",
        k: int = 5,
        session_id: Optional[int] = None,
        extra_doc_ids: Optional[list[int]] = None,
    ) -> tuple[str, list[str]]:
        """Retrieve text context and source document ids for a query."""


class VectorStoreInterface(RetrieverInterface):
    @abstractmethod
    def add_documents(self, documents: list[LCDocument]) -> int:
        """Store already prepared chunks and return the number of stored chunks."""

    @abstractmethod
    def delete_doc_from_index(self, doc_id: int) -> int:
        """Delete all chunks for one document and return the deleted count."""


class FileLoaderInterface(ABC):
    @abstractmethod
    def load(self, file_path: str) -> list[LCDocument]:
        """Load a file into LangChain documents."""


class EmbeddingServiceInterface(ABC):
    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Create an embedding vector for a query."""

