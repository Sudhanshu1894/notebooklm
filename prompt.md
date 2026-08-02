# Agent Build Instructions — GraphRAG Research Notebook

This file contains a sequence of ready-to-paste prompts for an agentic coding
tool (Antigravity, Claude Code, Cursor, etc.) to build this project end to end.
Each phase is a separate prompt — run them in order, verify the output, commit,
then move to the next. Don't paste multiple phases into one agent run; each
phase depends on the previous one being verified working.

## How to use this file

1. Read the "Global constraints" section once — keep it in mind for every phase.
2. Copy one phase's prompt block into your agent.
3. After the agent finishes, actually run/test what it built (each phase lists
   a verification step) before moving on.
4. Commit with the suggested message.
5. Move to the next phase.

Phase 0 (repo scaffold + dataset loader) is already done. Start at Phase 1.

---

## Global constraints (apply to every phase)

- **Free tier only.** No paid APIs, no credit-card-required services, no
  services that silently start billing past a quota. If a step would require
  payment, the agent should stop and ask instead of proceeding.
- **Stack is fixed** — don't let the agent substitute a different vector DB,
  graph DB, or LLM provider without asking:
  - LLM + entity extraction: Gemini API (free tier, `gemini-2.5-flash` or
    `gemini-flash-lite`)
  - Embeddings: `sentence-transformers` (local, `all-MiniLM-L6-v2` or
    `bge-base-en`) — no API calls, no quota
  - Vector store: ChromaDB (local, embedded)
  - Graph store: Neo4j AuraDB Free
  - Backend: FastAPI (Python)
  - Frontend: Next.js + Tailwind
  - Orchestration: LangChain or LlamaIndex (pick one, stay consistent)
  - Auth/relational DB/file storage: Supabase free tier
  - Audio TTS: `edge-tts`
- **Secrets never hardcoded.** All API keys/credentials go through `.env`,
  referenced via `.env.example` with placeholder values.
- **Every phase ends with a commit.** Small, verifiable commits — not one
  giant commit at the end.
- **Every new module gets a README.md** in its folder explaining what it does
  and how it fits the overall pipeline (matches the scaffold already committed).
- **Ask before assuming.** If a design decision isn't specified in the prompt
  (e.g. exact chunk size, exact graph schema fields), the agent should propose
  a reasonable default and briefly explain why, not silently pick one.

---

## Phase 1 — Service setup and connectivity

**Goal:** every external free-tier service is reachable and verified before
any pipeline code depends on it.

```
Set up and verify connectivity to all external services this project depends
on, using only free tiers. Do not write any pipeline logic yet — this phase is
purely "can we talk to every service."

1. Create a config module (config/settings.py or similar) that loads all
   required environment variables via pydantic-settings or python-dotenv:
   GEMINI_API_KEY, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, CHROMA_PERSIST_DIR,
   SUPABASE_URL, SUPABASE_KEY. Fail with a clear error message naming the
   missing variable if any required one is absent.

2. Write a small connectivity-check script (scripts/check_services.py) that:
   - Sends a trivial test prompt to Gemini and confirms a response comes back
   - Connects to the Neo4j AuraDB Free instance and runs a simple `RETURN 1`
     query to confirm the connection
   - Initializes a local ChromaDB client, creates a test collection, inserts
     one dummy embedding, queries it back, then deletes the test collection
   - Connects to Supabase and confirms the client authenticates

3. Print a clear pass/fail summary for each service when the script runs.

4. Update the top-level README with a "Setup" section: how to get each
   free-tier credential (Gemini API key from Google AI Studio, Neo4j AuraDB
   Free instance creation, Supabase free project creation), and how to run
   the connectivity check.

5. Do not proceed to write ingestion/retrieval code in this phase.
```

**Verify:** run `scripts/check_services.py` yourself, confirm all four checks
pass with your actual credentials in `.env` (not committed).

**Commit:** `Phase 1: service connectivity checks for Gemini, Neo4j, Chroma, Supabase`

---

## Phase 2 — Document ingestion and chunking

**Goal:** raw documents (PDF, DOCX, TXT) become clean, structured text chunks
ready for embedding and entity extraction.

