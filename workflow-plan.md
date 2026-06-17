# Job Scout 2026 — Agentic Workflow Plan

**Goal:** While Daniel is in Europe (~2.5 months), an automated workflow monitors AU + AU-timezone-remote senior/staff/principal product design roles (contract and full-time), filters them against his profile, identifies people to contact at each company, and accumulates everything into a running markdown file — plus a fortnightly digest. On return: a single "welcome back" document of live jobs, expired-but-relevant jobs, and named contacts for warm outreach.

---

## 1. How it works (pipeline)

```
SOURCES → INGEST → FILTER → ENRICH → OUTPUT
```

**Sources (set up before departure)**
Email alerts from job platforms land in your inbox. This is the key trick: instead of scraping LinkedIn (blocked, against ToS, brittle), you create saved-search **email alerts** on each platform before you leave. The agent reads those alert emails via the Gmail connector — completely reliable and ToS-safe. Note LinkedIn alert emails arrive 18–72h after a job goes live; fine for this use case.

**Ingest (each run)**
1. Read new job-alert emails from a dedicated Gmail label/filter (e.g. `job-scout`).
2. Directly check 2–3 boards that work via plain web fetch/search (Seek listings, uiuxjobsboard, startup.jobs).

**Filter**
Score each role against `job-criteria.md` (see section 4): seniority, contract vs perm, AU timezone, domain fit, values fit, red flags. Discard noise; keep a "maybe" tier rather than hard-cutting borderline roles.

