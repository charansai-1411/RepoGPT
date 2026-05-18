import os
from langchain_chroma import Chroma
from ingestion.embedder import get_embeddings

def get_vector_store(collection_name: str = "repo_chunks"):
    embeddings = get_embeddings()
    import tempfile
    persist_directory = os.path.join(tempfile.gettempdir(), "repogpt_chroma_db")
    
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
                if ("/" not in doc.metadata.get("file_path", "") and "\\" not in doc.metadata.get("file_path", "")) or
                any(doc.metadata.get("file_path", "").startswith(d + "/") or doc.metadata.get("file_path", "").startswith(d + "\\") for d in relevant_dirs)
            ]
            
    # 2. Separate file-mentioned matches, core implementation, and test/example files
    file_mentioned_results = []
    impl_results = []
    test_results = []
    
    query_lower = query.lower()
    
    for doc, score in results:
        file_path = doc.metadata.get("file_path", "")
        file_path_lower = file_path.lower()
        file_name = os.path.basename(file_path).lower()
        
        # Check if the query explicitly mentions this specific file name or path
        is_file_mentioned = (file_name in query_lower) or (file_path_lower in query_lower)
        
        if is_file_mentioned:
            file_mentioned_results.append((doc, score))
        else:
            is_test_file = any(file_path_lower.startswith(p) for p in ["tests/", "tests\\", "examples/", "examples\\"]) or "test_" in file_path_lower or "conftest" in file_path_lower
            if is_test_file:
                test_results.append((doc, score))
            else:
                impl_results.append((doc, score))
                
    # 3. Sort mentioned file chunks chronologically by start_line so the LLM reads them sequentially!
    file_mentioned_results.sort(key=lambda x: x[0].metadata.get("start_line", 0))
    
    # Prioritize: 1) Explicitly mentioned files, 2) Core implementation, 3) Test suites
    sorted_results = file_mentioned_results + impl_results + test_results
    
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