```
Implement the document ingestion and chunking pipeline in the ingestion/
module. This takes raw uploaded documents and produces clean text chunks with
metadata — no embedding or graph work yet, that's the next phases.

1. Support these input formats: PDF (use PyMuPDF), DOCX (use python-docx),
   and plain TXT. Structure it so adding a new format later is a small,
   isolated change (e.g. a format->parser registry, not a growing if/elif).

2. Each parser should extract: raw text, and where available, page numbers
   or section headers — this metadata is required later for citation
   grounding, so don't discard it.

3. Implement a chunking function with a configurable chunk size (default
   ~500 tokens) and overlap (default ~50 tokens), using a sentence-aware
   splitter (don't cut mid-sentence). Use langchain's or llama-index's
   text splitter utilities rather than writing one from scratch.

4. Each chunk must carry metadata: source document ID, chunk index, page
   number (if available), and character offsets into the original text.

5. Write a simple in-memory or SQLite-backed "document registry" that tracks:
   document ID, filename, upload timestamp, processing status
   (uploaded/parsed/chunked/failed). This will back the notebook's source
   list in the UI later.

6. Add unit tests: one sample PDF, one DOCX, one TXT file (small test fixtures
   you generate), confirming each produces the expected chunk structure and
   metadata.

7. Write ingestion/README.md documenting the chunking strategy and why the
   default size/overlap was chosen.
```

**Verify:** run the test suite; manually ingest one real PDF from your dataset
sample and inspect that chunks look sane (no broken sentences, metadata present).

**Commit:** `Phase 2: document ingestion and chunking pipeline`

---

## Phase 3 — Embeddings and vector store

**Goal:** chunks from Phase 2 get embedded locally and indexed in Chroma for
similarity search.

```
Implement the embedding and vector storage layer in embedding/ and
vector_store/.

1. In embedding/, wrap sentence-transformers with a simple interface:
   embed_texts(list[str]) -> list[vector]. Load the model once (not per call)
   and make the model name configurable via settings, defaulting to
   all-MiniLM-L6-v2.

2. In vector_store/, wrap ChromaDB with functions to: create/get a collection
   per notebook (so notebooks are isolated from each other), upsert chunks
   with their embeddings and metadata from Phase 2, and query top-k similar
   chunks given a query embedding, with optional metadata filtering
   (e.g. restrict to one document).

3. Write an end-to-end script (scripts/index_document.py) that takes a file
   path and a notebook ID, runs it through ingestion -> chunking -> embedding
   -> Chroma upsert, and prints how many chunks were indexed.

4. Add a query test script (scripts/test_vector_search.py) that takes a
   notebook ID and a text query, embeds the query, and prints the top-5
   retrieved chunks with their similarity scores and source metadata.

5. Add unit tests confirming: embeddings are deterministic for the same
   input, collection isolation works (a query in notebook A never returns
   chunks from notebook B), and metadata survives the round trip.

6. Write vector_store/README.md and embedding/README.md.
```

**Verify:** index 2-3 real sample documents into a test notebook, run
`test_vector_search.py` with a few queries, confirm retrieved chunks are
actually relevant.

**Commit:** `Phase 3: embedding pipeline and Chroma vector store`

---

## Phase 4 — Knowledge graph construction

**Goal:** entities and relationships get extracted from chunks via Gemini and
written into Neo4j as a queryable graph. This is the core GraphRAG piece.

