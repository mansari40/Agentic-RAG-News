from rag_baseline.orchestration.rag_pipeline import RAGPipeline

if __name__ == "__main__":
    rag = RAGPipeline()

    questions = [
        "What tariffs did Trump impose on timber and lumber?",
        "What is happening with West Fraser Timber?",
        "What are the recent lumber price trends?",
        "Tell me about Mercer International's acquisition",
        "What impact will tariffs have on housing costs?",
    ]

    for question in questions:
        print(f"\nQuestion: {question}")
        print("=" * 70)
        answer = rag.answer(question)
        print(answer)
        print()
