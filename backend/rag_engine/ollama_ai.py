import logging
import time

import httpx
from langchain_ollama import OllamaLLM
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TEMPERATURE, OLLAMA_TIMEOUT_SECONDS
from contracts.rag import LLMProviderInterface
from services.admin.config_service import get_ollama_settings
from services.rag.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class OllamaAI(LLMProviderInterface):
    def __init__(self, model_name=None, prompt_builder: PromptBuilder | None = None, db=None):
        settings = get_ollama_settings(db) if db is not None else {
            "base_url": OLLAMA_BASE_URL,
            "model": OLLAMA_MODEL,
        }
        self.model = model_name or settings["model"]
        self.base_url = settings["base_url"]
        self.llm = OllamaLLM(
            model=self.model,
            base_url=self.base_url,
            timeout=OLLAMA_TIMEOUT_SECONDS,
            temperature=OLLAMA_TEMPERATURE,  # 0 = deterministic, bám sát context
        )
        self.prompt_builder = prompt_builder or PromptBuilder()

    def generate_answer(self, question: str, context: str, chat_history: str = ""):
        """Sinh câu trả lời có kèm lịch sử hội thoại gần nhất để AI không bị quên."""
        formatted = self.prompt_builder.build_answer_prompt(question, context, chat_history)
        started_at = time.perf_counter()
        logger.info(
            "Calling Ollama model=%s base_url=%s prompt_chars=%s context_chars=%s history_chars=%s timeout=%ss",
            self.model,
            self.base_url,
            len(formatted),
            len(context or ""),
            len(chat_history or ""),
            OLLAMA_TIMEOUT_SECONDS,
        )
        try:
            answer = self.llm.invoke(formatted)
        except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError, httpx.TimeoutException) as exc:
            logger.exception("Ollama connection failed after %.2fs", time.perf_counter() - started_at)
            raise RuntimeError(
                "Ollama khong tra ve cau tra loi. Ket noi toi Ollama bi dong hoac qua thoi gian cho. "
                "Hay kiem tra Ollama server, model dang chay, GPU/VRAM va thu lai bang lenh ollama run."
            ) from exc
        except Exception:
            logger.exception("Ollama call failed after %.2fs", time.perf_counter() - started_at)
            raise
        logger.info(
            "Ollama call finished in %.2fs answer_chars=%s",
            time.perf_counter() - started_at,
            len(answer or ""),
        )
        return answer
