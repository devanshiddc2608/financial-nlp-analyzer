"""
download_edgar_filings.py

Downloads a list of SEC EDGAR 10-K filings (as .htm files) into your
data/raw_pdfs/ folder (or wherever you point it), in one batch run.

Why the User-Agent header matters:
SEC EDGAR blocks/rate-limits requests that don't identify a real requester.
Put your own name and email in USER_AGENT below before running this.
"""

import requests
import time
import os

# ---- CONFIG: edit these two things before running ----
USER_AGENT = "Devanshi Chauhan ddcgames0718@gmail.com"  # <-- REQUIRED by SEC, put your real info
OUTPUT_DIR = "data/raw_pdfs"                       # matches the folder structure from Phase 4

# ---- Company filings to download ----
# filename: what you want it saved as locally
# url: the EDGAR filing URL
FILINGS = [
    {
        "company": "JPMorgan Chase",
        "filename": "jpm_10k_2024.htm",
        "url": "https://www.sec.gov/Archives/edgar/data/19617/000001961725000270/jpm-20241231.htm",
    },
    {
        "company": "Caterpillar",
        "filename": "caterpillar_10k_2024.htm",
        "url": "https://www.sec.gov/Archives/edgar/data/0000018230/000001823025000008/cat-20241231.htm",
    },
    {
        "company": "Accenture",
        "filename": "accenture_10k_2024.htm",
        "url": "https://www.sec.gov/Archives/edgar/data/0001467373/000146737324000278/acn-20240831.htm",
    },
    {
        "company": "Procter & Gamble",
        "filename": "pg_10k_2024.htm",
        "url": "https://www.sec.gov/Archives/edgar/data/0000080424/000008042424000083/pg-20240630.htm",
    },
]


def download_filings(filings=FILINGS, output_dir=OUTPUT_DIR, user_agent=USER_AGENT, delay_seconds=1.5):
    """
    Downloads each filing in `filings` to `output_dir`.

    Parameters:
        filings (list of dict): each dict needs "company", "filename", "url"
        output_dir (str): folder to save files into (created if it doesn't exist)
        user_agent (str): required by SEC EDGAR — your name + email
        delay_seconds (float): pause between requests so we don't hammer SEC's servers
                                (SEC asks for max ~10 requests/second; we go much slower to be safe)

    Returns:
        list of dict: results with success/failure info for each filing
    """
    os.makedirs(output_dir, exist_ok=True)
    headers = {"User-Agent": user_agent}
    results = []

    for i, filing in enumerate(filings, start=1):
        company = filing["company"]
        filename = filing["filename"]
        url = filing["url"]
        filepath = os.path.join(output_dir, filename)

        print(f"[{i}/{len(filings)}] Downloading {company}...")

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()  # raises an error if status isn't 200 OK

            with open(filepath, "wb") as f:
                f.write(response.content)

            size_kb = len(response.content) / 1024
            print(f"    -> Saved to {filepath} ({size_kb:,.0f} KB)")
            results.append({"company": company, "status": "success", "path": filepath, "size_kb": round(size_kb, 1)})

        except requests.exceptions.RequestException as e:
            print(f"    -> FAILED: {e}")
            results.append({"company": company, "status": "failed", "error": str(e)})

        # Be a polite citizen of SEC's servers — small delay between requests
        if i < len(filings):
            time.sleep(delay_seconds)

    # Summary
    print("\n--- Summary ---")
    for r in results:
        if r["status"] == "success":
            print(f"  OK   {r['company']}: {r['path']} ({r['size_kb']} KB)")
        else:
            print(f"  FAIL {r['company']}: {r['error']}")

    return results


if __name__ == "__main__":
    download_filings()
