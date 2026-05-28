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
        """Sinh câu trả lời có kèm lịch sử hội thoại gần nhất để AI không bị quên."""
        formatted = self.prompt_builder.build_answer_prompt(question, context, chat_history)
        return self.llm.invoke(formatted)
