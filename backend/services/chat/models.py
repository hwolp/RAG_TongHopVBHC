from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievedContext:
    context: str
    sources: list[str]


@dataclass(frozen=True)
class GeneratedAnswer:
    answer: str
    sources: list[str]


@dataclass(frozen=True)
class ChatAnswerResult:
    answer: str
    sources: list[str]
    session_id: int
    session_title: str
    attached_docs: int

