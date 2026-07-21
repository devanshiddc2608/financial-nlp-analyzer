import json
import threading
import time
import uuid

from flask import Flask, render_template, request
from groq import Groq
from config import Config
from file_extractors import extract_text_from_upload

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024   # 100 MB upload limit (files)
app.config["MAX_FORM_MEMORY_SIZE"] = 5 * 1024 * 1024    # 5 MB for pasted textarea text

client = Groq(api_key=Config.GROQ_API_KEY)

# Seconds to wait between chunk calls so Groq's per-minute token window resets.
# Kept as a module-level variable (not Config) so tests can override it without touching .env.
WAIT_BETWEEN_CHUNKS_SECONDS = 65

# In-memory job tracker: {job_id: {status, progress_message, current_chunk, total_chunks, result, error}}
# NOTE: this only works correctly with a SINGLE server process (see Procfile: --workers 1).
# With multiple workers, each has its own copy of JOBS and polling would hit the wrong one.
JOBS = {}
JOBS_LOCK = threading.Lock()

SYSTEM_PROMPT = """You are a financial analyst assistant that performs structured extraction \
and analysis on financial statement content. You are NOT a conversational chatbot — you output \
structured analysis only.

The input you receive may be one of two kinds:
1. Narrative text (MD&A, Risk Factors, earnings commentary, annual report excerpts).
2. Tabular data extracted from a spreadsheet or PDF (e.g. an income statement, balance sheet, or \
cash flow statement rendered as a plain-text table with rows and columns of numbers).

For narrative text: focus on qualitative growth drivers, disclosed risks, tone, and hedging language.
For tabular data: focus on notable trends, ratios, or anomalies visible in the numbers themselves \
(e.g. revenue or margin changes across periods/columns, unusual jumps, negative values) and treat \
these as the "growth_drivers" / "red_flags" instead of narrative sentences.

Given the input, respond with ONLY a valid JSON object (no markdown, \
no commentary) with exactly this structure:

{
  "sentiment": {
    "label": "Positive" | "Neutral" | "Cautious" | "Negative",
    "reasoning": "one sentence explaining the label"
  },
  "growth_drivers": ["driver 1", "driver 2", "driver 3"],
  "risk_factors": [
    {"risk": "short description", "category": "market_risk" | "credit_risk" | "operational_risk" | "regulatory_risk" | "competitive_risk" | "liquidity_risk" | "cybersecurity_risk" | "currency_risk" | "other"}
  ],
  "red_flags": ["any unusual disclosures, hedging language spikes, or notable concerns — empty list if none"],
  "executive_summary": "2-3 sentence summary a CFO or analyst could read in 10 seconds"
}

Rules:
- Base every field ONLY on the text provided — do not invent figures, company names, or facts not in the text.
- If the text is too short or not financial in nature, still return valid JSON with empty lists and a sentiment of "Neutral", and say so in executive_summary.
- growth_drivers and risk_factors should each have at most 5 items.
- Keep each risk description under 20 words.
"""


def analyze_text(text: str) -> dict:
    """Sends a single block of financial text to Groq and returns parsed structured JSON.
    Caller is responsible for keeping `text` under Groq's per-minute token limit."""
    completion = client.chat.completions.create(
        model=Config.MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze the following financial statement excerpt:\n\n{text}"},
        ],
        temperature=Config.TEMPERATURE,
        max_tokens=Config.MAX_TOKENS,
        response_format={"type": "json_object"},
    )
    raw = completion.choices[0].message.content
    return json.loads(raw)


def chunk_text(text: str, max_chars: int) -> list[str]:
    """Splits text into word-safe chunks, each under max_chars."""
    words = text.split()
    chunks, current, current_len = [], [], 0
    for w in words:
        current.append(w)
        current_len += len(w) + 1
        if current_len >= max_chars:
            chunks.append(" ".join(current))
            current, current_len = [], 0
    if current:
        chunks.append(" ".join(current))
    return chunks


