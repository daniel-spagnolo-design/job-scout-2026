# Job Scout — Weekly Scan Prompt (headless / GitHub Actions)

This is the self-contained instruction set the GitHub Actions workflow runs each week via Claude Code. Assume no memory of prior conversations — everything needed is in this repo. Read the context files, run the pipeline, edit files, then stop.

## Context files (read first, every run)
- `job-criteria.md` — scoring rubric, hard filters, and Daniel's calibration set. Source of truth for what's a fit.
- `about-me.md` — Daniel's profile, history, availability date, and what he loves/avoids. Use instead of parsing the CV PDF.
- `target-companies.md` — 20 companies whose careers pages to check directly.
- `jobs-log.md` — running master output. Read it so you don't duplicate roles already logged. Append new results here.
- `state/inbox-dump.md` — job-alert emails pulled from Gmail this run (produced by `scripts/fetch_alerts.py` before you run). May be empty or absent if the Gmail connection isn't set up yet — that's fine, continue with web sources.

## Who this is for (quick profile)
Daniel Spagnolo — Senior Product Designer, Melbourne; open to Staff/Lead/Principal IC. Background: AI products (Culture Amp), mental health (Unmind), digital health (Babylon/NHS), biometric identity (Onfido), AU gov/retail data (Informed Decisions). Available ~9 Sep 2026. Full detail in `about-me.md`.

---

## Pipeline (run in order)

### 1. Ingest
**a. Email alerts.** Read `state/inbox-dump.md`. It contains the bodies of job-alert emails from the past ~8 days. Each email bundles many roles — extract each listing: title, company, location, contract/perm, rate/salary if shown, posted date, source platform, apply/source URL.

**b. Direct web sources** (use WebSearch / WebFetch):
- Job boards: uiuxjobsboard.com (AU/remote), startup.jobs, wellfound.com, and Seek listings for senior/staff product designer roles in Australia / AU-timezone remote.
- **Target companies:** for each company in `target-companies.md`, check its careers page for senior/staff/lead/principal product design roles. Confirm the live careers URL via search if the listed one 404s.

Deduplicate against `jobs-log.md` (same company + title + similar posted date = already logged; skip).

### 2. Filter & score
Apply `job-criteria.md` exactly:
- **Hard filters first** — reject outright if any trip (crypto/web3, gambling, tobacco/alcohol, surveillance/defence; below senior; not Melbourne-commutable AND not AU-timezone remote; onsite >3 days/wk; rate explicitly <$900/day; perm salary explicitly <$140k). Missing rate/salary is NOT a reject — keep, flag "rate unknown".
- Score survivors 0–100 using the signal tables. Apply the −10 perm handicap. Apply the +10 honest-ad bonus where earned. Do NOT penalise honest craft-led roles for de-emphasising research (see judgment notes + calibration).
- Tiers: 🔥 75+, ⏳ 50–74, discard <50. A 🔥 role must have discovery/0→1/AI-native OR exceptional honest craft-led framing in a strong-fit domain.
- Flag "starts before availability" for roles needing a start before ~9 Sep 2026 (do not reject).
- When unsure between tiers, pick the lower and say why in one line.

### 3. Enrich (🔥 and ⏳ keepers only)
Light web research per keeper: what the company does, rough size, funding/stability, design-team maturity; named design leadership / likely hiring manager with public LinkedIn URLs where findable; recruiter + agency if agency-posted; a one-paragraph "why it fits" tied to Daniel's background; a suggested outreach angle (shared past employer, conference talk, design-systems work, etc.). **Never fabricate** names, emails, or URLs — write "no named contact found" if unknown.

### 4. Output — edit `jobs-log.md`
- **Append** new keepers under the correct section in the existing format. Never rewrite or reorder existing entries.
- Move newly-expired 🔥/⏳ roles into "Expired but relevant — outreach targets".
- Update the master contact list table with any new names.
- Add notable patterns to "Companies hiring repeatedly" and one line to "Market notes".
- Add a dated line at the top of "Run history": `YYYY-MM-DD · alerts read: N · new 🔥: N · new ⏳: N · notes`. Increment "Total runs".

### 5. Digest body — write `state/digest-latest.md`
Always overwrite `state/digest-latest.md` with a short, phone-readable digest of THIS run's new 🔥 roles (title, company, one-line why, link), then a one-line count of new ⏳, then any market note. `scripts/send_digest.py` decides whether to email it to Daniel's own inbox (every second run) — you just write the file.

### 6. Close out
Note in the run-history line anything that broke (board unreachable, empty inbox, etc.) so it can be fixed.

---

## Guardrails
- ToS-safe only: read the email dump and do plain WebSearch/WebFetch. Never scrape LinkedIn directly or attempt logins. (LinkedIn alert *emails* in the dump are fine to read.)
- Never auto-send applications or outreach. Deliverable = curated `jobs-log.md` + digest file. A script separately emails the digest from Daniel's Gmail to his own inbox — nothing goes to anyone else, and no applications/outreach are ever sent.
- Don't invent companies, roles, people, or links. Missing data is flagged, not filled.
- If `state/inbox-dump.md` is empty/absent, run the web portion only and note the gap.
- Edit only `jobs-log.md` and `state/digest-latest.md`. Do not modify criteria, profile, or scripts.
