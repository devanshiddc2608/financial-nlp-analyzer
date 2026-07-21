# AI Financial Statement Analyzer

A Flask web app that takes financial statement content — either pasted text or an uploaded
file (.txt, .pdf, .csv, .xlsx, .xls) — and returns structured analysis: sentiment, growth
drivers, categorized risk factors, red flags, and a short executive summary, using Groq's
hosted Llama 3.3 70B model.

This is a companion piece to a classical NLP pipeline (spaCy NER + Loughran-McDonald
dictionary scoring): that pipeline does deterministic, auditable extraction; this app
demonstrates the same extraction task using an LLM, on demand, for arbitrary input —
including raw narrative filings (PDF/TXT) and tabular financial statements (CSV/Excel).

## Supported inputs

- **Paste text** directly (MD&A, Risk Factors excerpts, etc.)
- **Upload a .txt file** (e.g. one of your notebook 01 extracted section files)
- **Upload a .pdf** (e.g. the original Infosys annual report PDF) — text is extracted page by page
- **Upload a .csv or .xlsx/.xls** (e.g. an income statement or balance sheet) — tabular data is
  converted to a readable text table before analysis; multi-sheet Excel files are all included,
  labeled by sheet name

Files up to 100 MB are accepted. If both a file and pasted text are provided, the file takes priority.

## How long documents are handled

Groq's free tier limits requests to 12,000 tokens/minute for this model — well under what a full
MD&A or Risk Factors section can contain (some of the source filings run 100,000+ characters).

- Text under `SINGLE_REQUEST_CHAR_LIMIT` (default 30,000 chars ≈ 7,500 tokens) is analyzed
  immediately in one API call — this is the fast path, used for most single-section files.
- Text over that limit is automatically split into word-safe chunks, analyzed one chunk at a
  time with a short wait between each (to let Groq's per-minute limit reset), and the results
  are merged: sentiment takes the worst-case label across chunks, growth drivers/risks/red flags
  are deduplicated and combined. A live progress bar shows which section is currently being
  analyzed and the countdown until the next one. This can take a few minutes for very long
  documents — the page updates automatically via polling, no need to refresh.
- `MAX_INPUT_CHARS` (default 450,000) is the outer ceiling on what the app accepts at all —
  this is separate from `SINGLE_REQUEST_CHAR_LIMIT`, which governs the size of each individual
  API call within that.

## Local setup

1. Install dependencies:
   ```
   pip install -r requirements.txt --break-system-packages
   ```

2. Get a free Groq API key at https://console.groq.com/keys

3. Copy `.env.example` to `.env` and paste your key in:
   ```
   cp .env.example .env
   ```
   Edit `.env` so it reads:
   ```
   GROQ_API_KEY=gsk_your_actual_key
   ```
   `config.py` loads this automatically via `python-dotenv`. The example file also sets
   `MAX_INPUT_CHARS=450000` and `SINGLE_REQUEST_CHAR_LIMIT=30000` — adjust these if you want a
   different balance between how much the app accepts vs. how large each Groq call is.

4. Run locally:
   ```
   python app.py
   ```
   Open http://localhost:5000

## Deploying to Render (free tier)

1. Push this folder to a GitHub repo.
2. Go to https://dashboard.render.com → **New +** → **Web Service** → connect your repo.
3. Settings:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --workers 1 --timeout 300` (already set in `Procfile`)
4. Under **Environment**, add:
   - `GROQ_API_KEY` — your Groq API key
   - (Optional) `GROQ_MODEL`, `MAX_INPUT_CHARS`, `SINGLE_REQUEST_CHAR_LIMIT`, `GROQ_TEMPERATURE`, `GROQ_MAX_TOKENS` — see `config.py` for defaults
5. Click **Create Web Service**. First deploy takes a few minutes; you'll get a URL like
   `https://your-app.onrender.com`.

**Important — `--workers 1` is required, not optional.** Job progress is tracked in an
in-memory dictionary inside the running process. With more than one gunicorn worker, a status
poll could land on a different worker than the one running the job and get a false "not found."
Don't change this without switching to a shared store (e.g. Redis) first.

Note: Render's free tier spins the service down after inactivity, so the first request
after idle time takes ~30-50 seconds to wake up. This is expected — mention it if you demo
the link live.

## Project structure

```
financial-analyzer-app/
├── app.py                 # Flask routes + Groq calls + chunking/merging + in-memory job tracker
├── config.py               # all settings (API key, model, limits) in one place
├── file_extractors.py      # extracts text from .txt / .pdf / .csv / .xlsx uploads
├── templates/
│   └── index.html         # form (paste OR upload) + progress bar + results, all in one template
├── static/
│   └── style.css          # styling, including progress bar
├── requirements.txt
├── Procfile                # gunicorn --workers 1 --timeout 300 (see note above)
├── .env.example
└── README.md
```

## Notes on the prompt design

- The system prompt forces strict JSON output (`response_format={"type": "json_object"}`)
  so the app never has to parse free-form prose — this mirrors the "structured extraction,
  not a chatbot" positioning from the rest of the portfolio project.
- Temperature is set low (0.2) to keep output consistent and reduce hallucination risk.
- For long documents, each chunk is analyzed independently and results are merged rather than
  sent as one giant request — this keeps every individual API call small and fast, at the cost
  of the model not seeing the full document at once when forming its per-chunk judgments.
