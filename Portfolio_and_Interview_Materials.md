# Portfolio & Interview Materials

## Resume bullet (2–3 lines, numbers-driven)

> Built an NLP pipeline extracting and classifying risk factors, financial sentiment, and growth
> drivers from 5 companies' annual reports (10-K filings + Indian annual report) across 4 sectors,
> using spaCy NER and the Loughran-McDonald financial dictionary; identified 268+ distinct
> disclosed risk sentences across 3 confirmed companies and generated auto-summarized one-page
> analyst briefs per company. Companion Flask + Groq LLM app extends the same structured-extraction
> approach to arbitrary uploaded financial documents (PDF/CSV/Excel), deployed on Render.

*(268 = confirmed sum of riskcount_* columns for JPMorgan, Caterpillar, and P&G only. Accenture's
risk-section extraction needed a mid-project fix — re-run notebook 04 and confirm Accenture's
numbers are non-zero before including its count in this total. Infosys returned zero matches for a
documented, different reason — see the Limitations doc — so it's excluded from this count by
design, not omitted by accident.)*

## Portfolio website project card

**Title:** AI-Powered Financial Statement Analysis

**One-line description:** Automated NLP pipeline that extracts risk factors, sentiment, and
growth drivers from annual reports across 5 companies and 4 sectors — structured extraction,
not a chatbot.

**Tags:** `Python` `spaCy` `Hugging Face` `NLP` `Financial Analysis` `Flask` `Groq API`
`Loughran-McDonald`

**Outcome sentence:** Reduced first-pass annual report review from ~2–3 hours to under 5 minutes
per company, while surfacing a genuine cross-jurisdiction limitation in keyword-based risk
classification that a production version would need to address.

## Two-minute interview pitch (practice script)

**[0:00–0:20] The problem**
"Analysts spend two to three hours manually reading a single annual report before their real
analysis even starts — reading through risk disclosures, gauging tone, pulling out growth drivers.
I wanted to see how much of that first pass could be automated with NLP, not with a chatbot, but
with actual structured extraction that an analyst could audit."

**[0:20–0:50] What I built**
"I built a pipeline that takes 10-K filings and annual reports, extracts the MD&A and Risk Factors
sections, and then does three things: scores sentiment using the Loughran-McDonald dictionary,
which is purpose-built for financial text instead of generic sentiment models; classifies each
individual disclosed risk into a standard taxonomy — market, credit, regulatory, and so on; and
generates an extractive summary and a one-page brief per company. I ran this across five companies
in four different sectors — banking, industrials, IT services, and consumer goods — plus one
Indian company, specifically to see how well it generalizes."

**[0:50–1:20] The most interesting finding**
"The most interesting result wasn't a success — it was a limitation I found and documented. The
keyword-based risk classifier worked well on the four US filings, but it returned zero matches for
the Indian company's risk section, even though that section was fully extracted and has 7,500
characters of real risk text. The keyword list I built from US 10-K phrasing just didn't match how
that filing's risks were worded. That told me keyword-based classification doesn't generalize
across filing jurisdictions without more work — and I think being able to say that clearly, with
evidence, matters more than pretending the pipeline is flawless."

**[1:20–1:45] Honest scope**
"I want to be clear this isn't a replacement for an analyst — it's a first-pass screening layer.
It tells you where to look: which company is using the most hedged language this quarter, which
risk categories are newly emphasized. The judgment part still needs a person."

**[1:45–2:00] What's next / extra**
"If I extended it, I'd want multi-year data to do real trend analysis, and I'd fix the
cross-jurisdiction gap with either an expanded keyword taxonomy or a similarity-based classifier.
I also built a small companion web app using an LLM through the Groq API to do the same kind of
structured extraction on-demand for any uploaded document, which was a good way to compare a
classical NLP approach against an LLM-based one on the same task."

---

### Common interview follow-up questions to be ready for

- **"Why Loughran-McDonald instead of a general sentiment model?"** → General models often
  misclassify neutral financial terms (e.g. "significant," "liability") as negative; L&M was
  built specifically from financial filing text.
- **"Why extractive summarization instead of abstractive?"** → Abstractive models can generate
  fluent but factually invented content — unacceptable risk for financial figures. Extractive
  guarantees every summary sentence is real, sourced text.
- **"How did you validate accuracy?"** → Manually spot-checked a 10% sample of classified risk
  sentences on two companies against the category definitions; documented in
  `Phase12_Validation_and_Limitations.md` with the actual sentences reviewed.
- **"What would you do differently with more time?"** → Multi-year data for trend analysis, and
  a jurisdiction-aware or embedding-based fallback for risk classification instead of only
  keyword matching.
