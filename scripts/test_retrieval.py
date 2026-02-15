from rag_baseline.retrieval.semantic_retriever import SemanticRetriever

if __name__ == "__main__":
    retriever = SemanticRetriever()

    query = "What is the weather like in Australia?"

    results = retriever.retrieve(query)

    print(f"\nQuery: {query}")
    print(f"Found {len(results)} results:\n")

    for i, result in enumerate(results, 1):
        print(f"Result {i}:")
        print(f"  Score: {result.similarity_score:.4f}")
        print(f"  Content: {result.content[:200]}...")
        print()
