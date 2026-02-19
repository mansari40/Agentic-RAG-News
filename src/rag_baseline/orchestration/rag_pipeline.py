from rag_baseline.generation.answer_generator import AnswerGenerator
from rag_baseline.retrieval.hybrid_retriever import HybridRetriever


class RAGPipeline:
    """
    Baseline Retrieval-Augmented Generation pipeline with hybrid search.

    Flow:
        question -> retrieve (vector + keyword) -> generate -> answer
    """

    def __init__(self, use_hybrid: bool = True) -> None:
        self.retriever = HybridRetriever()
        self.generator = AnswerGenerator()
        self.use_hybrid = use_hybrid

    def answer(self, question: str) -> str:
        """
        Run full RAG pipeline with hybrid search.

        Args:
            question: user query

        Returns:
            generated answer
        """
        chunks = self.retriever.retrieve(question, use_hybrid=self.use_hybrid)
        answer: str = self.generator.generate(question, chunks)
        return answer
