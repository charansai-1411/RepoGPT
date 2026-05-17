from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
from agent.prompts import qa_prompt
from retrieval.vector_store import search_code

def format_context(chunks: list[dict]) -> str:
    """Formats the retrieved chunks into a string for the prompt context."""
    context_parts = []
    total_chars = 0
    
    for chunk in chunks:
        file_path = chunk.get("file_path", "unknown")
        start_line = chunk.get("start_line", 0)
        end_line = chunk.get("end_line", 0)
        content = chunk.get("content", "")
        
        if len(content) > 3000:
            content = content[:3000] + "\n...[TRUNCATED]"
            
        if total_chars + len(content) > 15000:
            break
            
        context_parts.append(
            f"--- File: {file_path} (Lines {start_line}-{end_line}) ---\n{content}\n"
        )
        total_chars += len(content)
        
    return "\n".join(context_parts)

def get_qa_chain():
    """Builds and returns the LCEL QA chain."""
    import os
    model_name = os.environ.get("MODEL_ID", "llama-3.3-70b-versatile")
    llm = ChatGroq(model_name=model_name, temperature=0)
    
    chain = (
        qa_prompt 
        | llm 
        | StrOutputParser()
    )
    
    return chain

def ask_question(question: str, repo_path: str = None, repo_map: dict = None, top_k: int = 8) -> tuple[str, list[dict]]:
    """Retrieves context and asks the question using the QA chain."""
    # 1. Retrieve context
    chunks = search_code(question, repo_path=repo_path, repo_map=repo_map, top_k=top_k)
    
    # 2. Format context
    formatted_context = format_context(chunks)
    
    # 3. Generate answer
    chain = get_qa_chain()
    answer = chain.invoke({
        "context": formatted_context,
        "question": question
    })
    
    return answer, chunks
