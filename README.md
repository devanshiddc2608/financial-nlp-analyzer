# AI-Powered Financial Statement Analysis

**Automated extraction of risk factors, sentiment, and analyst insights from annual reports —
structured extraction and analysis, not a chatbot.**

## The business problem

Equity research analysts, credit analysts, and internal strategy teams spend two to three hours
manually reading a single company's annual report before any real analysis begins — identifying
disclosed risks, gauging tone, and pulling out growth commentary buried across 50–100+ pages of
narrative text. This project builds an automated first-pass extraction pipeline that compresses
that initial read to a few minutes, using classical NLP techniques to pull structured, auditable
data out of unstructured filing text.

**This is not a chatbot.** Every output is a structured field — a categorized risk, a dictionary-
based sentiment score, an extracted growth driver — traceable back to the exact sentence it came
from. There is no free-form conversational generation in the core pipeline.

## Companies analyzed

| Company | Sector | Filing source |
|---|---|---|
| JPMorgan Chase | Banking / BFSI | SEC EDGAR 10-K |
| Caterpillar | Industrial Manufacturing | SEC EDGAR 10-K |
| Accenture | IT Services | SEC EDGAR 10-K |
| Procter & Gamble | Consumer Goods | SEC EDGAR 10-K |
| Infosys | IT Services (India) | Company Annual Report (PDF) |

Chosen deliberately across four sectors and two filing jurisdictions (US 10-K vs. Indian annual
report) to stress-test how well one extraction pipeline generalizes — see **Key Findings** below
for what that stress test actually revealed.

## Key findings

- **Risk profile tracks sector, as expected**: JPMorgan's top risk categories are regulatory
  (75 disclosed sentences) and liquidity (22); Caterpillar's are market (17) and liquidity (17) —
  consistent with a capital-intensive manufacturer's commodity and financing exposure.
- **JPMorgan is both the most negatively toned and most heavily hedged filer** of the five
  (highest Negative %, Uncertainty %, and Litigious % scores in the Risk Factors section) —
  consistent with a systemically important bank's legally cautious disclosure style.
- **Keyword-based risk classification does not generalize across filing jurisdictions without
  adaptation**: it returned zero matches across all seven risk categories for Infosys, despite
  successfully extracting 7,514 characters of real risk disclosure text. This is a genuine,
  demonstrated limitation — documented in detail in `Phase12_Validation_and_Limitations.md` —
  not a data extraction failure.

## Methodology

1. **PDF/HTML extraction & section splitting** — pdfplumber + BeautifulSoup, with regex-based
   isolation of MD&A (Item 7) and Risk Factors (Item 1A) from each filing.
2. **Named Entity Recognition** — spaCy (`en_core_web_sm`) for entities; regex for financial
   figures where deterministic pattern matching outperforms model-based extraction.
3. **Financial sentiment scoring** — the Loughran-McDonald dictionary, purpose-built for
   financial text (Negative / Positive / Uncertainty / Litigious / Constraining).
4. **Risk categorization** — sentence-level keyword matching against a seven-category taxonomy
   (market, credit, operational, regulatory, competitive, liquidity, cybersecurity risk).
5. **Extractive summarization** — Hugging Face `distilbart-cnn-12-6`, chosen over abstractive
   summarization specifically because it only ever surfaces real sentences from the source text,
   eliminating the risk of an invented figure in a financial context.
6. **One-page analyst briefs** — auto-generated per company, combining sections 1–5 into a
   consistent, professional single-page format, exported as PDF.
7. **LLM-based companion analyzer** (`financial-analyzer-app/`) — a Flask + Groq (Llama 3.3 70B)
   web app that performs the same style of structured extraction on-demand for arbitrary pasted
   text or uploaded files (.txt/.pdf/.csv/.xlsx), with strict JSON-schema output and chunked
   processing with a live progress bar for long documents — demonstrating the same "structured
   extraction, not a chatbot" positioning via an LLM rather than classical NLP.

## Tech stack

`Python` · `pandas` · `spaCy` · `Hugging Face Transformers` · `Loughran-McDonald Dictionary` ·
`pdfplumber` · `BeautifulSoup` · `Flask` · `Groq API (Llama 3.3 70B)` · `fpdf2`

## Repository structure

```
financial-nlp-analyzer/
├── notebooks/
│   ├── 01_pdf_extraction.ipynb          # PDF/HTML → clean text, section splitting
│   ├── 02_ner_extraction.ipynb          # spaCy NER + regex financial figure extraction
│   ├── 03_sentiment_analysis.ipynb      # Loughran-McDonald sentiment scoring
│   ├── 04_risk_categorization.ipynb     # Risk taxonomy classification + cross-company comparison
│   └── 05_summarization.ipynb           # Extractive summarization + one-page briefs
├── data/
│   ├── raw_pdfs/                        # original downloaded filings
│   ├── extracted_text/                  # per-company MD&A / Risk Factors .txt files
│   └── processed/                       # company_extractions.csv, sentiment_scores.csv,
│                                         #   cross_company_comparison.csv
├── outputs/
│   └── one_page_briefs_pdf/             # final formatted one-page analyst briefs (PDF)
├── financial-analyzer-app/              # companion Flask + Groq web app (see its own README)
├── Financial_Statement_Analysis_Report.docx   # Phase 13 consulting-style write-up
├── Phase12_Validation_and_Limitations.md      # spot-check evidence + honest limitations
└── README.md                            # this file
```

## Setup

```bash
pip install pandas spacy transformers torch pdfplumber beautifulsoup4 --break-system-packages
python -m spacy download en_core_web_sm
```

Download the Loughran-McDonald Master Dictionary from
[sraf.nd.edu/loughranmcdonald-master-dictionary](https://sraf.nd.edu/loughranmcdonald-master-dictionary/)
and place it at `dictionaries/loughran_mcdonald.csv`.

Run notebooks 01 → 05 in order; each reads fresh from disk rather than depending on prior
notebooks' in-memory state, so any notebook can be re-run independently once 01 has produced the
extracted text files.

## What this tool can and cannot replace

This is a first-pass screening tool, not an analyst replacement. It tells you *where to look* —
which company has the most hedged language this quarter, which risk categories are newly
emphasized — rather than replacing the judgment required to interpret those signals. See
`Phase12_Validation_and_Limitations.md` for the full, evidence-backed breakdown of what was
validated and where the real limits are.
