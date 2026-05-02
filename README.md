# ETHGlobal Skills

```bash
npx skills add ethglobal-skills/repo
```

One command gives your coding agents access to:

- 17,180 hackathon projects from the past 6 years
- sponsor docs + bounties for upcoming hacks
- all Finalist + bounty winners

---

## Quickstart

### 1. Install the skill

Run `npx skills add ethglobal-skills/repo`.

### 2. What you get

The skill wraps a search API over ETHGlobal hackathons from the past 6 years. Agents use it to:

- Look up **sponsor prizes** (descriptions, qualifications, doc links) with `GET /api/prizes`
- **Search projects** by event, keyword, sponsor, or prize (e.g. Finalists) with `GET /api/projects`
- Resolve **exact sponsor names** with `GET /api/sponsors` when a query returns nothing

### 3. Using exact names

- **Events:** use the exact event strings listed in the skill
- **Sponsors:** use names as returned by prizes/projects; if unsure, call `/api/sponsors?keyword=...`.
- **Years:** if an event name is ambiguous (e.g. “ETHGlobal New York”), pick the year before querying.

### 4. Typical agent workflows

**Bounties available at a hackathon from specific sponsor**

1. `GET /api/prizes?event=<event-name>&sponsor=<sponsor-name>`
2. If empty, `GET /api/sponsors?keyword=...` to find the sponsor name.

**Who won a sponsor’s prize**

1. `GET /api/projects?event=<event-name>&sponsor=<sponsor-name>`

**Finalists**

1. `GET /api/projects?event=<event-name>&prize=Finalist`

**Thematic search**

1. `GET /api/projects?event=<exact-event>&keyword=<topic>`

Full endpoint tables, response shapes, presentation rules (e.g. hyperlink titles, include full bounty text), rate limits, and **AgentCash** / 402 payment steps live in [`skills/ethglobal-skills/SKILL.md`](skills/ethglobal-skills/SKILL.md). Companion files in that folder: **sponsor docs / MCP / skills** → [`SPONSOR_RESOURCES.md`](skills/ethglobal-skills/SPONSOR_RESOURCES.md); **hackathon FAQ** → [`HACKATHON_FAQ.md`](skills/ethglobal-skills/HACKATHON_FAQ.md).

### 5. Version check

After the first API call, compare the `X-Skill-Version` response header to the version in the skill. If the API reports a newer version, reinstall with the same `npx skills add …` pattern the skill documents.