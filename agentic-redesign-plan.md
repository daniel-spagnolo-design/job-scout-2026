# Job Scout — Agentic Redesign Plan

How I'd rebuild this as a proper agentic workflow, based on six runs of real evidence.

**Status:** proposal only. The current system works and is finding roles. Nothing here is urgent — it's a staged path, ordered so you can stop after any phase and still be better off.

---

## 1. What the current design is, honestly

One `claude -p` call does everything: read the criteria, read the profile, read the email dump, search the web, fetch pages, score each role, research companies, write `jobs-log.md`, write `state/seen.md`, write the digest. A single agent, a single context, a single shot.

That's the right way to *start* — it proved the idea in a weekend. It's now hitting predictable limits.

### Evidence from runs 1–6

| Symptom | Seen in | Root cause |
|---|---|---|
| Artificial caps: 4 companies/run, ~6 fetches total | `scan-prompt.md` token-budget section | Everything shares one 30k-token context |
| "Scored from search snippets only" | Runs 2, 4, 5, 5b | `WebFetch` 403s (Lever, startup.jobs) and 404s (Bupa, Lyrebird); no fallback |
| "enrich next run" carried for months | Atlassian since run 2, Airwallex since run 1 | No work queue — deferrals live in prose, nothing re-queues them |
| Jun 2026 roles "likely expired" for 11+ weeks | Runs 3, 4, 6 market notes | Nothing verifies liveness; expiry is a suggestion the model may skip |
| Gmail silently broken ~10 weeks | Runs 3–5b | Failure absorbed into a prose note instead of raising an alarm |
| Manual reformat of 12 entries | This session | Markdown *is* the database; format is welded to content |
| One provisional 80/100 (Blinq) from snippets alone | Run 5 | Confidence isn't modelled — a guess and a read look identical |
| Whole run lost on credit failure | Run at 05:52, 2 Sep | No checkpointing; commit step skipped, all work discarded |

None of these are prompt bugs. They're all the same architectural fact: **one context doing deterministic work and judgment work at the same time, with markdown as the datastore.**

---

## 2. The organising principle

> Use code for everything that is decidable by code. Spend model tokens only on judgment. Use a *workflow* (fixed path) wherever the path is known, and an *agent* (model-directed tool loop) only where it genuinely isn't.

Applied here:

**Decidable by code** — parsing alert emails, deduping, date/expiry maths, target rotation, hard filters that are pure predicates (gambling, below-senior, onsite >3 days, rate <$900), rendering markdown, sending the digest, counting runs.

**Needs judgment** — "is this ad honest or a ticket factory?", "does this domain overlap Daniel's background?", why-it-fits prose, outreach angles, resolving an ambiguous title.

**Genuinely open-ended** — company/contact enrichment. This is the *only* stage that deserves a real agent loop, because the research path can't be known in advance.

Right now all three are mixed together. Separating them is the whole redesign.

---

## 3. Target architecture

```
                    ┌─ code ──────────────────────────────────┐
  Gmail IMAP ──────▶│ HARVEST    normalise → Posting records  │
  Job boards ──────▶│ DEDUPE     canonical key vs store       │
                    │ PREFILTER  pure-predicate hard filters  │
                    └────────────────────┬────────────────────┘
                                         │  survivors only
                    ┌─ Haiku, batched ───▼────────────────────┐
                    │ TRIAGE     20 roles/call → keep|drop    │
                    └────────────────────┬────────────────────┘
                                         │  ~20% survive
                    ┌─ Sonnet, per role ─▼────────────────────┐
                    │ SCORE      rubric → structured JSON     │
                    └────────────────────┬────────────────────┘
                                         │  keepers only
                    ┌─ agent sub-loop, isolated ctx, budgeted ┐
                    │ ENRICH     research company + contacts  │
                    └────────────────────┬────────────────────┘
                                         │
                    ┌─ code ──────────────▼───────────────────┐
                    │ STORE      SQLite / JSON (source truth) │
                    │ RENDER     jobs-log.md + digest         │
                    │ VERIFY     liveness sweep, expiry moves │
                    └─────────────────────────────────────────┘
```

