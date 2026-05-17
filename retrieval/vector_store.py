import os
from langchain_chroma import Chroma
from ingestion.embedder import get_embeddings

def get_vector_store(collection_name: str = "repo_chunks"):
    embeddings = get_embeddings()
    persist_directory = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")
    
    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=persist_directory
    )

def search_code(query: str, repo_path: str = None, repo_map: dict[str, str] = None, top_k: int = 8) -> list[dict]:
    """Searches the vector store for relevant code chunks."""
    vector_store = get_vector_store()
    
    try:
        # Retrieve more candidates to allow sorting/filtering implementation vs test code
        results = vector_store.similarity_search_with_score(query, k=100)
    except Exception:
        results = []
    
    # 1. Apply repo_map filtering if provided
    if repo_map:
        from retrieval.repo_map import filter_directories
        relevant_dirs = filter_directories(query, repo_map)
        if len(relevant_dirs) < len(repo_map):
            results = [
                (doc, score) for doc, score in results
                if any(doc.metadata.get("file_path", "").startswith(d + "/") or doc.metadata.get("file_path", "").startswith(d + "\\") for d in relevant_dirs)
            ]
            
    # 2. Separate implementation and test/example files
    impl_results = []
    test_results = []
    
    for doc, score in results:
        file_path = doc.metadata.get("file_path", "").lower()
        is_test_file = any(file_path.startswith(p) for p in ["tests/", "tests\\", "examples/", "examples\\"]) or "test_" in file_path or "conftest" in file_path
        
        if is_test_file:
            test_results.append((doc, score))
        else:
            impl_results.append((doc, score))
            
    # 3. Always prioritize core implementation chunks, fall back to test chunks
    sorted_results = impl_results + test_results
    
    filtered_results = [doc for doc, score in sorted_results[:top_k]]
        
    enriched_chunks = []
    
    for doc in filtered_results:
        file_path = doc.metadata.get("file_path", "")
        start_line = doc.metadata.get("start_line")
        end_line = doc.metadata.get("end_line")
        content = doc.page_content
        
        enriched_chunks.append({
            "file_path": file_path,
            "start_line": start_line,
            "end_line": end_line,
            "content": content
        })
        
    return enriched_chunks
