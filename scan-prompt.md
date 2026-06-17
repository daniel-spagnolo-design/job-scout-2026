# Job Scout — Weekly Scan Prompt (headless / GitHub Actions)

This is the self-contained instruction set the GitHub Actions workflow runs each week via Claude Code. Assume no memory of prior conversations — everything needed is in this repo. Read the context files, run the pipeline, edit files, then stop.

## ⚠️ Token budget — READ FIRST (Tier-1 rate limit: 30k input tokens/minute)
This account is on the entry API tier. If the working context grows past ~30k tokens the run is rejected, so be economical the whole way through:
- **Prefer `WebSearch` over `WebFetch`.** Search returns short snippets; full-page fetches are huge and blow the budget. Only `WebFetch` a specific page when a role looks like a likely keeper and you need its detail.
- **Hard cap: at most ~6 `WebFetch` calls for the entire run.** If you're near the cap, stop fetching and work with search snippets.
- **Only check the target companies listed in `state/targets-this-run.md`** (a small rotating slice), NOT all of `target-companies.md`.
- **Don't read the CV PDF** (`about-me.md` has everything) and **don't re-read the whole `jobs-log.md`** — dedupe via the small `state/seen.md` index instead.
- Work role-by-role; don't accumulate many large pages in context at once.

## Context files (read first, every run)
- `job-criteria.md` — scoring rubric, hard filters, and Daniel's calibration set. Source of truth for what's a fit.
- `about-me.md` — Daniel's profile, history, availability date, and what he loves/avoids. Use instead of the CV PDF.
- `state/targets-this-run.md` — the small rotating set of target companies to check this run (written by the fetch script). Use this, not the full list.
- `state/inbox-dump.md` — job-alert emails pulled from Gmail this run (size-capped). May be empty if Gmail isn't set up — that's fine, continue with web sources.
- `state/seen.md` — lightweight dedup index of roles already logged (one line each). Read this to avoid duplicates instead of re-reading `jobs-log.md`.

## Who this is for (quick profile)
Daniel Spagnolo — Senior Product Designer, Melbourne; open to Staff/Lead/Principal IC. Background: AI products (Culture Amp), mental health (Unmind), digital health (Babylon/NHS), biometric identity (Onfido), AU gov/retail data (Informed Decisions). Available ~9 Sep 2026. Full detail in `about-me.md`.

---

## Pipeline (run in order)

### 1. Ingest
**a. Email alerts.** Read `state/inbox-dump.md`. It contains (size-capped) bodies of job-alert emails from the past ~8 days. Each email bundles many roles — extract each listing: title, company, location, contract/perm, rate/salary if shown, posted date, source platform, apply/source URL. This is your primary, cheapest source — lean on it.

**b. Direct web sources** (economical — respect the token budget above):
- **Target companies:** only the ones in `state/targets-this-run.md`. For each, do ONE `WebSearch` like `"<company> product designer careers"`; only `WebFetch` a careers/role page if a senior/staff/lead/principal product design role looks present and promising.
- Optionally one or two `WebSearch` queries for AU job boards (e.g. `site:uiuxjobsboard.com senior product designer Australia`, `senior product designer contract Australia`). Fetch a specific listing only if it looks like a keeper. Skip if you're near the fetch cap.

Dedupe against `state/seen.md` (same company + title = already logged; skip).

### 2. Filter & score
Apply `job-criteria.md` exactly:
- **Hard filters first** — reject outright if any trip (crypto/web3, gambling, tobacco/alcohol, surveillance/defence; below senior; not Melbourne-commutable AND not AU-timezone remote; onsite >3 days/wk; rate explicitly <$900/day; perm salary explicitly <$140k). Missing rate/salary is NOT a reject — keep, flag "rate unknown".
- Score survivors 0–100 using the signal tables. Apply the −10 perm handicap. Apply the +10 honest-ad bonus where earned. Do NOT penalise honest craft-led roles for de-emphasising research (see judgment notes + calibration).
- Tiers: 🔥 75+, ⏳ 50–74, discard <50. A 🔥 role must have discovery/0→1/AI-native OR exceptional honest craft-led framing in a strong-fit domain.
- Flag "starts before availability" for roles needing a start before ~9 Sep 2026 (do not reject).
- When unsure between tiers, pick the lower and say why in one line.

### 3. Enrich (🔥 and ⏳ keepers only — cap the work)
- Enrich at most the **top 3 keepers** this run; for the rest, log the basics and note "enrich next run".
- Per keeper, at most **2 `WebSearch` queries** (count toward the fetch budget); avoid full-page fetches if a snippet already answers it.
- Capture: what the company does, rough size, design-team maturity; named design leadership / likely hiring manager with public LinkedIn URLs where findable; recruiter + agency if agency-posted; a one-paragraph "why it fits" tied to Daniel's background; a suggested outreach angle.
- **Never fabricate** names, emails, or URLs — write "no named contact found" if unknown.

### 4. Output — edit `jobs-log.md` and `state/seen.md`
- **Append** new keepers under the correct section of `jobs-log.md` in the existing format. Never rewrite or reorder existing entries.
- For every new role logged, append one line to `state/seen.md`: `Company — Title — posted-date — tier`.
- Move newly-expired 🔥/⏳ roles into "Expired but relevant — outreach targets".
- Update the master contact list table with any new names; add notable patterns to "Companies hiring repeatedly" and one line to "Market notes".
- Add a dated line at the top of "Run history": `YYYY-MM-DD · alerts read: N · new 🔥: N · new ⏳: N · notes`. (The run counter in `state/run-state.json` is managed by the scripts — don't edit it.)

### 5. Digest body — write `state/digest-latest.md`
Overwrite `state/digest-latest.md` with a short, phone-readable digest of THIS run's new 🔥 roles (title, company, one-line why, link), then a one-line count of new ⏳, then any market note. `scripts/send_digest.py` decides whether to email it to Daniel's own inbox (every second run) — you just write the file.

### 6. Close out
Note in the run-history line anything that broke (board unreachable, empty inbox, hit the fetch cap, etc.).

---

## Guardrails
- Respect the token budget at the top — it's the difference between the run succeeding or failing.
- ToS-safe only: read the email dump and do plain WebSearch/WebFetch. Never scrape LinkedIn directly or attempt logins. (LinkedIn alert *emails* in the dump are fine to read.)
- Never auto-send applications or outreach. A script separately emails the digest from Daniel's Gmail to his own inbox — nothing goes to anyone else, and no applications/outreach are ever sent.
- Don't invent companies, roles, people, or links. Missing data is flagged, not filled.
- If `state/inbox-dump.md` is empty/absent, run the web portion only and note the gap.
- Edit only `jobs-log.md`, `state/seen.md`, and `state/digest-latest.md`. Do not modify criteria, profile, or scripts.