def merge_chunk_results(results: list[dict]) -> dict:
    """Combines per-chunk analysis JSON into one final structured result."""
    if not results:
        return {
            "sentiment": {"label": "Neutral", "reasoning": "No content was analyzed."},
            "growth_drivers": [],
            "risk_factors": [],
            "red_flags": [],
            "executive_summary": "No content was analyzed.",
        }

    # Worst-case sentiment wins across chunks (a single very negative section should dominate)
    severity_order = ["Negative", "Cautious", "Neutral", "Positive"]
    labels = [r.get("sentiment", {}).get("label", "Neutral") for r in results]
    overall_label = min(labels, key=lambda l: severity_order.index(l) if l in severity_order else 2)

    def dedupe(items):
        seen, out = set(), []
        for item in items:
            key = item.strip().lower()
            if key and key not in seen:
                seen.add(key)
                out.append(item)
        return out

    growth_drivers = dedupe([d for r in results for d in r.get("growth_drivers", [])])

    seen_risks, merged_risks = set(), []
    for r in results:
        for rf in r.get("risk_factors", []):
            key = rf.get("risk", "").strip().lower()
            if key and key not in seen_risks:
                seen_risks.add(key)
                merged_risks.append(rf)

    red_flags = dedupe([f for r in results for f in r.get("red_flags", [])])

    summaries = [r.get("executive_summary", "").strip() for r in results if r.get("executive_summary")]

    return {
        "sentiment": {
            "label": overall_label,
            "reasoning": f"Aggregated (worst-case) sentiment across {len(results)} sections of the document.",
        },
        "growth_drivers": growth_drivers[:5],
        "risk_factors": merged_risks[:8],
        "red_flags": red_flags[:5],
        "executive_summary": " ".join(summaries[:3]) or "No summary could be generated.",
        "chunked": True,
        "chunk_count": len(results),
    }


