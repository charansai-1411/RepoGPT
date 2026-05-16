**PRD: Codebase Q&A Agent**

Codename: RepoGPT  •  Version: 2.0 (Stack-Updated)

Owner: Charan Sai  •  Timeline: 4–5 days to MVP  •  Budget: $0 (GCP $300 credit)

# **1. Problem Statement**
Engineers joining a new codebase spend 4–6 weeks reading code before contributing. Senior engineers get interrupted daily with “where is X?” or “how does Y work?” questions. Grep fails for conceptual questions. Docs are outdated.

*For V1 we target: Solo devs and small teams working on repos <50k lines who need fast answers with file + line citations.*

# **2. Goals & Non-Goals**

|**Goals**|**Non-Goals for V1**|
| :- | :- |
|Answer “where is X” and “how does Y work” with file paths + line numbers|Write or edit code|
|Ingest Python repos up to 50k lines in <2 min|Support JS / Go / Rust|
|<3s query latency on warm instance|Multi-repo or monorepo support|
|Deploy for $0 using GCP credit|Auth, private repos, team features|
|80%+ accuracy on 15 eval questions|Production-grade eval harness|


# **3. User Personas**
**Alex — New Hire**

Just joined team, needs to understand auth flow before first ticket. Wants answer in 10s, not 2 hours of grepping.

**Sam — Maintainer**

Owns legacy repo. Gets asked same 5 questions weekly. Wants to paste a link instead of answering.

**Charan — Portfolio Builder**

Needs to prove RAG + agent skills in interviews. Needs clean demo + GitHub repo targeting ServiceNow off-campus role.

# **4. Core User Flow**
- User inputs GitHub URL of public repo → clicks Ingest
- System clones, parses with AST, chunks by function/class, embeds, stores in pgvector
- User asks question in chat → system retrieves relevant code + repo map → LLM answers with citations
- Answer shows: markdown explanation + collapsible code blocks + links to GitHub


# **5. Requirements**
## **P0 — Must Ship**
**Ingestion**

- Clone public GitHub repo. Support .py files only. Ignore venv, node\_modules, .git
- Hard limit: 50k lines. Show error: “Repo too large for V1” if exceeded

**Chunking**

- Use tree-sitter-python to chunk by function\_definition and class\_definition
- Metadata per chunk: file\_path, start\_line, end\_line, symbol\_name
- No token-level chunking — AST chunking prevents broken function boundaries

**Repo Map**

- On ingest, run gemini-1.5-flash to summarize each top-level directory in 2 sentences
- Store repo map in memory (fast lookup, no vector overhead)

**Retrieval**

- Query → check repo map to filter directories → pgvector search top 5 chunks
- For each chunk, pull full file context if <2k tokens
- Use LCEL chain (not deprecated RetrievalQA)

**Answering**

- Use gemini-1.5-flash with strict prompt: “Answer using only provided context. Cite file\_path:start-end for every fact. If not in context, say I don’t know.”
- All code facts must cite format: src/auth.py:12-25

**UI (Streamlit)**

- Left sidebar: ingest controls (URL input, Ingest button, Clear DB button)
- Main panel: chat interface with sources shown under each answer
- Clickable citation links to GitHub line anchors

## **P1 — Nice to Have**
- Show latency + token cost per query in UI footer
- Cache pgvector data across Cloud Run restarts (Cloud SQL persists by default — this is free with pgvector on Cloud SQL)
- Clear DB button for testing

# **6. Technical Architecture (Updated Stack)**

|**Component**|**Tool**|**Reason**|
| :- | :- | :- |
|LLM|Vertex AI gemini-1.5-flash-001|Free tier, fast, good at code. $300 credit|
|Embeddings|Vertex AI text-embedding-004|768 dim, free tier, matches Gemini|
|Vector DB|pgvector on Cloud SQL (PostgreSQL)|Durable across Cloud Run restarts. No GCS sync hack needed. Already in stack.|
|Parsing|tree-sitter + tree-sitter-python|AST-aware chunking prevents broken functions|
|Orchestration|LangChain LCEL|Non-deprecated. ChatVertexAI + VertexAIEmbeddings. Explicit Python classes over heavy abstractions.|
|UI|Streamlit|Fastest to demo|
|Deploy|Cloud Run|Scales to 0. 2M req free. Dockerfile|
|Infra|GCP project us-central1|All services in free tier region|

