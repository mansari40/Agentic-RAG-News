from rag_baseline.indexing.vector_indexer import VectorIndexingPipeline

if __name__ == "__main__":
    pipeline = VectorIndexingPipeline()
    pipeline.index_all_chunks()
    print("Indexing completed.")
