#!/usr/bin/env python3
"""
Runs in GitHub Actions after the scan. Owns the run counter and the digest cadence.

- Increments state/run-state.json total_runs every run.
- On every SECOND run (roughly fortnightly given weekly scans), emails the digest
  (state/digest-latest.md) to the Gmail account itself (Daniel -> Daniel), so it lands
  in his inbox with a notification. The digest is also committed as a file in the repo.

Missing Gmail secrets or no digest file -> still bumps the counter, skips the send,
exits 0 (so the workflow's commit step records the counter increment).
"""
import base64
import json
import os
import sys
from email.mime.text import MIMEText

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(ROOT, "state")
STATE_PATH = os.path.join(STATE_DIR, "run-state.json")
DIGEST_PATH = os.path.join(STATE_DIR, "digest-latest.md")
DIGEST_EVERY = 2  # email on every Nth run

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",  # email the digest to yourself
]


def load_state():
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"total_runs": 0, "last_digest_run": 0}


def save_state(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def send_email(subject, body):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=os.environ["GMAIL_REFRESH_TOKEN"],
        client_id=os.environ["GMAIL_CLIENT_ID"],
        client_secret=os.environ["GMAIL_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    svc = build("gmail", "v1", credentials=creds)
    own_email = svc.users().getProfile(userId="me").execute().get("emailAddress", "me")

    msg = MIMEText(body)
    msg["to"] = own_email  # send to yourself; lands in your inbox
    msg["from"] = own_email
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    svc.users().messages().send(userId="me", body={"raw": raw}).execute()
    return own_email


def main():
    state = load_state()
    state["total_runs"] += 1
    run_no = state["total_runs"]

    due = (run_no - state.get("last_digest_run", 0)) >= DIGEST_EVERY
    have_secrets = all(
        os.environ.get(k)
        for k in ("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN")
    )

    if not due:
        print(f"Run {run_no}: digest not due (every {DIGEST_EVERY} runs). Counter saved.")
        save_state(state)
        return

    if not have_secrets:
        print(f"Run {run_no}: digest due but Gmail secrets missing — skipping send.")
        save_state(state)
        return

    if not os.path.exists(DIGEST_PATH):
        print(f"Run {run_no}: digest due but {DIGEST_PATH} missing — skipping send.")
        save_state(state)
        return

    with open(DIGEST_PATH, encoding="utf-8") as f:
        body = f.read().strip() or "No new strong-fit roles this fortnight."

    fire_count = body.count("🔥")
    subject = f"Job Scout digest — {fire_count} new strong fit(s)"

    try:
        where = send_email(subject, body)
        state["last_digest_run"] = run_no
        print(f"Run {run_no}: digest emailed to {where} (your own inbox).")
    except Exception as e:  # don't fail the whole workflow over a send error
        print(f"Run {run_no}: digest send failed: {e}", file=sys.stderr)

    save_state(state)


if __name__ == "__main__":
    main()
