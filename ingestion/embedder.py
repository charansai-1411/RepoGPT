import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_chroma import Chroma
import shutil

def get_embeddings():
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def get_vector_store(collection_name: str = "repo_chunks"):
    embeddings = get_embeddings()
    persist_directory = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")
    
    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=persist_directory
    )
    return vector_store

def embed_and_store(chunks: list[dict], clear_existing: bool = True):
    if not chunks:
        print("No chunks to store.")
        return
        
    persist_directory = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")
    if clear_existing and os.path.exists(persist_directory):
        shutil.rmtree(persist_directory)
        
    vector_store = get_vector_store()
    
    documents = []
    for chunk in chunks:
        doc = Document(
            page_content=chunk["content"],
            metadata={
                "file_path": chunk["file_path"],
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
                "symbol_name": chunk["symbol_name"],
            }
        )
        documents.append(doc)
        
    vector_store.add_documents(documents)
    print(f"Stored {len(documents)} chunks in Chroma database.")

def clear_db(collection_name: str = "repo_chunks"):
    persist_directory = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")
    if os.path.exists(persist_directory):
        shutil.rmtree(persist_directory)
        print(f"Cleared Chroma DB at {persist_directory}")