Each stage is separately runnable, separately testable, and checkpoints its output.

---

## 4. The seven moves

### Move 1 — Structured store; markdown becomes a *view*

The highest-leverage change, and the one that unblocks the rest.

A `roles` table (SQLite is plenty; a JSON file works too) holds one row per role:

```
id, company, title, url, source, first_seen, last_seen, last_verified,
employment_type, location, remote_policy, rate_min, rate_max, rate_stated,
score, tier, score_breakdown (json), confidence, evidence_level,
status (live|expired|applied|rejected), enriched_at, contacts (json),
why_fits (json array), watch_outs (json array)
```

`jobs-log.md`, the digest, and the Obsidian note all become **rendered outputs**. The model never writes them.

Why this matters concretely:
- The reformat we did by hand becomes a template change plus `render.py`.
- Dedup becomes a query, not the model reading a 21-line text index.
- "Which ⏳ roles are >8 weeks old and unverified?" becomes `WHERE` — not a note the model might forget.
- `state/seen.md` disappears entirely.

### Move 2 — Split triage from deep scoring, and route models

Run 6 read 6 emails and hard-filtered 8 roles as obvious noise: *mechanical* design, *graphic* designers, mid-weight, furniture retail. Those cost the same tokens as evaluating Lyrebird Health.

- **Prefilter (code):** pure predicates. Gambling/crypto keywords, "graphic designer", "mechanical", below-senior titles, onsite >3 days, stated rate under floor. Free, instant, and deterministic.
- **Triage (Haiku, batched ~20 roles per call):** one line in, `keep|drop` + reason out. Cheap, high volume.
- **Deep score (Sonnet, one call per survivor):** the full rubric, structured output.

This is what actually dissolves the Tier-1 token pressure — not the current workaround of only looking at 4 companies a week.

### Move 3 — Enrichment as isolated sub-agents

One sub-agent per keeper role, each with:
- its own context (just that role — no cross-contamination between companies)
- a hard tool budget (e.g. 4 calls)
- a narrow brief: company, size, design maturity, named design leadership, outreach angle
- a required `confidence` and `sources` field in its return

The orchestrator holds only role IDs and short summaries. Sub-agents can run in parallel. This is the pattern that makes "enrich the top 3" scale to "enrich all keepers".

### Move 4 — Purpose-built tools with fallback chains

`WebFetch` returning 403 has silently degraded scores in four of six runs. Replace it with one well-designed tool:

```
fetch_job_ad(url) -> { text, evidence_level, source }
    1. direct fetch
    2. reader proxy (e.g. r.jina.ai)
    3. cached search snippet
    4. give up → evidence_level="none"
```

`evidence_level` (`full_ad` | `snippet` | `none`) then flows into the record. **A score derived from a snippet must be visibly distinct from one derived from the full ad** — that's the fix for Blinq's provisional 80/100 sitting in the 🔥 section next to Heidi's fully-evidenced 92.

Good agent tools look like good APIs: narrow, documented, hard to misuse, and honest about failure.

### Move 5 — Turn the calibration set into an eval harness

You already have labelled data in `job-criteria.md`: three "would apply" (Amber, Heidi, Cadmus) and three "would never" (Binance, xAI, crypto). That is an eval set — it's just not being executed.

```
tests/test_scoring.py
  - Amber, Heidi, Cadmus  → must score 🔥 (≥75)
  - Binance, xAI, crypto  → must hard-filter
  - plus every role you've thumbs-up/down'd since
```

Run it in CI on any change to `job-criteria.md` or the scoring prompt. Without this, every rubric tweak is a guess — you cannot tell an improvement from a regression. With it, the rubric becomes safely editable.

This is the single biggest quality lever available, and the data already exists.

### Move 6 — Fail loudly

Gmail was broken for ten weeks behind a green tick. Graceful degradation was the right call for *not losing a run*; it was the wrong call for *staying quiet*.

