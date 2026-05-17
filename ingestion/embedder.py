import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_chroma import Chroma
import shutil

_embeddings_instance = None

def get_embeddings():
    global _embeddings_instance
    if _embeddings_instance is None:
        _embeddings_instance = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return _embeddings_instance

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
        
    vector_store = get_vector_store()
    
    if clear_existing:
        try:
            db_data = vector_store.get()
            if db_data and "ids" in db_data and db_data["ids"]:
                vector_store.delete(ids=db_data["ids"])
                print(f"Cleared {len(db_data['ids'])} existing chunks via Chroma API.")
        except Exception as e:
            print(f"Warning: Could not clear existing chunks via API: {e}")
            persist_directory = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")
            if os.path.exists(persist_directory):
                try:
                    shutil.rmtree(persist_directory)
                    print("Cleared Chroma DB directory.")
                except Exception as ex:
                    print(f"Warning: Could not remove directory: {ex}")
    
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