```
Implement knowledge graph construction in graph_store/.

1. Design a graph schema before writing extraction code. At minimum: an
   Entity node (properties: name, type e.g. person/org/concept/event,
   source_chunk_ids) and a RELATION edge between entities (properties:
   relation_type, description, source_chunk_id). Write this schema as a
   short spec in graph_store/SCHEMA.md before implementing, and use it
   consistently.

2. Implement an extraction function that takes a chunk's text and calls
   Gemini with a structured-output prompt (request JSON only) asking it to
   return a list of entities and a list of relationships between them found
   in that chunk. Include a few-shot example in the prompt to stabilize the
   output format. Parse and validate the JSON response; if parsing fails,
   retry once with a stricter "return valid JSON only" instruction before
   giving up on that chunk.

3. Implement Neo4j write functions: upsert an entity (MERGE on name+type to
   avoid duplicate nodes across chunks), and upsert a relationship edge
   (MERGE on the entity pair + relation_type). Every entity/edge should
   retain a reference back to the chunk(s) it was extracted from, for
   citation purposes later.

4. Write an end-to-end script (scripts/build_graph.py) that takes a notebook
   ID, pulls all chunks already indexed for that notebook from Phase 3's
   storage, runs extraction on each, and writes results into Neo4j scoped
   to that notebook (use a notebook_id property on nodes/edges, or a
   separate Neo4j database per notebook if your AuraDB Free plan allows it —
   check and use whichever is simpler).

5. Add a script (scripts/query_graph.py) that takes an entity name and prints
   its direct neighbors and relationship types — a basic sanity-check tool,
   not the final retrieval logic (that's Phase 5).

6. Add tests using a small fixed set of sample chunks with known expected
   entities, confirming extraction finds them (allow some tolerance —
   LLM extraction won't be perfectly deterministic).

7. Note the cost/rate-limit reality in graph_store/README.md: this phase
   makes one Gemini call per chunk, so document how to batch or rate-limit
   ingestion to stay within the free tier's daily request cap.
```

**Verify:** run `build_graph.py` on your 2-3 sample documents, then open the
Neo4j AuraDB browser console and visually inspect the resulting graph —
confirm entities and relationships look correct, not just "present."

**Commit:** `Phase 4: LLM-based entity/relationship extraction into Neo4j`

---

## Phase 5 — Hybrid retrieval

**Goal:** given a query, combine vector search (Phase 3) and graph traversal
(Phase 4) into one merged, reranked context set. This is where the project's
core novelty lives — don't just bolt the two together naively.

```
Implement hybrid retrieval in retrieval/.

1. Implement vector-only retrieval: embed the query, get top-k chunks from
   Chroma (reuse Phase 3's function).

2. Implement graph-augmented retrieval: given the top vector-search hits,
   look up which entities were extracted from those chunks (Phase 4's
   chunk->entity links), then traverse the graph 1-2 hops out from those
   entities to find related entities and pull in the chunks associated with
   THEM too. This is the multi-hop expansion step that plain vector search
   can't do.

3. Implement a merge/rerank step that combines the vector-search chunks and
   graph-expanded chunks into one ranked list, deduplicated, with a simple
   scoring approach (e.g. weight by vector similarity, boost items that
   appeared in the graph expansion). Cap the final context to a token budget
   you define (e.g. ~4000 tokens) so it fits comfortably in the generation
   prompt.

4. Implement a lightweight query router: before retrieving, classify whether
   the query is likely single-hop/factual (route to vector-only, cheaper and
   faster) or multi-hop/relational (route to the full hybrid path). A simple
   heuristic or a small Gemini classification call is fine — don't
   over-engineer this, but do log which path was taken so it can be
   evaluated later.

5. Write scripts/test_retrieval.py that takes a notebook ID and a query,
   runs both vector-only and hybrid retrieval, and prints both result sets
   side by side so you can visually compare what the graph expansion added.

6. Add retrieval/README.md explaining the merge/rerank logic and the routing
   heuristic, since this is the piece you'll want to describe carefully in
   your report later.
```

**Verify:** run `test_retrieval.py` with a genuinely multi-hop question about
your sample documents (one whose answer requires connecting two different
sources) and confirm the hybrid path retrieves relevant chunks that the
vector-only path misses.

**Commit:** `Phase 5: hybrid vector + graph retrieval with query routing`

---

## Phase 6 — Answer generation with citations

**Goal:** turn retrieved context into a grounded answer, with every claim
traceable back to a specific chunk/page.

```
Implement generation in generation/.

1. Build a prompt template that takes the user's query and the merged
   context chunks from Phase 5 (each chunk carries its source metadata),
   and instructs Gemini to answer using only the provided context, citing
   each claim with a bracketed reference to the source chunk (e.g. [1], [2])
   matching a source list you'll render alongside the answer.

2. Implement the generation function: call Gemini with the prompt, parse the
   response, and map the citation markers back to the actual source
   metadata (document name, page number) so the final output pairs each
   citation number with a real, clickable source reference.

3. Handle the "not enough context to answer" case explicitly — instruct the
   model to say so rather than hallucinating, and detect this case in the
   response so the API layer can surface it clearly to the user.

4. Write scripts/test_generation.py that runs a full query end to end:
   retrieval (Phase 5) -> generation -> printed answer with numbered
   citations and their source documents.

5. Add generation/README.md documenting the citation format and how source
   mapping works.
```

