import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
import streamlit as st
import re
import sys
from dotenv import load_dotenv

load_dotenv()

# Ensure imports work when running from the ui folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.cloner import clone_and_validate, RepoTooLargeError
from ingestion.chunker import extract_chunks
from ingestion.embedder import embed_and_store, clear_db
from retrieval.repo_map import build_repo_map
from agent.qa_chain import ask_question

st.set_page_config(page_title="RepoGPT", layout="wide")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "repo_map" not in st.session_state:
    st.session_state.repo_map = None
if "repo_url" not in st.session_state:
    st.session_state.repo_url = None
if "repo_path" not in st.session_state:
    st.session_state.repo_path = None

def get_github_link(repo_url: str, file_path: str, start_line: str, end_line: str) -> str:
    """Creates a GitHub URL to the specific file and lines."""
    base = repo_url.rstrip("/")
    return f"{base}/blob/main/{file_path}#L{start_line}-L{end_line}"

def parse_citations(text: str, repo_url: str) -> str:
    """Parses `file_path:start-end` and replaces it with markdown links."""
    if not repo_url:
        return text
    
    # Regex to find `file_path:start-end` inside backticks
    pattern = r'`([^`]+):(\d+)-(\d+)`'
    
    def repl(match):
        file_path = match.group(1)
        start_line = match.group(2)
        end_line = match.group(3)
        link = get_github_link(repo_url, file_path, start_line, end_line)
        return f"[{file_path}:{start_line}-{end_line}]({link})"
        
    return re.sub(pattern, repl, text)

# Sidebar
with st.sidebar:
    st.title("RepoGPT Ingestion")
    
    repo_url_input = st.text_input("GitHub URL", placeholder="https://github.com/pallets/flask")
    
    if st.button("Ingest Repo"):
        if not repo_url_input:
            st.error("Please enter a GitHub URL")
        else:
            try:
                st.session_state.repo_url = repo_url_input
                
                with st.spinner("Cloning and validating repo..."):
                    repo_path, py_files = clone_and_validate(repo_url_input)
                    st.session_state.repo_path = repo_path
                    
                with st.spinner("Chunking files..."):
                    all_chunks = []
                    for f in py_files:
                        chunks = extract_chunks(f, repo_path)
                        all_chunks.extend(chunks)
                    st.success(f"Created {len(all_chunks)} chunks.")
                    
                with st.spinner("Embedding and storing in PGVector..."):
                    embed_and_store(all_chunks, clear_existing=True)
                    
                with st.spinner("Building Repo Map with Gemini..."):
                    st.session_state.repo_map = build_repo_map(repo_path)
                    
                st.success("Ingestion complete! You can now chat.")
            except RepoTooLargeError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Error during ingestion: {e}")
                
    st.divider()
    
    if st.button("Clear Vector DB"):
        try:
            clear_db()
            st.success("Vector DB cleared.")
        except Exception as e:
            st.error(f"Error clearing DB: {e}")

# Main Chat Interface
st.title("RepoGPT Chat")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander("View Context Sources"):
                for s in msg["sources"]:
                    st.markdown(f"**{s['file_path']}** (Lines {s['start_line']}-{s['end_line']})")
                    st.code(s["content"], language="python")

if prompt := st.chat_input("Ask about the codebase..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
        
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                answer, sources = ask_question(
                    prompt, 
                    repo_path=st.session_state.repo_path, 
                    repo_map=st.session_state.repo_map
                )
                
                # Replace backtick citations with clickable links
                formatted_answer = parse_citations(answer, st.session_state.repo_url)
                
                st.markdown(formatted_answer)
                
                if sources:
                    with st.expander("View Context Sources"):
                        for s in sources:
                            st.markdown(f"**{s['file_path']}** (Lines {s['start_line']}-{s['end_line']})")
                            st.code(s["content"], language="python")
                            
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": formatted_answer,
                    "sources": sources
                })
            except Exception as e:
                st.error(f"Error: {e}")
