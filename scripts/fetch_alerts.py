#!/usr/bin/env python3
"""
Runs in GitHub Actions before the scan. Two jobs:

1. Writes state/targets-this-run.md — a small ROTATING slice of the target companies
   (a few per run) so the scan doesn't fetch all 20 careers pages every week. This is
   the main lever for staying under the Tier-1 30k-input-tokens/minute rate limit.
2. Pulls job-alert emails from the past ~8 days carrying the `job-scout` Gmail label and
   writes them (size-capped) to state/inbox-dump.md.

Auth is a Gmail App Password (IMAP), via two repo secrets:
  GMAIL_ADDRESS, GMAIL_APP_PASSWORD
App Passwords need 2-Step Verification on the Google account and never expire on a
timer — unlike OAuth "Testing"-mode refresh tokens, which was the old approach.
If the secrets are missing OR the IMAP fetch fails, the email step degrades to a note
in inbox-dump.md and exits 0, so the web-only scan still runs.
"""
import email
import imaplib
import json
import os
import re
import sys
from datetime import datetime, timedelta
from email.header import decode_header, make_header
from html import unescape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(ROOT, "state")
DUMP_PATH = os.path.join(STATE_DIR, "inbox-dump.md")
TARGETS_PATH = os.path.join(STATE_DIR, "targets-this-run.md")
STATE_PATH = os.path.join(STATE_DIR, "run-state.json")
TARGET_LIST = os.path.join(ROOT, "target-companies.md")

LABEL_NAME = "job-scout"
IMAP_HOST = "imap.gmail.com"
LOOKBACK_DAYS = 8
MAX_MSGS = 60

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


# ---------- email ingest (IMAP) ----------

def _strip_html(html):
    html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</p>", "\n", html)
    html = re.sub(r"<[^>]+>", " ", html)
    text = unescape(html)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


def _decode_header(value):
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _extract_body(msg):
    """Pull a text body out of an email.message.Message: prefer text/plain, else stripped HTML."""
    plain, html = [], []

    def read(part):
        try:
            payload = part.get_payload(decode=True)
        except Exception:
            return ""
        if payload is None:
            return ""
        charset = part.get_content_charset() or "utf-8"
        try:
            return payload.decode(charset, "replace")
        except (LookupError, TypeError):
            return payload.decode("utf-8", "replace")

    for part in msg.walk():
        if part.is_multipart():
            continue
        disp = str(part.get("Content-Disposition") or "").lower()
        if "attachment" in disp:
            continue
        ctype = part.get_content_type()
        if ctype == "text/plain":
            plain.append(read(part))
        elif ctype == "text/html":
            html.append(_strip_html(read(part)))

    body = ("\n".join(plain) if plain else "\n".join(html)).strip()
    if len(body) > MAX_MSG_CHARS:
        body = body[:MAX_MSG_CHARS] + "\n…[truncated]"
    return body


def ingest_email():
    addr = os.environ.get("GMAIL_ADDRESS")
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    if not (addr and pw):
        _write(DUMP_PATH, "# Inbox dump\n\n_Gmail secrets not set — web sources only._\n")
        print("Gmail secrets not set — skipping email ingest.")
        return

    # Any IMAP/auth failure must degrade to a web-only scan, never crash the workflow.
    imap = None
    try:
        imap = imaplib.IMAP4_SSL(IMAP_HOST, 993)
        imap.login(addr, pw)

        # Gmail exposes each label as a selectable mailbox of the same name.
        status, _ = imap.select(f'"{LABEL_NAME}"', readonly=True)
        if status != "OK":
            _write(DUMP_PATH, f"# Inbox dump\n\n_Label '{LABEL_NAME}' not found._\n")
            print(f"Label '{LABEL_NAME}' not found.")
            return

        since = (datetime.utcnow() - timedelta(days=LOOKBACK_DAYS)).strftime("%d-%b-%Y")
        status, data = imap.search(None, "SINCE", since)
        ids = data[0].split() if (status == "OK" and data and data[0]) else []
        ids = ids[-MAX_MSGS:]  # newest N

        chunks = [
            f"# Inbox dump — {len(ids)} message(s), label '{LABEL_NAME}', "
            f"newer_than:{LOOKBACK_DAYS}d\n"
        ]
        total = len(chunks[0])
        for num in reversed(ids):  # newest first
            status, msgdata = imap.fetch(num, "(RFC822)")
            if status != "OK" or not msgdata or not msgdata[0]:
                continue
            msg = email.message_from_bytes(msgdata[0][1])
            body = _extract_body(msg)
            if not body:
                continue
            block = (
                f"\n\n---\n## {_decode_header(msg.get('Subject')) or '(no subject)'}\n"
                f"**From:** {_decode_header(msg.get('From')) or '?'} · "
                f"**Date:** {msg.get('Date', '')}\n\n{body}\n"
            )
            if total + len(block) > MAX_DUMP_CHARS:
                chunks.append("\n\n_[dump truncated to stay within token budget]_\n")
                break
            chunks.append(block)
            total += len(block)

        _write(DUMP_PATH, "".join(chunks))
        print(f"Wrote {DUMP_PATH} from {len(ids)} message(s).")
    except Exception as e:  # noqa: BLE001 — any Gmail failure degrades to web-only
        _write(
            DUMP_PATH,
            "# Inbox dump\n\n_Gmail fetch failed — continuing with web sources only._\n\n"
            f"_Error: {type(e).__name__}: {e}_\n\n"
            "_Check the GMAIL_ADDRESS / GMAIL_APP_PASSWORD secrets and that IMAP is "
            "enabled in Gmail settings — see SETUP-github-actions.md troubleshooting._\n",
        )
        print(f"Gmail fetch failed ({type(e).__name__}: {e}) — web-only scan.")
    finally:
        if imap is not None:
            try:
                imap.logout()
            except Exception:
                pass


def main():
    write_target_rotation()  # always runs, even without Gmail
    ingest_email()
    sys.exit(0)


if __name__ == "__main__":
    main()
