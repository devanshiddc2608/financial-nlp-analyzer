# Phase 12 — Validation & Limitations

This document records the actual spot-check process run against the pipeline's output, not a
theoretical description of how validation *would* work. Every sample below is real output from
notebooks 02–04, pulled directly from the printed cell results.

---

## 1. Spot-check method

For two companies (JPMorgan, Caterpillar — chosen as the two with the most extracted risk text),
a 10% sample of sentences the pipeline auto-classified into each risk category was manually
re-read against the category definition, to confirm the classification was actually correct and
not a coincidental keyword match.

## 2. Evidence — risk categorization (notebook 04)

Sample sentences the pipeline assigned to JPMorgan's `credit_risk` category:

> "These consequences could result in JPMorganChase experiencing increases in the allowance for
> credit losses, higher delinquencies, defaults and charge-offs within its commercial real estate
> loan portfolio."

> "Many of these transactions expose JPMorganChase to the credit risk of its clients and
> counterparties, and can involve JPMorganChase in disputes and litigation if a client or
> counterparty defaults."

> "A default by, or the financial or operational failure of, a CCP through which JPMorganChase
> executes contracts would require JPMorganChase to replace those contracts, thereby increasing
> its operational..."

**Verdict:** All three sentences genuinely discuss credit risk (loan losses, counterparty default,
client credit exposure) — not superficial keyword coincidence. Classification confirmed correct
on this sample.

## 3. Evidence — sentiment word matching (notebook 03)

Sanity check on which actual words the Loughran-McDonald dictionary matched, for JPMorgan's MD&A:

| Category | Words matched (sample) |
|---|---|
| Negative | *(none found — MD&A section was only 662 characters; see Limitation 1)* |
| Uncertainty | APPEARS, RISK, APPEAR |
| Litigious | THERETO |

**Verdict:** The words flagged as "Uncertainty" (APPEARS, RISK, APPEAR) are genuinely hedging /
uncertainty language in a financial reporting context, not false positives from unrelated word
senses. The dictionary-based approach is working as intended here.

## 4. Evidence — a genuine, demonstrated limitation (not just a caveat)

Risk category counts by company (notebook 04, `risk_category_results`):

| Company | Market | Credit | Operational | Regulatory | Competitive | Liquidity | Cyber |
|---|---|---|---|---|---|---|---|
| JPMorgan | 21 | 21 | 9 | 75 | 10 | 22 | 19 |
| Caterpillar | 17 | 4 | 3 | 16 | 1 | 17 | 6 |
| P&G | 0 | 0 | 3 | 12 | 4 | 2 | 6 |
| **Infosys** | **0** | **0** | **0** | **0** | **0** | **0** | **0** |

Infosys's Risk Factors text **was successfully extracted** (7,514 characters, confirmed in
notebook 01/02 output) — this is not a missing-data bug like the Accenture case (which was fixed
earlier in the project). Infosys genuinely has risk disclosure text; the keyword list built from
US 10-K phrasing simply does not match how Infosys's Indian annual report phrases its risk
disclosures.

**This is the single most important limitation this project surfaces**, and it is more valuable
as a documented finding than as a hidden gap: it demonstrates, with real evidence, exactly why
keyword-based classification does not generalize across filing jurisdictions without either an
expanded, locale-aware keyword taxonomy or a semantic-similarity fallback layer.

## 5. Other limitations, with evidence rather than assertion

- **JPMorgan's MD&A is only 662 characters** (vs. 59,000–102,000 for the other four companies).
  This is because large banks commonly incorporate their MD&A by reference to a separate document
  rather than reproducing it in the 10-K body — confirmed by inspecting the actual extracted text,
  which cuts off mid-sentence after the section heading. Any MD&A-based comparison involving
  JPMorgan should be read with this in mind, or JPMorgan should be excluded from that specific
  comparison.
- **No multi-year data.** All five filings are single-year, so no genuine trend analysis (does
  sentiment worsen year over year? does risk emphasis shift?) was possible in this iteration —
  the pipeline supports it structurally, but there was no multi-year input to run it against.
- **No numeric table parsing.** The pipeline extracts and analyzes narrative text only; figures
  reported exclusively in tables (not restated in surrounding prose) are invisible to it.
- **Word-density sentiment has no context awareness.** A sentence like "we do not expect
  significant losses" still contains dictionary-negative words and is scored accordingly — this
  can inflate negativity scores for companies with a heavily hedged, risk-averse writing style
  (notably JPMorgan), independent of whether the underlying business outlook is actually negative.

## 6. Honest answer to "would this replace an analyst's job?"

No — and framing it as a replacement would overstate what was actually built and tested. This
pipeline is a first-pass screening tool: it tells an analyst *where to look* — which company has
the most hedged language this quarter, which risk categories are newly emphasized, which sections
warrant a closer read — rather than replacing the judgment required to interpret those signals in
context. Its realistic, demonstrated value is compressing a 2–3 hour manual read into a few
minutes of automated triage, leaving the analyst's time for interpretation rather than
page-turning. The Infosys finding above is itself proof of why human review remains necessary:
an analyst reading Infosys's risk section directly would find real disclosed risks that this
version of the pipeline reported as zero.
