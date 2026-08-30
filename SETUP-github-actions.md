# Job Scout — Setup Guide (Option D: GitHub Actions + Claude Code)

This gets the agent running hands-off: a private GitHub repo holds these files, and a weekly workflow runs Claude Code in the cloud — it reads your `job-scout` Gmail alerts, scores and enriches roles, commits them to `jobs-log.md`, and emails you a digest (to your own Gmail inbox) every second run. No machine of yours involved. Cost = Anthropic API tokens (a few dollars a fortnight).

Work top to bottom. Total time ~20–30 min.

---

## Part 1 — Put the files in a private GitHub repo

1. Create a GitHub account if you don't have one (github.com).
2. New repo → name it `job-scout-2026` → **Private** → Create.
3. Upload this whole folder's contents (drag-and-drop in the GitHub web UI, or `git push`). Make sure these come across:
   ```
   .github/workflows/job-scout.yml
   scripts/  (requirements.txt, fetch_alerts.py, send_digest.py)
   state/    (run-state.json)
   job-criteria.md  about-me.md  target-companies.md  scan-prompt.md  jobs-log.md
   daniel-spagnolo_cv-2026.pdf  (optional in repo; about-me.md already holds the facts)
   .gitignore
   ```
   The `.gitignore` keeps secrets out — never commit your app password or any token.

---

## Part 2 — Anthropic API key (the agent's brain)

1. Go to console.anthropic.com → sign in → **Billing** → add a payment method and a small credit (e.g. $20 lasts a long time at this volume).
2. **API keys** → Create key → copy it (starts `sk-ant-...`). You won't see it again.
3. Add it as a repo secret (Part 5) named `ANTHROPIC_API_KEY`.

---

## Part 3 — Gmail access via an App Password (the easy way)

This lets the agent read your `job-scout` label (IMAP) and email the digest to your own Gmail inbox (SMTP). An **App Password** replaces the old OAuth flow — no Google Cloud project, no consent screen, no publishing/verification, and **the credential never expires on a timer**. You do it once.

1. **Create the Gmail label + filter** (in Gmail): follow `email-alerts-setup.md` Step 1 — make a label called exactly `job-scout` and a filter routing your job-alert senders into it.
2. **Turn on 2-Step Verification** (required before App Passwords exist): myaccount.google.com → **Security → 2-Step Verification** → follow the steps.
3. **Create the App Password**: go to **myaccount.google.com/apppasswords** (or Security → 2-Step Verification → App passwords). Give it a name like `job-scout` → **Create**. Google shows a **16-character password** (four groups of four). Copy it. You can paste it with or without spaces — the scripts handle both.
4. **Confirm IMAP is on**: Gmail → ⚙ **See all settings → Forwarding and POP/IMAP → Enable IMAP → Save**. (Newer accounts have it on already.)

Keep two values handy for Part 5:
```
GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=the 16-character app password
```

> Note: the digest is **emailed from this Gmail account to itself**, so it lands in your own inbox (with a notification) — it is never sent to anyone else. You can also read the committed `state/digest-latest.md` in the repo.

---

## Part 4 — (Already done) the email alerts themselves
Set up your saved-search alerts on each platform per `email-alerts-setup.md` Steps 2–3, so real alert emails start landing in the `job-scout` label before you fly.

---

## Part 5 — Add the three repo secrets

GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**. Add:

| Secret name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | from Part 2 |
| `GMAIL_ADDRESS` | your Gmail address (from Part 3) |
| `GMAIL_APP_PASSWORD` | the 16-character app password (from Part 3) |

(No recipient secret needed — the digest is emailed to your own Gmail inbox.)

---

## Part 6 — Test it

1. Repo → **Actions** tab → enable workflows if prompted.
2. Left list → **Job Scout (weekly)** → **Run workflow** (this is the `workflow_dispatch` manual trigger) → Run.
3. Watch the run. On success it commits an updated `jobs-log.md` and bumps `state/run-state.json`. Open `jobs-log.md` in the repo to review quality.
4. Tune: if scoring feels off, edit `job-criteria.md` / `about-me.md` and run again. The digest email is only sent on every second run — to test it immediately, run the workflow twice and check your Gmail inbox.

---

## How it runs after setup
- **Schedule:** every Monday ~7–8am Melbourne (`cron: 0 21 * * 0`, UTC). Change the cron in `.github/workflows/job-scout.yml` to adjust.
- **Each run:** fetch `job-scout` emails (last 8 days) → score + enrich against your criteria → append to `jobs-log.md` → write `state/digest-latest.md` → email the digest to your inbox every 2nd run → commit everything back to the repo.
- **Safety net:** because alerts pile up in Gmail regardless, no data is lost if a run fails. A single catch-up run on return processes the backlog.
- **Cost control:** the workflow uses `claude-sonnet-4-6`. Swap the `--model` flag if you want cheaper/stronger. Each run is one short Claude session + web research — typically a few cents to a couple of dollars.

## Troubleshooting
- **Run fails at "Fetch emails":** the script degrades to a web-only scan on any Gmail error (it writes the reason into `state/inbox-dump.md` and continues), so it should no longer fail the whole run. If email is being skipped, check the `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD` secrets, that IMAP is enabled in Gmail settings, and that the `job-scout` label exists.
- **`AUTHENTICATIONFAILED` / login errors:** the app password is wrong or 2-Step Verification was turned off (which invalidates app passwords). Regenerate at myaccount.google.com/apppasswords and update the `GMAIL_APP_PASSWORD` secret.
- **No digest arrived:** the digest emails every *second* run; confirm `state/run-state.json`. Check your inbox (and Spam).
- **Empty results:** likely no alert emails in the label yet and target pages had nothing matching — check the Run history line in `jobs-log.md`.