**Verify:** ask a question you know the answer to from your sample documents,
confirm the citations actually point to the correct source and page.

**Commit:** `Phase 6: cited answer generation`

---

## Phase 7 — API layer

**Goal:** expose the pipeline as a FastAPI backend the frontend can call.

```
Build the FastAPI backend in api/.

1. Endpoints needed:
   - POST /notebooks — create a new notebook, returns notebook_id
   - POST /notebooks/{id}/documents — upload a document, runs ingestion ->
     chunking -> embedding -> graph extraction (Phases 2-4) as a background
     task, returns immediately with a processing status
   - GET /notebooks/{id}/documents/{doc_id}/status — poll processing status
   - POST /notebooks/{id}/chat — takes a query, runs retrieval + generation
     (Phases 5-6), returns the answer with citations
   - GET /notebooks/{id}/graph — returns the notebook's graph as
     nodes/edges JSON for frontend visualization
   - GET /notebooks/{id}/sources — list uploaded documents and their status

2. Use FastAPI's BackgroundTasks (or a simple task queue if you prefer) for
   the document-processing endpoint, since extraction can take a while —
   don't block the HTTP response on it.

3. Add request/response models with Pydantic for every endpoint — don't
   pass raw dicts around.

4. Add basic error handling: invalid notebook_id returns 404, malformed
   uploads return 422 with a clear message, and any pipeline failure is
   caught and surfaced as a 500 with a logged stack trace rather than
   crashing the server.

5. Add CORS configuration permissive enough for local frontend development.

6. Write api/README.md with example curl requests for every endpoint.

7. Add a minimal integration test that spins up the app with FastAPI's
   TestClient and exercises the notebook-create -> document-upload ->
   status-poll -> chat flow against your sample documents.
```

**Verify:** run the server locally, exercise every endpoint with curl or the
FastAPI auto-generated docs UI at /docs.

**Commit:** `Phase 7: FastAPI backend exposing the full pipeline`

---

## Phase 8 — Frontend

**Goal:** a usable chat + source + graph-explorer UI.

```
Build the Next.js frontend.

1. Pages/views needed: a notebook list/creation view, a notebook workspace
   view with three panels — source list (upload + processing status), chat
   (query input + answer with clickable citations), and a graph explorer
   (interactive visualization of the notebook's knowledge graph using
   react-force-graph or a similar library).

2. Citations in the chat panel should be clickable and highlight/scroll to
   the relevant source in the source panel — this is the "source grounding"
   experience that's the whole point of the project, so don't skip it for a
   plain text answer.

3. The graph explorer should let a user click a node and see its connected
   chunks/documents, reinforcing the connection between the chat citations
   and the graph.

4. Poll the document status endpoint while a document is processing and show
   a clear progress state, since graph extraction (Phase 4) can take a while
   on the free tier.

5. Keep styling simple and clean with Tailwind — this doesn't need to be
   visually elaborate, it needs to clearly demonstrate the retrieval and
   citation flow working end to end.

6. Add a README section documenting how to run the frontend against the
   local backend.
```

**Verify:** run the full stack locally (backend + frontend), upload a real
document, ask a question, confirm citations and the graph view both work.

**Commit:** `Phase 8: Next.js frontend with chat, sources, and graph explorer`

---

## Phase 9 — Novelty features

**Goal:** the differentiators from the project's literature-survey positioning
— pick based on what your team locked in as the problem statement, don't
build all of them unless time allows.

