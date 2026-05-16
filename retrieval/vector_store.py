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

def search_code(query: str, repo_path: str = None, repo_map: dict[str, str] = None, top_k: int = 5) -> list[dict]:
    """Searches the vector store for relevant code chunks."""
    vector_store = get_vector_store()
    
    try:
        results = vector_store.similarity_search_with_score(query, k=top_k * 2)
    except Exception:
        results = []
    
    filtered_results = []
    
    if repo_map:
        from retrieval.repo_map import filter_directories
        relevant_dirs = filter_directories(query, repo_map)
        
        if len(relevant_dirs) < len(repo_map):
            for doc, score in results:
                file_path = doc.metadata.get("file_path", "")
                if any(file_path.startswith(d + "/") or file_path.startswith(d + "\\") for d in relevant_dirs):
                    filtered_results.append(doc)
                if len(filtered_results) >= top_k:
                    break
                    
    if not filtered_results:
        filtered_results = [doc for doc, score in results[:top_k]]
    else:
        filtered_results = filtered_results[:top_k]
        
    enriched_chunks = []
    
    for doc in filtered_results:
        file_path = doc.metadata.get("file_path", "")
        start_line = doc.metadata.get("start_line")
        end_line = doc.metadata.get("end_line")
        content = doc.page_content
        
        if repo_path:
            full_file_path = os.path.join(repo_path, file_path)
            if os.path.exists(full_file_path):
                try:
                    with open(full_file_path, "r", encoding="utf-8") as f:
                        full_content = f.read()
                        if len(full_content) < 8000:  # Approx 2k tokens
                            content = full_content
                            start_line = 1
                            end_line = full_content.count('\\n') + 1
                except Exception:
                    pass
                    
        enriched_chunks.append({
            "file_path": file_path,
            "start_line": start_line,
            "end_line": end_line,
            "content": content
        })
        
    return enriched_chunks
