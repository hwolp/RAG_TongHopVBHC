from langchain_community.llms import Ollama
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TEMPERATURE, OLLAMA_TIMEOUT_SECONDS
from contracts.rag import LLMProviderInterface
from services.rag.prompt_builder import PromptBuilder


class OllamaAI(LLMProviderInterface):
    def __init__(self, model_name=None, prompt_builder: PromptBuilder | None = None):
        self.llm = Ollama(
            model=model_name or OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            timeout=OLLAMA_TIMEOUT_SECONDS,
            temperature=OLLAMA_TEMPERATURE,  # 0 = deterministic, bám sát context
        )
        self.prompt_builder = prompt_builder or PromptBuilder()

    def generate_answer(self, question: str, context: str, chat_history: str = ""):
        """Generate an answer from retrieved context and the original user question."""
        formatted = self.prompt_builder.build_answer_prompt(question, context, chat_history)
        return self._clean_answer(str(self.llm.invoke(formatted) or ""))

    def rewrite_query(self, question: str, chat_history: str = "") -> str:
        """Rewrite follow-up questions into standalone retrieval queries."""
        if not chat_history.strip():
            return question
        formatted = self.prompt_builder.build_rewrite_prompt(question, chat_history)
        rewritten = str(self.llm.invoke(formatted) or "").strip()
        if not rewritten:
            return question
        candidate = rewritten.splitlines()[0].strip(" \"'-•:") or question
        return candidate if self._is_valid_rewrite(question, candidate) else question

    @staticmethod
    def _is_valid_rewrite(question: str, rewritten: str) -> bool:
        clean = (rewritten or "").strip()
        if not clean:
            return False
        if len(clean) > max(240, len(question or "") * 3 + 80):
            return False
        normalized = clean.lower()
        answer_markers = [
            "câu trả lời",
            "trả lời:",
            "dựa trên ngữ cảnh",
            "theo ngữ cảnh",
            "tôi không tìm thấy",
            "không tìm thấy thông tin",
        ]
        return not any(marker in normalized for marker in answer_markers)

    @staticmethod
    def _clean_answer(answer: str) -> str:
        lines = [line.strip() for line in answer.strip().splitlines()]
        cleaned = []
        previous = None
        for line in lines:
            if not line:
                if cleaned and cleaned[-1]:
                    cleaned.append("")
                continue
            if line == previous:
                continue
            cleaned.append(line)
            previous = line
        return "\n".join(cleaned).strip()