def run_chunked_analysis(job_id: str, text: str):
    """Background-thread target: analyzes text in chunks, updating JOBS[job_id] as it goes."""
    chunks = chunk_text(text, Config.SINGLE_REQUEST_CHAR_LIMIT)
    total = len(chunks)

    with JOBS_LOCK:
        JOBS[job_id]["status"] = "running"
        JOBS[job_id]["total_chunks"] = total

    results = []
    for i, chunk in enumerate(chunks, start=1):
        with JOBS_LOCK:
            JOBS[job_id]["current_chunk"] = i
            JOBS[job_id]["progress_message"] = f"Analyzing section {i} of {total}..."

        try:
            chunk_result = analyze_text(chunk)
            results.append(chunk_result)
        except Exception as e:
            with JOBS_LOCK:
                JOBS[job_id]["status"] = "error"
                JOBS[job_id]["error"] = f"Failed on section {i} of {total}: {e}"
            return

        # Wait before the next chunk to reset Groq's per-minute token window (skip after the last chunk)
        if i < total:
            for remaining in range(WAIT_BETWEEN_CHUNKS_SECONDS, 0, -1):
                with JOBS_LOCK:
                    JOBS[job_id]["progress_message"] = (
                        f"Section {i}/{total} done. Waiting {remaining}s before section {i + 1} "
                        f"(Groq rate-limit reset)..."
                    )
                time.sleep(1)

    merged = merge_chunk_results(results)
    with JOBS_LOCK:
        JOBS[job_id]["status"] = "done"
        JOBS[job_id]["result"] = merged
        JOBS[job_id]["progress_message"] = "Done."


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    input_text = ""
    uploaded_filename = None
    job_id = None

    if request.method == "POST":
        pasted_text = request.form.get("financial_text", "").strip()
        uploaded_file = request.files.get("financial_file")

        extracted_text = ""

        if uploaded_file and uploaded_file.filename:
            try:
                extracted_text = extract_text_from_upload(uploaded_file).strip()
                uploaded_filename = uploaded_file.filename
            except ValueError as e:
                error = str(e)
        elif pasted_text:
            extracted_text = pasted_text
            input_text = pasted_text
        else:
            error = "Please paste some text or upload a file (.txt, .pdf, .csv, .xlsx, .xls)."

        if not error:
            if not extracted_text:
                error = "No readable text could be extracted from the input."
            elif len(extracted_text) > Config.MAX_INPUT_CHARS:
                est_chunks = -(-len(extracted_text) // Config.SINGLE_REQUEST_CHAR_LIMIT)  # ceil division
                est_minutes = round((est_chunks - 1) * WAIT_BETWEEN_CHUNKS_SECONDS / 60, 1) if est_chunks > 1 else 0
                hint = ""
                if len(extracted_text) > 500000:
                    hint = (
                        " This looks like a full raw filing rather than an extracted section — "
                        "try uploading just the MD&A or Risk Factors text instead "
                        "(e.g. your notebook 01 '_mdna.txt' or '_risk.txt' output)."
                    )
                error = (
                    f"Extracted text too long ({len(extracted_text):,} chars, "
                    f"limit {Config.MAX_INPUT_CHARS:,}).{hint} Raising MAX_INPUT_CHARS to fit this "
                    f"would need roughly {est_chunks} chunks and ~{est_minutes} minutes to analyze "
                    f"due to Groq's per-minute rate limit — not recommended for full documents."
                )
            elif not Config.GROQ_API_KEY:
                error = "Server is missing GROQ_API_KEY — set it in your environment variables."
            elif len(extracted_text) <= Config.SINGLE_REQUEST_CHAR_LIMIT:
                # Fast path: fits in one Groq call, analyze immediately, no job needed
                try:
                    result = analyze_text(extracted_text)
                except json.JSONDecodeError:
                    error = "The model returned an unexpected format. Please try again."
                except Exception as e:
                    error = f"Analysis failed: {e}"
            else:
                # Slow path: too long for one call, run chunked analysis in the background
                job_id = str(uuid.uuid4())
                with JOBS_LOCK:
                    JOBS[job_id] = {
                        "status": "starting",
                        "progress_message": "Starting analysis...",
                        "current_chunk": 0,
                        "total_chunks": 0,
                        "result": None,
                        "error": None,
                    }
                thread = threading.Thread(
                    target=run_chunked_analysis, args=(job_id, extracted_text), daemon=True
                )
                thread.start()

    return render_template(
        "index.html",
        result=result,
        error=error,
        input_text=input_text,
        uploaded_filename=uploaded_filename,
        job_id=job_id,
    )


@app.route("/status/<job_id>")
def status(job_id):
    """Polled by the browser every few seconds while a chunked analysis runs."""
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        return {"status": "not_found"}, 404
    return {
        "status": job["status"],
        "progress_message": job.get("progress_message", ""),
        "current_chunk": job.get("current_chunk", 0),
        "total_chunks": job.get("total_chunks", 0),
        "error": job.get("error"),
    }


@app.route("/result/<job_id>")
def show_result(job_id):
    """Shown once a chunked analysis job completes. Cleans up the job after displaying it."""
    with JOBS_LOCK:
        job = JOBS.pop(job_id, None)

    if not job:
        return render_template(
            "index.html", result=None, error="Job not found or already viewed.",
            input_text="", uploaded_filename=None, job_id=None,
        )

    if job["status"] == "error":
        return render_template(
            "index.html", result=None, error=job.get("error", "Unknown error occurred."),
            input_text="", uploaded_filename=None, job_id=None,
        )

    return render_template(
        "index.html", result=job.get("result"), error=None,
        input_text="", uploaded_filename=None, job_id=None,
    )


@app.errorhandler(413)
def file_too_large(e):
    max_mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
    return render_template(
        "index.html",
        result=None,
        error=f"Uploaded file is too large. Please upload a file under {max_mb} MB.",
        input_text="",
        uploaded_filename=None,
        job_id=None,
    ), 413


@app.route("/health")
def health():
    """Simple health check endpoint for Render."""
    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
