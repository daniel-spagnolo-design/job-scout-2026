#!/usr/bin/env python3
"""
ONE-TIME, RUN LOCALLY. Gets a Gmail refresh token for the agent.

Prereqs:
  1. In Google Cloud Console: create a project, enable the Gmail API, and create an
     OAuth client of type "Desktop app". Download its JSON as `credentials.json`
     into this `scripts/` folder. (Full steps in SETUP-github-actions.md.)
  2. pip install -r scripts/requirements.txt

Then:
  python scripts/get_gmail_token.py

A browser window opens; sign in with the Gmail account that has the `job-scout`
label and approve. The script prints three values — add them to GitHub as the
secrets GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN.

DO NOT commit credentials.json or the printed token to the repo.
"""
import json
import os
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

# readonly = read alert emails; send = email the digest to your own Gmail inbox.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

HERE = os.path.dirname(os.path.abspath(__file__))
CRED_PATH = os.path.join(HERE, "credentials.json")


def main():
    if not os.path.exists(CRED_PATH):
        sys.exit(
            f"Missing {CRED_PATH}\n"
            "Download your OAuth 'Desktop app' client JSON from Google Cloud Console "
            "and save it as scripts/credentials.json. See SETUP-github-actions.md."
        )

    flow = InstalledAppFlow.from_client_secrets_file(CRED_PATH, SCOPES)
    # access_type=offline + prompt=consent guarantees a refresh_token is returned.
    creds = flow.run_local_server(
        port=0, access_type="offline", prompt="consent"
    )

    if not creds.refresh_token:
        sys.exit(
            "No refresh token returned. Revoke prior access at "
            "https://myaccount.google.com/permissions and run again."
        )

    with open(CRED_PATH) as f:
        installed = json.load(f)["installed"]

    print("\n=== Add these three values as GitHub repo secrets ===\n")
    print(f"GMAIL_CLIENT_ID={installed['client_id']}")
    print(f"GMAIL_CLIENT_SECRET={installed['client_secret']}")
    print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")
    print("\n(Settings -> Secrets and variables -> Actions -> New repository secret)")
    print("Do NOT commit credentials.json or these values.\n")


if __name__ == "__main__":
    main()