## **Data Flow**
GitHub URL → git clone /tmp → tree-sitter chunk → VertexAI embed → pgvector (Cloud SQL)

User Query → Repo map filter → pgvector search → Parent file fetch → Gemini answer → Streamlit render

## **Why ChromaDB was replaced**
- Cloud Run containers are ephemeral — /tmp is wiped on restart
- The P1 mitigation (persist ChromaDB to GCS) is non-trivial and a Day 4 time bomb
- pgvector on Cloud SQL persists durably with zero extra work, and the SQL interface is cleaner for metadata filtering

# **7. Project Structure**
repogpt/

`  `├── ingestion/

`  `│   ├── cloner.py        # git clone to /tmp, size check, cleanup

`  `│   ├── chunker.py       # tree-sitter AST → chunks with metadata

`  `│   └── embedder.py      # Vertex AI text-embedding-004 + pgvector write

`  `├── retrieval/

`  `│   ├── vector\_store.py  # pgvector queries, top-k search

`  `│   └── repo\_map.py      # per-directory summaries via Gemini Flash

`  `├── agent/

`  `│   ├── qa\_chain.py      # LCEL chain: retrieve → format → generate

`  `│   └── prompts.py       # system prompt, citation format, guardrails

`  `├── ui/

`  `│   └── app.py           # Streamlit: sidebar ingest, main chat, sources panel

`  `├── evals/

`  `│   ├── evals.jsonl      # 15 Q&A pairs against pallets/flask

`  `│   └── run\_evals.py     # accuracy + citation rate runner

`  `├── Dockerfile

`  `├── requirements.txt

`  `└── README.md

# **8. Evaluation Plan**
Create evals.jsonl with 15 Q&A pairs against pallets/flask. Examples:

{"question": "Where is request context pushed?", "answer\_contains": ["appcontext.py", "push"]}

{"question": "How does routing work?", "ground\_truth\_files": ["app.py", "routing.py"]}

|**Metric**|**Target**|**How Measured**|
| :- | :- | :- |
|Accuracy|>80%|% questions where answer contains ground truth file/symbol|
|Citation Rate|100%|% factual statements with valid file:line citation|
|Latency p95|<3s|Timed query runs on warm instance|
|Cost|<$5 total GCP spend|Vertex AI token logs|


# **9. Milestones**

|**Day**|**Deliverable**|**Acceptance Criteria**|
| :- | :- | :- |
|Day 1|ingestion/ fully working|Unit test: chunk 1 .py file, assert metadata fields present|
|Day 2|retrieval/ + agent/ CLI working|python -m agent.qa\_chain returns cited answer in terminal|
|Day 3|Streamlit UI + citations + GitHub links|3 questions answered with clickable src:line citations in browser|
|Day 4|Evals + Dockerfile|run\_evals.py prints accuracy + citation rate. docker build passes.|
|Day 5|Deploy to Cloud Run + README + Loom|Public URL live. 2-min Loom recorded. README has architecture diagram.|


# **10. Risks & Mitigations**

|**Risk**|**Mitigation**|
| :- | :- |
|Hallucinated file paths|Strict prompt: If not in context, say I don’t know. Evals catch this.|
|Cloud Run cold start >5s|Keep 1 min instance warm during demo. Note in README.|
|Gemini bad at code vs GPT-4|Test Day 2. If bad, swap to GPT-4o-mini. Still under $300 credit.|
|Repo too large, OOM|Hard limit: 50k lines. Return error before cloning.|
|pgvector Cloud SQL billing|Use db-f1-micro (free tier). Ensure billing account is active before Day 1.|


# **11. Success Criteria**
- Demo: 2-min Loom showing ingest + 3 questions answered correctly with citations
- Code: Public GitHub repo with README, architecture diagram, eval results
- Interview: Whiteboard the system + explain AST chunking vs token chunking + repo map tradeoff
- Cost: Total GCP spend <$5 after build

# **12. Out of Scope for V1**
- Multi-language support (JS, Go, Rust)
- Private repos / OAuth
- Incremental indexing on git push
- Write code agent mode
- Re-ranking, hybrid search
- Multi-repo or monorepo support

*Stack change summary: ChromaDB → pgvector on Cloud SQL (durable, no GCS sync). LangChain RetrievalQA → LCEL chains (non-deprecated). All other components unchanged.*
