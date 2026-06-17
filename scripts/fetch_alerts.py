#!/usr/bin/env python3
"""
Runs in GitHub Actions before the scan. Two jobs:

1. Writes state/targets-this-run.md — a small ROTATING slice of the target companies
   (a few per run) so the scan doesn't fetch all 20 careers pages every week. This is
   the main lever for staying under the Tier-1 30k-input-tokens/minute rate limit.
2. Pulls job-alert emails from the past ~8 days carrying the `job-scout` Gmail label and
   writes them (size-capped) to state/inbox-dump.md.

Auth comes from three repo secrets (set via get_gmail_token.py):
  GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN
If those are missing, the email step is skipped (exit 0) but the rotation file is still
written, so the web-only scan still runs.
"""
import base64
import json
import os
import re
import sys
from html import unescape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(ROOT, "state")
DUMP_PATH = os.path.join(STATE_DIR, "inbox-dump.md")
TARGETS_PATH = os.path.join(STATE_DIR, "targets-this-run.md")
STATE_PATH = os.path.join(STATE_DIR, "run-state.json")
TARGET_LIST = os.path.join(ROOT, "target-companies.md")

LABEL_NAME = "job-scout"
LOOKBACK = "newer_than:8d"
MAX_THREADS = 60

# Token-control caps (Tier 1 friendly)
TARGET_BATCH = 4        # target companies checked per run (20 / 4 = full sweep every 5 runs)
MAX_MSG_CHARS = 2000    # per email body
MAX_DUMP_CHARS = 30000  # whole inbox dump


def _write(path, text):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# ---------- target-company rotation ----------

def _parse_targets():
    """Read the markdown table in target-companies.md -> list of (company, careers_url)."""
    rows = []
    if not os.path.exists(TARGET_LIST):
        return rows
    with open(TARGET_LIST, encoding="utf-8") as f:
        for line in f:
            if not line.strip().startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and cells[0].isdigit():
                company = cells[1]
                url = cells[3] if len(cells) >= 4 else ""
                rows.append((company, url))
    return rows


def write_target_rotation():
    try:
        with open(STATE_PATH) as f:
            runs = json.load(f).get("total_runs", 0)
    except (FileNotFoundError, json.JSONDecodeError):
        runs = 0

    targets = _parse_targets()
    if not targets:
        _write(TARGETS_PATH, "# Target companies this run\n\n_(none parsed)_\n")
        return

    n = len(targets)
    start = (runs * TARGET_BATCH) % n
    batch = [targets[(start + i) % n] for i in range(min(TARGET_BATCH, n))]

    lines = [f"# Target companies to check THIS run (rotating {TARGET_BATCH} of {n})\n"]
    lines.append(f"_Run index {runs}; next run advances the window._\n")
    for company, url in batch:
        lines.append(f"- **{company}** — {url or '(find careers page via search)'}")
    _write(TARGETS_PATH, "\n".join(lines) + "\n")
    print(f"Target rotation: {[c for c, _ in batch]}")


# ---------- email ingest ----------

def _strip_html(html):
    html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</p>", "\n", html)
    html = re.sub(r"<[^>]+>", " ", html)
    text = unescape(html)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


def _decode(data):
    return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", "replace")


def _extract_body(payload):
    plain, html = [], []

    def walk(part):
        mime = part.get("mimeType", "")
        body = part.get("body", {})
        data = body.get("data")
        if data and mime == "text/plain":
            plain.append(_decode(data))
        elif data and mime == "text/html":
            html.append(_strip_html(_decode(data)))
        for sub in part.get("parts", []) or []:
            walk(sub)

    walk(payload)
    body = ("\n".join(plain) if plain else "\n".join(html)).strip()
    if len(body) > MAX_MSG_CHARS:
        body = body[:MAX_MSG_CHARS] + "\n…[truncated]"
    return body


def ingest_email():
    cid = os.environ.get("GMAIL_CLIENT_ID")
    csecret = os.environ.get("GMAIL_CLIENT_SECRET")
    rtoken = os.environ.get("GMAIL_REFRESH_TOKEN")
    if not (cid and csecret and rtoken):
        _write(DUMP_PATH, "# Inbox dump\n\n_Gmail secrets not set — web sources only._\n")
        print("Gmail secrets not set — skipping email ingest.")
        return

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        _write(DUMP_PATH, "# Inbox dump\n\n_google api libs missing._\n")
        print("google api libs missing.")
        return

    creds = Credentials(
        token=None, refresh_token=rtoken, client_id=cid, client_secret=csecret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
        ],
    )
    svc = build("gmail", "v1", credentials=creds)

    labels = svc.users().labels().list(userId="me").execute().get("labels", [])
    label_id = next((l["id"] for l in labels if l["name"].lower() == LABEL_NAME), None)
    if not label_id:
        _write(DUMP_PATH, f"# Inbox dump\n\n_Label '{LABEL_NAME}' not found._\n")
        print(f"Label '{LABEL_NAME}' not found.")
        return

    resp = svc.users().threads().list(
        userId="me", labelIds=[label_id], q=LOOKBACK, maxResults=MAX_THREADS
    ).execute()
    threads = resp.get("threads", [])

    chunks = [f"# Inbox dump — {len(threads)} thread(s), label '{LABEL_NAME}', {LOOKBACK}\n"]
    total = len(chunks[0])
    for t in threads:
        full = svc.users().threads().get(userId="me", id=t["id"], format="full").execute()
        for msg in full.get("messages", []):
            headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
            body = _extract_body(msg["payload"])
            if not body:
                continue
            block = (
                f"\n\n---\n## {headers.get('subject', '(no subject)')}\n"
                f"**From:** {headers.get('from', '?')} · **Date:** {headers.get('date', '')}\n\n{body}\n"
            )
            if total + len(block) > MAX_DUMP_CHARS:
                chunks.append("\n\n_[dump truncated to stay within token budget]_\n")
                _write(DUMP_PATH, "".join(chunks))
                print(f"Wrote {DUMP_PATH} (capped) from {len(threads)} thread(s).")
                return
            chunks.append(block)
            total += len(block)

    _write(DUMP_PATH, "".join(chunks))
    print(f"Wrote {DUMP_PATH} from {len(threads)} thread(s).")


def main():
    write_target_rotation()  # always runs, even without Gmail
    ingest_email()
    sys.exit(0)


if __name__ == "__main__":
    main()