**Enrich (the part that makes this worth it)**
For each keeper, web-research the company:
- What they do, size, funding/stability, design team maturity
- Named people: Head of Design / Design Director / Principal Designers / hiring manager if listed, plus their public LinkedIn URLs
- Recruiter name if posted via agency
- Why this role matches (or doesn't quite) your criteria — one paragraph

**Output**
- Append to `jobs-log.md` (running master file, structured per section 6)
- Every second run: draft a short digest email to daniel_spagnolo@yahoo.com.au (the connector creates drafts — pre-departure we test whether send works or whether you read drafts/the MD from your phone)

---

## 2. Platforms & sources

### Set up email alerts on (pre-departure):
| Platform                      | Why                                             | Alert setup                                                                                                                                                       |
| ----------------------------- | ----------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **LinkedIn**                  | Largest volume, best for perm + contract        | 3–4 saved searches: "Senior Product Designer", "Staff/Principal Product Designer", "Product Design contract", filtered to Australia + Remote. Daily email alerts. |
| **Seek**                      | #1 AU board; strong contract/temp filter        | Saved searches with Contract/Temp + Full-time variants                                                                                                            |
| **Indeed AU**                 | Aggregates company career pages                 | 1–2 broad alerts                                                                                                                                                  |
| **Glassdoor AU**              | Overlap, but catches some uniques + salary data | 1 alert                                                                                                                                                           |
| **uiuxjobsboard.com**         | Design-specific, AU filter                      | Alert or direct fetch each run                                                                                                                                    |
| **startup.jobs / Wellfound**  | Startup roles, often remote AU-friendly         | Alert                                                                                                                                                             |
| **The Loop (theloop.com.au)** | AU creative-industry board, 125k+ profiles      | Alert + keep portfolio profile current                                                                                                                            |

### Recruiters/agencies (register + set alerts before leaving):
- **Aquent AU** — design/creative contract specialist, Sydney/Melbourne
- **Brightbox Consulting** — specialist AU design recruiter
- **Creative Recruiters** — digital/UX/UI/product
- **SustainRecruit** — AU product + UX, perm and contract
- **TheDriveGroup** — product & UX/UI
- Generalists worth a registration: Hays, Robert Half, Talent International

Tell 2–3 of these recruiters *before you leave* that you're back and available from [date]. Recruiters with a known return date will pipeline you — this beats any automation.

### Not worth automating:
- Direct LinkedIn scraping (blocked, ToS violation, brittle)
- Slack communities (Design Buddies, AU design Slacks) — valuable but human-only; rejoin on return

---

## 3. Finding contacts — honest scope

What the agent **can** reliably produce per company:
- Names + titles of design leadership and likely hiring managers (from company team pages, LinkedIn public search results, press, conference bios)
- Public LinkedIn profile URLs
- Recruiter name + agency if the role was agency-posted
- Suggested outreach angle ("posted about design systems at X conference", "ex-[company you worked at]")

What it **can't** do without paid tools (Apollo, Hunter — skippable for now):
- Verified email addresses
- LinkedIn connection requests / InMail on your behalf (and you wouldn't want an agent doing this anyway)

The return deliverable is a **warm-outreach list**, not auto-sent messages. For expired jobs this is exactly what you want: "this role closed in July, here's the Head of Design — message them about what's next."

---

## 4. Profile artefacts to gather (your homework before we build)

The filter is only as good as the profile. Gather these into `about-me/` and `projects/job-scout-2026/`:

1. **about-me.md** (currently empty) — who you are, what you love/hate working on. Even 20 dot points beats nothing.
2. **CV/resume** (PDF or docx) — I'll extract domains, seniority signals, past companies.
3. **LinkedIn profile export** — Settings → Get a copy of your data, or just save profile as PDF.
4. **Portfolio link** + 2–3 case studies you're proudest of.
5. **Job-criteria inputs** (I'll turn these into `job-criteria.md`, the scoring rubric):
   - Day-rate floor for contract; salary floor for perm
   - Contract length sweet spot (3mo? 6mo? 12mo?)
   - Domains you want more of / never again
   - Company types: startup vs scale-up vs enterprise vs agency vs gov
   - Values deal-breakers (e.g. no gambling, no surveillance, design-mature orgs only?)
   - Remote/hybrid/onsite tolerance and which cities
   - Earliest start date (your return + buffer)
6. **Calibration set (high value, low effort):** links/screenshots of 3–5 job ads you'd *definitely* apply to and 3–5 you'd never touch, with one line why. This trains the filter better than any abstract values list.
7. **Target company list** — 10–20 companies you'd love to work with even if nothing's posted. The agent monitors their career pages too.

(Your `branding-questions.md` values/personality prompts are a good starting scaffold for #1 and #5.)

---

## 5. Execution options (decide later)

| Option | How | Trade-offs |
|---|---|---|
| **A. Mac stays on at home** | Cowork scheduled task, runs every 3–4 days; fortnightly digest | Full automation. Requires Mac on + Cowork running + sleep disabled for 2.5 months. Power/updates risk. |
| **B. Phone check-in** | No always-on machine. Every 1–2 weeks you open Claude on your phone and say "run my job scan" | Zero infrastructure. Depends on you remembering; mobile session may differ from Cowork setup. |
| **C. Hybrid** | Scheduled task on Mac + email alerts accumulate in Gmail regardless. If the Mac dies, nothing is lost — alerts keep stacking, and a single catch-up run on return processes the whole backlog | The email-alert backlog is the safety net: worst case, you come home and we process 2.5 months of alerts in one session. |
| **D. GitHub Actions + Claude Code (recommended if coding)** | Private repo holds criteria file, jobs-log.md, prompt. Scheduled workflow (every ~3 days) runs Claude Code headless: fetches alert emails via Gmail API (OAuth token as repo secret), filters/enriches, commits to jobs-log.md, sends fortnightly digest via email API (e.g. Resend) | No machine of yours involved, free runners, full run history in git. Cost = API tokens only (a few $/fortnight). Requires API billing + initial OAuth/secrets setup. |
| **E. VPS + cron + headless Claude Code** | $5–10/mo box (Hetzner/DigitalOcean) running `claude -p "run job scan"` on cron | Can auth with your existing Claude subscription instead of API billing. More control, but a remote box to babysit (updates, failures) while travelling. |
| **F. Claude Agent SDK on serverless** | Custom Python/TS agent deployed as a scheduled job (Cloud Run Jobs, Lambda + EventBridge, Fly.io) | Most robust, most engineering effort. Overkill for 2.5 months — unless you want it as a portfolio piece. |
| **G. Deterministic script + Claude API for judgment only** | Plain code (cron anywhere) fetches/parses alert emails; API called only for scoring + enrichment steps | Cheapest tokens, most predictable, fewest surprises when nobody's watching. Least flexible when emails change format. |

If coding: **D** is the sweet spot — serverless, version-controlled, and the email-alert safety net still applies if a run fails. **G** if you value reliability over flexibility.

Key insight: **because ingestion is email-based, no data is ever lost.** Automation frequency only affects how *fresh* the digest is, not what you ultimately capture.

---

## 6. Output spec — `jobs-log.md` (what you read when you're back)

```
# Job Scout — Welcome Back Report

## 🔥 Live & strong fit (apply now)
### [Role] — [Company] — [Contract/Perm] — [Posted date]
- Why it fits: ...
- Rate/salary signal: ...
- Contacts: [Name, Title, LinkedIn URL] / recruiter
- Link: ...

## ⏳ Live & maybe
(same format, lower score)

## 💀 Expired but relevant — outreach targets
### [Role] — [Company] — closed [date]
- Why it was a fit
- Who to contact + suggested angle

## 🏢 Companies hiring repeatedly (warm signal even with no open role)
- Company — pattern observed — contact

## 📇 Master contact list
| Name | Title | Company | Source role | Angle |

## 📊 Market notes
- Rate trends, demand patterns, which domains are hiring designers
```

---

## 7. Pre-departure checklist

- [ ] Fill `about-me.md` + gather artefacts (section 4)
- [ ] I build `job-criteria.md` scoring rubric from your inputs; you approve
- [ ] Create Gmail filter/label `job-scout` for all alert emails
- [ ] Set up saved-search alerts on each platform (section 2) — ~1 hour, I can guide step-by-step
- [ ] Register with 2–3 recruiters; tell them your return date
- [ ] Test run: I process one week of alerts end-to-end, you review the output quality and we tune the filter
- [ ] Decide execution option (section 5) and, if A/C, set up the scheduled task + Mac sleep settings
- [ ] Dry-run the fortnightly digest

---

## Open questions

1. Should the agent also watch your **target companies'** career pages directly? (Recommended — catches roles before they hit boards.)
2. Digest delivery: email draft vs. you reading `jobs-log.md` from your phone — test which works before departure.
3. Do you want expired-role contacts limited to strong-fit roles only, to keep the outreach list tight?
