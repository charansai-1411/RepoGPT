# RepoGPT

RepoGPT is a Codebase Q&A Agent that uses **Groq**, **HuggingFace Embeddings**, and **ChromaDB** to answer questions about Python repositories.

## Features

- **AST-Aware Chunking**: Parses code into logical blocks (functions/classes) rather than arbitrary tokens.
- **Intelligent Retrieval**: Uses a directory-level repo map to pre-filter relevant code before vector search.
- **Verified Answers**: Forces the LLM to provide citations in `file:line-range` format, which are converted to clickable GitHub links in the UI.
- **Fast Inference**: Powered by Groq for ultra-low latency chat responses.

## Setup

1. Create a Python virtual environment: `python -m venv venv`
2. Activate the environment: `.\venv\Scripts\activate` (Windows)
3. Install dependencies: `pip install -r requirements.txt`
4. Create a `.env` file with your `GROQ_API_KEY`.

## Running Locally

```bash
streamlit run ui/app.py
```

## Evaluation

To run accuracy and latency benchmarks:
```bash
python evals/run_evals.py
```
