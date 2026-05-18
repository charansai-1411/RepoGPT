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

st.set_page_config(page_title="RepoGPT", layout="wide", page_icon="⚡")

# Custom CSS for Premium Design & Visual Polish
st.markdown("""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    /* Apply outfit font globally */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Outfit', sans-serif;
        background-color: #0d0e15 !important;
        color: #e2e8f0 !important;
    }
    
    /* Elegant Title and Badges Styling */
    .title-gradient {
        background: linear-gradient(135deg, #a78bfa 0%, #ec4899 50%, #f43f5e 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3.5rem !important;
        letter-spacing: -0.03em;
        text-shadow: 0px 4px 20px rgba(236, 72, 153, 0.15);
    }
    
    /* Sidebar custom glassmorphism */
    [data-testid="stSidebar"] {
        background-color: #111320 !important;
        border-right: 1px solid rgba(167, 139, 250, 0.12) !important;
    }
    
    /* Elegant button styling */
    div.stButton > button {
        background: linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%) !important;
        color: white !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 10px 24px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0px 4px 15px rgba(139, 92, 246, 0.3) !important;
        width: 100% !important;
    }
    
    div.stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0px 8px 25px rgba(236, 72, 153, 0.5) !important;
        border: none !important;
    }
    
    /* Input field borders and shadow styling */
    div.stTextInput > div > div > input {
        border-radius: 10px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        background-color: rgba(255, 255, 255, 0.03) !important;
        color: white !important;
        transition: all 0.3s ease !important;
    }
    
    div.stTextInput > div > div > input:focus {
        border-color: #ec4899 !important;
        box-shadow: 0 0 10px rgba(236, 72, 153, 0.25) !important;
    }
    
    /* Styled Chat messages */
    [data-testid="stChatMessage"] {
        background: rgba(22, 25, 41, 0.65) !important;
        border: 1px solid rgba(255, 255, 255, 0.04) !important;
        border-radius: 16px !important;
        padding: 18px !important;
        box-shadow: 0px 8px 32px rgba(0, 0, 0, 0.25) !important;
        margin-bottom: 15px !important;
        transition: all 0.3s ease !important;
        backdrop-filter: blur(8px);
    }
    
    [data-testid="stChatMessage"]:hover {
        border-color: rgba(167, 139, 250, 0.2) !important;
        box-shadow: 0px 12px 40px rgba(139, 92, 246, 0.15) !important;
        transform: translateY(-2px) !important;
    }
    
    /* Code boxes in sources */
    div.stCodeBlock {
        border-radius: 10px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
    }
    
    /* View Context Sources expander */
    div.stExpander {
        background: rgba(255, 255, 255, 0.02) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.15) !important;
    }
</style>
""", unsafe_allow_html=True)

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
    st.markdown('<h2 style="font-size: 1.8rem; font-weight: 700; margin-bottom: 15px; background: linear-gradient(135deg, #a78bfa 0%, #ec4899 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-family: \'Outfit\', sans-serif;">⚡ Ingestion</h2>', unsafe_allow_html=True)
    
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
                    
                with st.spinner("Embedding & storing in ChromaDB via HuggingFace..."):
                    embed_and_store(all_chunks, clear_existing=True)
                    
                with st.spinner("Analyzing code structure & building Repo Map..."):
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
st.markdown("""
<div style="text-align: center; margin-bottom: 40px; margin-top: -20px;">
    <h1 class="title-gradient" style="margin-bottom: 10px;">⚡ RepoGPT</h1>
    <p style="font-size: 1.15rem; color: #a78bfa; font-weight: 500; margin-bottom: 25px; font-family: 'Outfit', sans-serif;">
        Zero-Cost, Ultra-Fast Local Codebase Intelligence Agent
    </p>
    <div style="display: flex; justify-content: center; gap: 12px; flex-wrap: wrap;">
        <span style="background: rgba(139, 92, 246, 0.12); border: 1px solid rgba(139, 92, 246, 0.4); color: #c084fc; padding: 6px 14px; border-radius: 20px; font-size: 0.85rem; font-weight: 600; box-shadow: 0 0 10px rgba(139,92,246,0.15); font-family: 'Outfit', sans-serif;">📦 ChromaDB Local</span>
        <span style="background: rgba(236, 72, 153, 0.12); border: 1px solid rgba(236, 72, 153, 0.4); color: #f472b6; padding: 6px 14px; border-radius: 20px; font-size: 0.85rem; font-weight: 600; box-shadow: 0 0 10px rgba(236,72,153,0.15); font-family: 'Outfit', sans-serif;">🤗 HuggingFace Embeddings</span>
        <span style="background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.4); color: #34d399; padding: 6px 14px; border-radius: 20px; font-size: 0.85rem; font-weight: 600; box-shadow: 0 0 10px rgba(16,185,129,0.15); font-family: 'Outfit', sans-serif;">🚀 Groq Llama 3 Connected</span>
    </div>
</div>
""", unsafe_allow_html=True)

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
