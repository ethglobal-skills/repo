---
name: ethglobal-skills
description: Search ETHGlobal hackathon projects, sponsor bounties, prize winners, and qualification requirements. Use when the user asks about ETHGlobal hackathons, past winning projects, sponsor bounties, prize requirements, or wants to find projects built at ETHGlobal events.
---

# ETHGlobal Hackathon Search API

Search ETHGlobal hackathon projects, sponsor bounties, and prize winners across all events from ETHWaterloo to present.

Base URL: `https://your-deployment.vercel.app` (replace with actual deployment URL)

---

## Endpoints

### GET /api/events
Returns all hackathon events sorted by most recent first.

**No parameters.**

**Response:**
```json
{
  "events": [
    {
      "name": "ETHGlobal Taipei",
      "url": "https://ethglobal.com/events/taipei",
      "start_date": "2025-04-04",
      "end_date": "2025-04-06"
    }
  ]
}
```

**Use this to:** look up valid event names before querying prizes or projects.

---

### GET /api/prizes
Returns sponsor bounties with descriptions, qualification requirements, and resource links. Results are grouped by sponsor.

**At least one of `event` or `sponsor` is required.**

| Param | Description |
|---|---|
| `event` | Partial event name, case-insensitive (e.g. `ethglobal taipei`) |
| `sponsor` | Exact sponsor name, case-insensitive (e.g. `world`, `uniswap foundation`) |

When `sponsor` is provided without `event`, returns the most recent 10 unique prizes for that sponsor across all events.

**Response:**
```json
{
  "results": [
    {
      "name": "World",
      "about": "...",
      "docs": [
        { "name": "Mini App Documentation", "url": "https://..." }
      ],
      "prizes": [
        {
          "title": "Best Mini App",
          "description": "...",
          "qualifications": "..."
        }
      ]
    }
  ]
}
```

**Examples:**
- All bounties at ETHGlobal Taipei: `GET /api/prizes?event=ethglobal+taipei`
- World's bounties at ETHGlobal Taipei: `GET /api/prizes?event=ethglobal+taipei&sponsor=world`
- All World bounties (most recent 10): `GET /api/prizes?sponsor=world`

---

### GET /api/projects
Search hackathon projects. Filter by event, keyword, sponsor, or prize won.

| Param | Description |
|---|---|
| `event` | Partial event name, case-insensitive (e.g. `ethglobal taipei`) |
| `keyword` | Searches title, tagline, description, and how_its_made |
| `sponsor` | Exact sponsor name — filters to projects that won a prize from this sponsor |
| `prize` | Partial prize title — filters to projects that won a matching prize (e.g. `best mini app`, `finalist`) |
| `include` | Comma-separated optional fields: `description`, `how_its_made` |
| `limit` | Max results, default `20`, max `100` |

**Response:**
```json
{
  "projects": [
    {
      "title": "Realove",
      "url": "https://ethglobal.com/showcase/realove-siv7w",
      "tagline": "...",
      "github": "https://github.com/...",
      "live_demo": "https://...",
      "hackathon": "ETHGlobal Taipei",
      "prizes_won": ["Best Mini App 1st place"]
    }
  ]
}
```

`prizes_won` is only present when `sponsor` or `prize` is used.

**Examples:**
- All projects at ETHGlobal Taipei: `GET /api/projects?event=ethglobal+taipei`
- Projects mentioning "uniswap" in any field: `GET /api/projects?keyword=uniswap`
- World's Best Mini App winners at ETHGlobal Taipei: `GET /api/projects?event=ethglobal+taipei&sponsor=world&prize=best+mini+app`
- Finalists at ETHGlobal Taipei with full descriptions: `GET /api/projects?event=ethglobal+taipei&prize=finalist&include=description,how_its_made`
- All Uniswap Foundation prize winners: `GET /api/projects?sponsor=uniswap+foundation`

---

## Typical workflows

**"What bounties does Uniswap have at ETHGlobal Taipei?"**
1. `GET /api/prizes?event=ethglobal+taipei&sponsor=uniswap+foundation`

**"Who won the Uniswap prize at ETHGlobal Taipei?"**
1. `GET /api/projects?event=ethglobal+taipei&sponsor=uniswap+foundation`

**"Show me DeFi projects from ETHGlobal Taipei"**
1. `GET /api/projects?event=ethglobal+taipei&keyword=defi`

**"What hackathons has ETHGlobal run?"**
1. `GET /api/events`

**"What are World's bounty requirements?"**
1. `GET /api/prizes?sponsor=world` — returns most recent 10 with qualifications and docs