- Every stage emits a structured `run_record` (counts in, counts out, errors, tokens, cost).
- Health assertions after each run: `alerts_read == 0` twice consecutively, or `fetch_failure_rate > 50%`, or `new_roles == 0` for three runs → **open a GitHub issue** (or fail the job).
- A run that dies mid-way resumes from its last checkpoint rather than discarding everything.

Degrade the *work*, never the *signal*.

### Move 7 — A human-in-the-loop that actually teaches the system

Once a fortnight, the digest includes 3–5 borderline roles with a one-tap 👍/👎. Each response appends a labelled example to the calibration set, which feeds Move 5's eval harness.

This is the loop the current design lacks entirely: **the rubric never learns from your reactions.** Ten labels would sharpen it more than any amount of prompt tuning. You are the only source of ground truth for your own taste — the system should be harvesting it.

---

## 5. What *not* to do

- **Don't adopt an agent framework.** LangGraph/CrewAI/AutoGen would add abstraction over what is fundamentally seven functions and a queue. Plain Python + the Claude SDK, or Claude Code per stage.
- **Don't make it more autonomous.** It already never applies or sends outreach — keep that. Autonomy should go *down* per stage as structure goes up.
- **Don't rewrite in one go.** The system is working. Each phase below stands alone.
- **Don't let the model write the output files** once Move 1 lands. Rendering is code's job.

---

## 6. Staged rollout

| Phase | Change | Effort | Risk | Payoff |
|---|---|---|---|---|
| **0** | Structured store + `render.py`; markdown becomes a view | ~1 day | Low — render current log, diff until identical | Unblocks everything; format edits become free |
| **1** | Code prefilter + Haiku triage + model routing | ~half day | Low | Kills the token ceiling; lift the 4-company cap |
| **2** | Eval harness from the calibration set, wired into CI | ~half day | Very low | Rubric becomes safely editable |
| **3** | `fetch_job_ad` fallback chain + `evidence_level` on records | ~half day | Low | Fixes the snippet-scoring problem |
| **4** | Enrichment sub-agents, parallel + budgeted | ~1 day | Medium | Enrich every keeper, not just three |
| **5** | Health checks, checkpointing, GitHub-issue alerts | ~half day | Low | No more silent ten-week failures |
| **6** | 👍/👎 review loop feeding calibration | ~1 day | Low | The system starts learning your taste |

**If you only ever do one:** Phase 0. Everything else gets easier once markdown stops being the database.
**If you only ever do two:** add Phase 2. It's the difference between tuning by vibes and tuning by measurement.

---

## 7. Smaller wins, independent of all the above

- Model in `job-scout.yml` is pinned to `claude-sonnet-4-6`. Worth reviewing against the current Claude 5 family (`claude-sonnet-5`, `claude-haiku-4-5` for triage) as part of Move 2's routing.
- `state/inbox-dump.md` is gitignored, so cloud-run fetch errors never reach the repo — we had to download Actions logs twice this session. A tiny tracked `state/fetch-status.md` (status line only, no email content) would fix that.
- Duplicate-company handling: Blinq Staff + Senior, Heidi Senior + Head-of are separate rows with no relation. A `related_to` field would let the render group them.

---

## 8. Open decisions — these are yours, not mine

1. **Store: SQLite or flat JSON?** SQLite gives real queries and handles growth; JSON stays diffable in git, which suits a repo you read as much as run. Genuine trade-off.
2. **How autonomous should enrichment be?** A fixed research checklist per role (predictable, cheaper, blander) versus a real agent loop (better contacts, occasionally wanders, costs more).
3. **Where's the human gate?** Today: none, it just publishes. Options — review borderline roles only, review everything before it enters 🔥, or keep it fully automatic and rely on the eval harness.
4. **Is expiry the model's job or a cron's?** A weekly code-only liveness sweep (HTTP status on every live URL) would resolve the eleven-week "likely expired" drift without any model involvement.
