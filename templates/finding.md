---
id: xx-0001              # <game short name or "gen">-<4 digits>; must equal the file name
title: One-line statement of what you found
summary: ≤200 chars. Enough for another agent to decide whether to read the body.
kind: blocker            # blocker | pitfall | technique | fact
games: [0100XXXXXXXXX000] # titleIds; omit for route-wide findings
builds: ["1.0.0"]        # required when games is set
components: [hle-fs]     # see knowledge/components/
status: inferred         # inferred | verified | replicated | contradicted | superseded
evidence:
  - {type: disasm, ref: "sdk+0x123456: what is there"}   # disasm | runtime | source | config | report
reproduce: "script + args another agent can run on their own copy"
fix:
  state: open            # open | done | wontfix
  approach: how it was / could be solved
  where: {repo: owner/repo, branch: main, path: dm/host/..., public: true}
  size: S                # S | M | L | XL
needs: [generic]         # generic | game:<titleId> | device:<mac|iphone|appletv|android>
related: []
updated: 2026-01-01
by: {agent: claude-code, model: ..., human: your-github-handle}
---

Free text: context, dead ends, why the fix works. No game bytes, keys, or links to game files.
