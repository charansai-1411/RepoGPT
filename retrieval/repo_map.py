import os
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

SUPPORTED_EXTS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".cpp", ".cc", ".h", ".hpp",
    ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".md", ".txt", ".html",
    ".css", ".json", ".yml", ".yaml", ".xml", ".sh", ".bash", ".sql", ".m", ".scala",
    ".dart", ".lua", ".r", ".pl"
}

def build_repo_map(repo_path: str) -> dict[str, str]:
    """Builds a summary map of top-level directories in the repository."""
    model_name = os.environ.get("MODEL_ID", "llama-3.3-70b-versatile")
    llm = ChatGroq(model_name=model_name)
    
    prompt = PromptTemplate.from_template(
        "Summarize the purpose of this directory in exactly 2 sentences based on the following files it contains.\n"
        "Directory: {dir_name}\n"
        "Files: {files}\n"
        "Summary:"
    )
    
    chain = prompt | llm
    
    repo_map = {}
    
    for item in os.listdir(repo_path):
        item_path = os.path.join(repo_path, item)
        if os.path.isdir(item_path) and not item.startswith('.') and item not in ('venv', 'node_modules', '__pycache__'):
            dir_files = []
            for root, _, files in os.walk(item_path):
                for f in files:
                    if any(f.endswith(ext) for ext in SUPPORTED_EXTS):
                        dir_files.append(os.path.relpath(os.path.join(root, f), repo_path))
            
            if dir_files:
                # Top 50 files to avoid prompt length issues
                files_str = ", ".join(dir_files[:50])
                try:
                    response = chain.invoke({"dir_name": item, "files": files_str})
                    repo_map[item] = response.content.strip()
                    print(f"Mapped directory: {item}")
                except Exception as e:
                    print(f"Error mapping directory {item}: {e}")
                    repo_map[item] = "Description unavailable due to error."
                    
    return repo_map

def filter_directories(query: str, repo_map: dict[str, str]) -> list[str]:
    """Uses LLM to decide which directories are relevant to the query."""
    if not repo_map:
        return []
        
    model_name = os.environ.get("MODEL_ID", "llama-3.3-70b-versatile")
    llm = ChatGroq(model_name=model_name)
    
    map_str = "\n".join([f"- {d}: {desc}" for d, desc in repo_map.items()])
    
    prompt = PromptTemplate.from_template(
        "You are an expert software engineer. Given the following repository map (directory -> description) "
        "and a user query, identify which directories are most likely to contain the answer.\n"
        "Return ONLY a comma-separated list of directory names. If none seem relevant, return 'ALL'.\n\n"
        "Repo Map:\n{map_str}\n\n"
        "Query: {query}\n"
        "Relevant Directories:"
    )
    
    chain = prompt | llm
    try:
        response = chain.invoke({"map_str": map_str, "query": query})
        content = response.content.strip()
        if content == "ALL":
            return list(repo_map.keys())
        
        dirs = [d.strip() for d in content.split(",") if d.strip() in repo_map]
        return dirs if dirs else list(repo_map.keys())
    except Exception as e:
        print(f"Error filtering directories: {e}")
        return list(repo_map.keys())
