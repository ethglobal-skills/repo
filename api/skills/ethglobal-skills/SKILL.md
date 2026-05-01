---
name: ethglobal-skills
description: Search ETHGlobal hackathon projects, sponsor bounties, prize winners, and qualification requirements. Use when the user asks about ETHGlobal hackathons, past winning projects, sponsor bounties, prize requirements, or wants to find projects built at ETHGlobal events.
---

# ETHGlobal Hackathon Search API

Search ETHGlobal hackathon projects, sponsor bounties, and prize winners across all events from ETHWaterloo to present.

Base URL: `https://your-deployment.vercel.app` (replace with actual deployment URL)

---

## Important: Always use exact names

- **Event names**: Use the exact name from the list below. Do not call `/api/events`.
- **Sponsor names**: Use the exact sponsor name as it appears in prize results. If unsure, call `GET /api/sponsors?keyword=...` to look it up.
- **Year disambiguation**: If the user says "ETHGlobal New York" without a year and multiple events match, ask them which year before querying.

### All events (use these exact strings for the `event` param)
ETHGlobal Mumbai, ETHGlobal Tokyo 2026, ETHOnline 2026, ETHGlobal Lisbon 2026, ETHGlobal New York 2026, Open Agents, ETHGlobal Cannes 2026, HackMoney 2026, ETHGlobal Buenos Aires, ETHOnline 2025, ETHGlobal New Delhi, ETHGlobal New York 2025, Unite Defi, ETHGlobal Cannes, ETHGlobal Prague, ETHGlobal Taipei, ETHGlobal Trifecta, Agentic Ethereum, ETHGlobal Bangkok, ETHGlobal San Francisco, ETHGlobal Singapore, ETHOnline 2024, Superhack 2024, ETHGlobal Brussels, StarkHack, HackFS 2024, ETHGlobal Sydney, Scaling Ethereum 2024, Frameworks, ETHGlobal London, Circuit Breaker, LFGHO, ETHIndia 2023, ETHGlobal Istanbul, ETHOnline 2023, ETHGlobal New York, Superhack, ETHGlobal Paris, ETHGlobal Waterloo, HackFS 2023, Autonomous Worlds, ETHGlobal Lisbon, ETHGlobal Tokyo, Scaling Ethereum 2023, FVM Space Warp, ETHIndia 2022, Hack FEVM, ETHSanFrancisco 2022, ETHBogotá, ETHOnline 2022, ETHMexico, Metabolism, HackFS 2022, ETHNewYork 2022, HackMoney 2022, ETHAmsterdam, DAOHacks, LFGrow, BuildQuest, Road to Web3, NFTHack 2022, Web3Jam, UniCode, ETHOnline 2021, HackFS 2021, HackMoney 2021, Web3 Weekend, Scaling Ethereum, NFTHack, MarketMake, ETHOnline, HackFS, HackMoney, ETHLondonUK, ETHWaterloo 2019, ETHBoston, ETHNewYork, ETHCapeTown, ETHParis, ETHSingapore, ETHSanFrancisco, ETHWaterloo

---

## Endpoints

### GET /api/sponsors
Returns sponsor names. Call this when a sponsor query returns no results to find the exact name to use.

| Param | Description |
|---|---|
| `keyword` | Partial name match to narrow results (optional) |

**Response:**
```json
{ "sponsors": ["Flow", "Uniswap Foundation", "World", ...] }
```

**Examples:**
- `GET /api/sponsors?keyword=uniswap` → `["Uniswap Foundation"]`
- `GET /api/sponsors` → full list

---

### GET /api/prizes
Returns sponsor bounties grouped by sponsor, with descriptions, qualifications, and resource links.

**At least one of `event` or `sponsor` is required.**

| Param | Description |
|---|---|
| `event` | Exact event name from the list above |
| `sponsor` | Exact sponsor name (use /api/sponsors to look up if unsure) |

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
- All bounties at ETHGlobal Taipei: `GET /api/prizes?event=ETHGlobal+Taipei`
- World's bounties at ETHGlobal Taipei: `GET /api/prizes?event=ETHGlobal+Taipei&sponsor=World`
- All World bounties (most recent 10): `GET /api/prizes?sponsor=World`

---

### GET /api/projects
Search hackathon projects. Filter by event, keyword, sponsor, or prize won.

| Param | Description |
|---|---|
| `event` | Exact event name from the list above |
| `keyword` | Searches title, tagline, description, and how_its_made |
| `sponsor` | Exact sponsor name — filters to projects that won a prize from this sponsor |
| `prize` | Partial prize title match (e.g. `Finalist`, `Best Mini App`) |
| `pool` | Set to `true` to include pool prize projects when filtering by sponsor (default: false) |
| `include` | Comma-separated optional fields: `description`, `how_its_made` |
| `limit` | Max results, default `30`, max `100` |

**Presentation:**
- Always hyperlink the project title using its `url` field: `[Project Title](url)`. Never display the raw URL.
- If `github` is present, hyperlink it as `[GitHub](github_url)`.
- If `live_demo` is present, hyperlink it as `[Live Demo](live_demo_url)`.
- When presenting bounties, always include both the `description` and `qualifications` fields in full. Never summarize or omit them.

**Notes:**
- `prizes_won` is only present when `sponsor` or `prize` is used.
- When filtering by `sponsor` only, pool prizes (e.g. "Flow Builder Pool Prize") are excluded by default — only named prize winners are returned. Pass `pool=true` to include them.
- For finalists, use `prize=Finalist`.

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

**Examples:**
- All projects at ETHGlobal Taipei: `GET /api/projects?event=ETHGlobal+Taipei`
- Projects mentioning "uniswap" in any field: `GET /api/projects?keyword=uniswap`
- World's Best Mini App winners at ETHGlobal Taipei: `GET /api/projects?event=ETHGlobal+Taipei&sponsor=World&prize=Best+Mini+App`
- Finalists at ETHGlobal Taipei: `GET /api/projects?event=ETHGlobal+Taipei&prize=Finalist`
- All Uniswap Foundation named prize winners: `GET /api/projects?sponsor=Uniswap+Foundation`
- All Uniswap Foundation winners including pool: `GET /api/projects?sponsor=Uniswap+Foundation&pool=true`

---

## Typical workflows

**"What bounties does Uniswap have at ETHGlobal Taipei?"**
1. `GET /api/prizes?event=ETHGlobal+Taipei&sponsor=Uniswap+Foundation`
   - If no results: `GET /api/sponsors?keyword=uniswap` to find the exact sponsor name

**"Who won the Uniswap prize at ETHGlobal Taipei?"**
1. `GET /api/projects?event=ETHGlobal+Taipei&sponsor=Uniswap+Foundation`

**"Show me stablecoin projects from ETHGlobal Taipei"**
1. `GET /api/projects?event=ETHGlobal+Taipei&keyword=stablecoin`

**"What are World's bounty requirements at ETHGlobal Cannes 2026?"**
1. `GET /api/prizes?event=ETHGlobal+Cannes+2026&sponsor=World`

**"Show me the Finalist projects at ETHGlobal Bangkok"**
1. `GET /api/projects?event=ETHGlobal+Bangkok&prize=Finalist`

**"Who received the Flow pool prize at ETHGlobal New York 2025?"**
1. `GET /api/projects?event=ETHGlobal+New+York+2025&sponsor=Flow&pool=true`
