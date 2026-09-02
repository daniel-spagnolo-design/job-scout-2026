#!/usr/bin/env python3
"""
Runs in GitHub Actions after the scan. Owns the run counter and the digest cadence.

- Increments state/run-state.json total_runs every run.
- On every SECOND run (roughly fortnightly given weekly scans), emails the digest
  (state/digest-latest.md) to the Gmail account itself (Daniel -> Daniel), so it lands
  in his inbox with a notification. The digest is also committed as a file in the repo.

Auth is a Gmail App Password (SMTP), via two repo secrets:
  GMAIL_ADDRESS, GMAIL_APP_PASSWORD

Missing Gmail secrets or no digest file -> still bumps the counter, skips the send,
exits 0 (so the workflow's commit step records the counter increment).
"""
import json
import os
import smtplib
import ssl
import sys
from email.mime.text import MIMEText

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(ROOT, "state")
STATE_PATH = os.path.join(STATE_DIR, "run-state.json")
DIGEST_PATH = os.path.join(STATE_DIR, "digest-latest.md")
DIGEST_EVERY = 2  # email on every Nth run

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


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
    # Same normalisation as fetch_alerts.py: Google's app-password display spaces
    # break the SMTP login, so strip all whitespace from the password and trim the
    # address.
    addr = os.environ["GMAIL_ADDRESS"].strip()
    pw = "".join(os.environ["GMAIL_APP_PASSWORD"].split())

    msg = MIMEText(body, _charset="utf-8")
    msg["To"] = addr  # send to yourself; lands in your inbox
    msg["From"] = addr
    msg["Subject"] = subject

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx) as s:
        s.login(addr, pw)
        s.sendmail(addr, [addr], msg.as_string())
    return addr


def main():
    state = load_state()
    state["total_runs"] += 1
    run_no = state["total_runs"]

    due = (run_no - state.get("last_digest_run", 0)) >= DIGEST_EVERY
    have_secrets = all(
        os.environ.get(k) for k in ("GMAIL_ADDRESS", "GMAIL_APP_PASSWORD")
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
