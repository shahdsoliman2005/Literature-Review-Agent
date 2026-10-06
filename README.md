# Research Literature Review Agent

An LLM-powered assistant that reads research papers (PDF), extracts structured information from each one, answers questions across all of them with citations, and produces a comparison table with a first draft of a **Related Work** section.

The language model runs on a free Kaggle GPU (4-bit quantized), is exposed through a FastAPI server and an ngrok tunnel, and is used from a Streamlit app running on your own machine.

---

## Features

- **Structured extraction.** Each paper is turned into validated JSON: title, problem, method, dataset, results, and limitations. Invalid model output is detected and retried automatically.
- **Question answering with sources (RAG).** Ask a question across all uploaded papers. Answers are grounded in retrieved passages and cite the paper and section they came from.
- **Comparison and Related Work.** A two-step chain builds a comparison table from the extracted data, then drafts Related Work paragraphs from that table.
- **Abstract writer.** Generates an academic-style abstract for any paper. Optionally improved with a LoRA adapter.
- **Private by design.** The model and the papers stay in your own Kaggle session. The API is protected by a bearer key.

---

## Architecture

```
 Your machine                              Kaggle (GPU T4)
┌──────────────────┐   HTTPS (ngrok)   ┌─────────────────────────────────────────┐
│ Streamlit app    │ ────────────────▶ │ FastAPI server                          │
│ app_local.py     │ ◀──────────────── │  ├─ PDF text extraction (pypdf)         │
└──────────────────┘                   │  ├─ Extraction chain + Pydantic parser  │
                                       │  ├─ RAG: section-aware chunks,          │
                                       │  │   BGE embeddings, FAISS index        │
                                       │  ├─ Compare chain → Related Work        │
                                       │  └─ Qwen2.5-7B-Instruct (4-bit, NF4)    │
                                       │      + optional LoRA adapter            │
                                       └─────────────────────────────────────────┘
```

**Pipeline**

```
PDF → text → extract_info (validated JSON)
          ↘ split by section → chunks → embeddings → FAISS

question → retrieve top-k chunks → LLM answer + cited sources
all papers' JSON → comparison table → Related Work draft
paper text → abstract (base model, or LoRA-tuned model)
```

---

## Tech stack

| Area | Choice |
|---|---|
| LLM | `Qwen/Qwen2.5-7B-Instruct`, 4-bit NF4 quantization with `bitsandbytes` |
| Fine-tuning (optional) | QLoRA with `peft` and `transformers.Trainer` |
| Embeddings | `BAAI/bge-base-en-v1.5` via `sentence-transformers` |
| Vector search | FAISS `IndexFlatIP` on normalized vectors (cosine similarity) |
| Output validation | Pydantic with retry on invalid JSON |
| Backend | FastAPI and Uvicorn |
| Tunnel | ngrok through `pyngrok` |
| Frontend | Streamlit |

---

## Repository structure

```
.
├── 1_kaggle_server.ipynb      # Model, RAG, chains, API, ngrok (runs on Kaggle)
├── 2_lora_finetune.ipynb      # Optional: QLoRA training for abstract writing (runs on Kaggle)
├── app_local.py               # Streamlit interface (runs on your machine)
├── .streamlit/
│   └── config.toml            # Light theme and upload size for the interface
└── README.md
```

---

## Getting started

### Requirements

- A Kaggle account with phone verification (needed for GPU and internet access)
- A free ngrok account and its authtoken
- Python 3.9 or newer on your local machine

### 1. Run the server on Kaggle

1. Create a new Kaggle notebook and import `1_kaggle_server.ipynb` (**File → Import Notebook**).
2. In the session options, set **Accelerator** to GPU T4 and turn **Internet** on.
3. Open **Add-ons → Secrets**, add a secret named `NGROK_TOKEN` with your ngrok authtoken, and attach it to the notebook.
4. In the second code cell, change `API_KEY` to your own secret value.
5. Run the cells in order. The first model download takes several minutes.
6. The last cell prints `Public URL: https://...` and keeps running. **Leave it running** while you use the app.

> If a cell asks you to restart the session after the `pip install` step, restart it and continue from the cell after the installation.

### 2. Run the interface locally

```bash
pip install streamlit requests pandas
streamlit run app_local.py
```

Place `config.toml` inside a `.streamlit` folder next to `app_local.py`.

In the sidebar, paste the **Public URL** from Kaggle into *Server address*, enter the same key you set as `API_KEY`, and press **Check connection**. When it reports a connection, you are ready.

