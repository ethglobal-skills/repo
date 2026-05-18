# ETHGlobal Skills

```bash
npx skills add ethglobal-skills/repo
```

One command gives your coding agents access to:

- 17,643 hackathon projects from the past 6 years
- sponsor docs + bounties for upcoming hacks
- all Finalist + bounty winners

If using Claude Code, use the plugin below or include `use ethglobal-skills` in the prompt.

For example queries and full API docs, check out [`skills/ethglobal-skills/SKILL.md`](skills/ethglobal-skills/SKILL.md). Rate limiting is done via x402. If you reach over 10 requests / minute, it'll be $0.05 USDC on Base mainnet. Install AgentCash and transfer a small amount to continue!

**⭐️ If you found this useful, please star this repo! ⭐️**

https://github.com/user-attachments/assets/6253ae42-d6de-4800-8ff3-7af8ee4731a7

### Claude Code

```
/plugin marketplace add ethglobal-skills/repo
/plugin install ethglobal@ethglobal-skills
```

One-time setup. The skill is then available globally as `/ethglobal:ethglobal-skills`.

### To Do

- Update + scrape prize descriptions/requirements for future hacks as they come in
- Add prize dollar amounts + placements
- Add prize descriptions before ETHGlobal Istanbul
- Add sponsor docs from hackathons before Open Agents


Inspired by [Colosseum Copilot](https://docs.colosseum.com/copilot/introduction) and [ETHSkills](https://ethskills.com/).
