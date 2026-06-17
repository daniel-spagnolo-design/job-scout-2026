# Email Alerts Setup — do this before you leave (~1 hour)

The agent reads job-alert emails out of one Gmail label. The only manual part is creating the saved-search alerts on each platform and routing them into that label. Once that's done, everything else is automated. Tick these off.

## Step 1 — Create the Gmail label + filter (5 min)
1. Gmail → Settings (gear) → **See all settings** → **Labels** → **Create new label** → name it exactly `job-scout`.
2. Settings → **Filters and Blocked Addresses** → **Create a new filter**.
3. In the **From** field, paste the alert senders (you can edit this later as you add platforms):
   ```
   jobalerts-noreply@linkedin.com OR jobs-noreply@linkedin.com OR jobalerts@seek.com.au OR alert@indeed.com OR noreply@glassdoor.com OR noreply@uiuxjobsboard.com OR noreply@startup.jobs OR noreply@wellfound.com OR noreply@theloop.com.au
   ```
4. **Create filter** → tick **Apply the label: `job-scout`** and **Never send it to Spam** → **Create filter**.
   - Tip: also tick "Also apply filter to matching conversations" so any existing alerts get labelled.

## Step 2 — Saved-search alerts per platform
For each, set the saved search to **daily email**. Filter to **Australia + Remote**, level **Senior / Staff / Principal / Lead**, and where the board allows, create both a **Contract/Temp** and a **Full-time** variant.

- [ ] **LinkedIn** — 3–4 saved searches, daily alerts:
  - "Senior Product Designer" · Australia + Remote
  - "Staff Product Designer" OR "Principal Product Designer" · Australia + Remote
  - "Product Designer" + Contract · Australia + Remote
  - (LinkedIn alert emails arrive 18–72h after a job posts — that's fine.)
- [ ] **Seek** (seek.com.au) — "Senior Product Designer", set work type Contract/Temp AND a second for Full-time. Save search → email alerts on.
- [ ] **Indeed AU** — 1–2 broad alerts ("senior product designer", "product designer contract"), Australia.
- [ ] **Glassdoor AU** — 1 alert, "senior product designer" Australia.
- [ ] **uiuxjobsboard.com** — alert if available (agent also fetches this directly, so optional).
- [ ] **startup.jobs / Wellfound** — alert for product design, remote AU-friendly.
- [ ] **The Loop** (theloop.com.au) — alert + make sure your portfolio profile is current.

## Step 3 — Recruiters (register + tell them your dates)
Register and set alerts, then email 2–3 to say you're back and available from **[your return date]**. A known return date gets you pipelined — this beats any automation.

- [ ] Aquent AU
- [ ] Brightbox Consulting
- [ ] Creative Recruiters
- [ ] SustainRecruit
- [ ] TheDriveGroup
- [ ] (generalists, optional) Hays · Robert Half · Talent International

## Step 4 — Reconnect the Gmail connector with full access
The agent needs the Gmail connector authorised to **read** mail and **create drafts**. Currently it reports limited permissions. In Claude, reconnect the Gmail connector and grant read + draft scopes. Until that's done the agent will run web-boards only and skip the email portion.

## Step 5 — Verify (do one test before you fly)
Once a few alerts have landed in `job-scout`, ask Claude: **"run my job scan"**. Check the output in `jobs-log.md` and tune `job-criteria.md` if the scoring feels off.

---

### Notes
- One label is all the agent needs — don't overthink folder structure.
- Because everything funnels into Gmail, **no data is ever lost** even if a weekly run is missed. Worst case, one catch-up run on return processes the whole backlog.
- Add/remove senders in the Step 1 filter anytime as you discover which platforms actually email you.