### 3. Use it

1. **Papers:** add two or more PDFs and choose *Read papers*. Each paper takes a few minutes. Check the extracted fields for accuracy.
2. **Ask:** type a question about your papers. The answer cites sources, and the passages used are listed below it.
3. **Compare:** generate the comparison table and the Related Work draft.

---

## Optional: LoRA fine-tuning

Everything works without this step. Fine-tuning only improves how closely the abstract writer follows an academic style.

1. Run `2_lora_finetune.ipynb` in a **separate** Kaggle session (GPU T4, internet on). Training and serving cannot share one GPU. Expect roughly an hour or more.
2. The default dataset is `ccdv/arxiv-summarization`. If it fails to load with your `datasets` version, set `LOCAL_JSONL` to your own file with `article` and `abstract` fields.
3. The adapter is saved to `/kaggle/working/lora_abstract`. Turn it into a Kaggle Dataset.
4. In the server notebook, attach that dataset and set `ADAPTER_PATH` to the adapter folder, then restart the server.

The system prompt used for abstracts (`SUM_SYS`) must be identical in both notebooks.

---

## API reference

All endpoints except `/health` require the header `Authorization: Bearer <API_KEY>`.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Check that the server is running and how many papers are loaded |
| POST | `/upload` | Upload one PDF (multipart field `file`), extract its data, and update the index |
| GET | `/papers` | List loaded papers and their extracted data |
| POST | `/ask` | Body: `{"question": "...", "k": 5}`. Returns the answer and the passages used |
| POST | `/compare` | Returns the comparison table and the Related Work draft (needs 2 or more papers) |
| POST | `/summarize` | Body: `{"name": "<file name>"}`. Returns an abstract |
| POST | `/reset` | Remove all papers |

Example:

```bash
curl -X POST "$URL/ask" \
  -H "Authorization: Bearer $API_KEY" \
  -H "ngrok-skip-browser-warning: true" \
  -H "Content-Type: application/json" \
  -d '{"question": "Which paper uses the largest dataset?", "k": 5}'
```

---

## Design notes

- **Quantization.** A 12B model in fp16 needs roughly 24 GB, more than a single T4 offers. A 7B model in 4-bit uses a small fraction of that, leaving room for the embedding model and long prompts.
- **Section-aware chunking.** Papers are split at headings such as Abstract, Methods, and Results, then into 200-word chunks with a 40-word overlap. Every chunk keeps its paper and section, which makes citations possible.
- **Retries on bad JSON.** The extraction step feeds the validation error back to the model and tries again, up to three attempts in total.
- **One GPU request at a time.** A lock serializes generation so concurrent requests cannot collide on the GPU.
- **Long papers.** For extraction, only the first 14,000 and last 4,000 characters are used. This usually covers the title, method, results, and conclusion, but details from the middle may be missed. Question answering searches the full text.

---

## Limitations

- Scanned PDFs without a text layer are rejected, since there is no OCR step.
- Papers and the index live in memory. They are lost when the Kaggle session ends or the server restarts.
- The ngrok address changes every time the tunnel is recreated, so update it in the app.
- Kaggle limits weekly GPU hours and session length.
- Extraction and comparison quality depends on the model. Always verify results against the original papers, and treat the Related Work output as a draft.

---

## Troubleshooting

| Problem | What to check |
|---|---|
| `asyncio.run() cannot be called from a running event loop` | The last notebook cell must use `await server.serve()` and must not call `uvicorn.run(...)` |
| Opening the ngrok address shows `{"detail":"Not Found"}` | This is expected. Open `/health` to test the server |
| `401 Invalid API key` | The key in the app must match `API_KEY` in the notebook exactly |
| Connection fails | Make sure the Kaggle cell is still running, and that the address has no trailing spaces |
| Out of GPU memory | Reduce `max_new_tokens`, or shorten the text passed to `extract_info` |
| Dataset fails to load in the LoRA notebook | Use `LOCAL_JSONL` with your own `article` and `abstract` data |

---

## Security

- Change the default `API_KEY` before starting the server.
- Never commit your ngrok token or API key. Keep the token in Kaggle Secrets.
- Anyone with the ngrok address and the key can use your server, so share neither publicly.

---

## Possible extensions

- Add OCR for scanned PDFs
- Store the index on disk so it survives restarts
- Add a reranker after retrieval for more precise answers
- Export the comparison table and Related Work draft to Word or LaTeX
- Evaluate extraction accuracy on a small set of papers with known answers
