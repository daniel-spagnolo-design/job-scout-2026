#!/usr/bin/env python3
"""
Runs in GitHub Actions before the scan. Pulls job-alert emails from the past ~8 days
that carry the `job-scout` Gmail label and writes their text to state/inbox-dump.md.

Auth comes from three repo secrets (set via get_gmail_token.py):
  GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN

If those env vars are missing (e.g. Gmail not set up yet), the script writes an empty
dump with a note and exits 0 so the web-only portion of the run still proceeds.
"""
import base64
import os
import re
import sys
from html import unescape

STATE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state")
DUMP_PATH = os.path.join(STATE_DIR, "inbox-dump.md")
LABEL_NAME = "job-scout"
LOOKBACK = "newer_than:8d"
MAX_THREADS = 80


def _write(text):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(DUMP_PATH, "w", encoding="utf-8") as f:
        f.write(text)


def _bail(note):
    _write(f"# Inbox dump\n\n_{note}_\n")
    print(note)
    sys.exit(0)


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
    """Walk MIME parts; prefer text/plain, fall back to stripped text/html."""
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
    if plain:
        return "\n".join(plain).strip()
    return "\n".join(html).strip()


def main():
    cid = os.environ.get("GMAIL_CLIENT_ID")
    csecret = os.environ.get("GMAIL_CLIENT_SECRET")
    rtoken = os.environ.get("GMAIL_REFRESH_TOKEN")
    if not (cid and csecret and rtoken):
        _bail("Gmail secrets not set — skipping email ingest, web sources only.")

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        _bail("google api libs missing — run pip install -r scripts/requirements.txt.")

    creds = Credentials(
        token=None,
        refresh_token=rtoken,
        client_id=cid,
        client_secret=csecret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
        ],
    )
    svc = build("gmail", "v1", credentials=creds)

    # Resolve the label name -> id.
    labels = svc.users().labels().list(userId="me").execute().get("labels", [])
    label_id = next((l["id"] for l in labels if l["name"].lower() == LABEL_NAME), None)
    if not label_id:
        _bail(f"Gmail label '{LABEL_NAME}' not found — create it and route alerts into it.")

    # List threads under the label within the lookback window.
    resp = svc.users().threads().list(
        userId="me", labelIds=[label_id], q=LOOKBACK, maxResults=MAX_THREADS
    ).execute()
    threads = resp.get("threads", [])

    chunks = [f"# Inbox dump — {len(threads)} thread(s), label '{LABEL_NAME}', {LOOKBACK}\n"]
    for t in threads:
        full = svc.users().threads().get(userId="me", id=t["id"], format="full").execute()
        for msg in full.get("messages", []):
            headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
            subject = headers.get("subject", "(no subject)")
            sender = headers.get("from", "(unknown)")
            date = headers.get("date", "")
            body = _extract_body(msg["payload"])
            if not body:
                continue
            chunks.append(
                f"\n\n---\n## {subject}\n**From:** {sender}  \n**Date:** {date}\n\n{body}\n"
            )

    _write("\n".join(chunks))
    print(f"Wrote {DUMP_PATH} from {len(threads)} thread(s).")


if __name__ == "__main__":
    main()