```
Implement the following novelty features on top of the existing pipeline.
Treat each as independent — implement one, verify it, commit, then move to
the next, rather than doing all of them in one pass.

A. User-in-the-loop graph correction: add an API endpoint and UI control
   letting a user flag an incorrect entity or relationship in the graph
   explorer (Phase 8). Store flagged corrections in Supabase. Add a script
   that re-runs extraction on affected chunks incorporating the correction
   as a negative example in the prompt, and updates Neo4j accordingly.

B. Retrieval routing evaluation: instrument the query router from Phase 5
   to log which path (vector-only vs hybrid) was chosen for each query,
   along with retrieval latency and the final answer's citation count.
   Build a small script that summarizes this log — this is what will let
   you claim an actual measured tradeoff in your DA2/DA3 report rather than
   an assumed one.

C. Audio overview: implement a script that takes a notebook's key sources,
   generates a two-speaker summary script via Gemini (prompt it explicitly
   to produce a back-and-forth dialogue, not a monologue), and synthesizes
   it with edge-tts using two distinct voices, concatenating into one audio
   file.

Document whichever features you implement in a NOVELTY.md at the repo root,
explaining what gap in the existing NotebookLM/GraphRAG landscape each one
addresses — this maps directly to your literature survey's research-gap
section.
```

**Verify:** each feature independently, against real notebook content.

**Commit:** one commit per feature, e.g. `Phase 9a: user graph correction loop`

---

## Phase 10 — Evaluation against baselines

**Goal:** the DA2 requirement — benchmark your system against a published
baseline on a public dataset.

```
Build an evaluation harness in evaluation/ using the HotpotQA (or
MultiHop-RAG) sample already loaded by the Phase 0 dataset loader.

1. Implement three retrieval configurations to compare: vector-only,
   graph-only, and hybrid (your Phase 5 pipeline) — reusing the same
   underlying functions, just varying which retrieval path is used.

2. For each configuration, run the evaluation subset through the full
   pipeline (retrieval -> generation) and score answers against the
   dataset's ground-truth answers using standard QA metrics (exact match
   and F1 — implement or import standard implementations, don't write
   fuzzy scoring from scratch).

3. Also log retrieval-only metrics (e.g. whether the gold supporting facts
   were present in the retrieved context) separately from final-answer
   correctness, since these can diverge and both are informative.

4. Output a results table (CSV or markdown) comparing all three
   configurations, plus a note on where you're benchmarking against a
   published baseline number from the literature survey for the same
   dataset subset.

5. Write evaluation/README.md explaining the metrics, the evaluation subset
   size, and how to reproduce a run.
```

**Verify:** confirm the numbers are sane (hybrid should generally beat
vector-only on multi-hop questions per the DA1 literature survey findings —
if it doesn't, that's worth investigating before treating it as a report result).

**Commit:** `Phase 10: evaluation harness and baseline comparison`

---

## Phase 11 — Deployment

**Goal:** a live, demoable instance, entirely on free tiers.

```
Deploy the full stack for free.

1. Deploy the FastAPI backend to Render's free tier (or Railway free
   credits) — set up the build/start commands, and configure all required
   environment variables through the platform's dashboard, not committed
   files.

2. Deploy the Next.js frontend to Vercel free tier, pointed at the deployed
   backend URL via an environment variable.

3. Confirm Neo4j AuraDB Free and Supabase free tier are both reachable from
   the deployed backend (not just localhost).

4. Add a DEPLOYMENT.md documenting the deployed URLs, how to redeploy, and
   the free-tier limits to watch (Render free tier sleeps after inactivity —
   note the cold-start behavior so it doesn't look broken during a demo).

5. Do a full smoke test against the deployed instance: create a notebook,
   upload a document, ask a question, confirm citations and graph view work
   in production, not just locally.
```

**Verify:** the smoke test above, from a browser, not curl.

**Commit:** `Phase 11: free-tier deployment configuration`

---

## Quick reference — phase-to-deadline mapping

- Phases 1-4 (services, ingestion, embeddings, graph): core pipeline, needed
  before DA2 implementation can be demonstrated
- Phases 5-8 (retrieval, generation, API, frontend): completes the working
  system for DA2's "implementation" requirement
- Phase 9 (novelty): what differentiates your DA2/DA3 report from a plain
  GraphRAG reimplementation
- Phase 10 (evaluation): directly satisfies DA2's "comparison with SOTA
  baselines" requirement
- Phase 11 (deployment): optional but strengthens a live demo for DA3
