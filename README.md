# Job Scout 2026

An automated agent that finds senior/staff/lead/principal **product design** roles (AU + AU-timezone remote) while Daniel is in Europe, scores them against his taste, researches contacts, and accumulates everything into `jobs-log.md` with a fortnightly digest emailed to his own Gmail inbox.

**Execution: Option D** — GitHub Actions runs Claude Code headless once a week. No machine of Daniel's involved. Setup in `SETUP-github-actions.md`.

## Files
| File | Role |
|---|---|
| `scan-prompt.md` | The agent's instructions, run each week. |
| `job-criteria.md` | Scoring rubric, hard filters, and calibration set (the taste model). |
| `about-me.md` | Daniel's profile, history, availability, likes/dislikes. |
| `target-companies.md` | 20 companies whose careers pages are checked directly. |
| `jobs-log.md` | Running master output — the "welcome back" report. |
| `email-alerts-setup.md` | One-time guide to wire up job-alert emails + the `job-scout` Gmail label. |
| `SETUP-github-actions.md` | One-time guide to deploy the agent (repo, API key, Gmail OAuth, secrets). |
| `.github/workflows/job-scout.yml` | Weekly schedule + the run steps. |
| `scripts/fetch_alerts.py` | Pulls `job-scout` emails into `state/inbox-dump.md`. |
| `scripts/send_digest.py` | Run counter + emails the digest to your own Gmail inbox every second run. |
| `scripts/get_gmail_token.py` | One-time local helper to mint the Gmail refresh token. |
| `state/run-state.json` | Run counter + last-digest bookkeeping. |

## Each weekly run
1. `fetch_alerts.py` reads job-alert emails (last 8 days) from the `job-scout` Gmail label.
2. Claude Code follows `scan-prompt.md`: ingest emails + job boards + target-company pages, score against `job-criteria.md`, enrich keepers with company/contact research, append to `jobs-log.md`, write the digest body.
3. `send_digest.py` emails the digest to your own Gmail inbox every second run.
4. The workflow commits the updated `jobs-log.md` + state back to the repo.

Pipeline: `SOURCES → INGEST → FILTER → ENRICH → OUTPUT`. ToS-safe (reads alert emails + plain web search; no LinkedIn scraping). Never auto-applies or sends outreach — it produces a curated list and a digest only.
