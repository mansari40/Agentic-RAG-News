from openai import OpenAI
from rag_baseline.configuration import settings
from rag_baseline.domain_models import RetrievalResult


class AnswerGenerator:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.chat_model_name

    def _build_context(self, chunks: list[RetrievalResult]) -> str:
        return "\n\n".join(chunk.content for chunk in chunks)

    def generate(self, question: str, chunks: list[RetrievalResult]) -> str:
        if not chunks:
            return "No relevant information found in the timber market news database."

        context = self._build_context(chunks)

        prompt = f"""You are a timber market analyst assistant specializing \
in the German wood industry.
Answer questions about timber markets, wood prices, forestry, lumber trade, \
and construction materials.
Use ONLY the provided news context. If the answer is not in the context, \
say you don't have that information.

Context from recent timber market news:
{context}

Question:
{question}

Answer:"""

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )

        content = response.choices[0].message.content
        return content.strip() if content else ""
