---
id: 0100XXXXXXXXX000     # base-game titleId; must equal the file name
name: Game name
summary: ≤200 chars on where the port stands
builds: [{version: "1.0.0", sdk: "12.3.7"}]
engine: engine-ue4       # a component id, if known
middleware: [mw-criware]
uses: [hle-fs]
profile: {rendering: forward, shaders: "n jobs"}
status:
  - {platform: macos, stage: boots, device: "M2 Mac", date: 2026-01-01, evidence: "log / video / note", by: handle}
  # stage: none analysed rewritten boots first-frame title-screen in-game playable complete
ports: [{repo: owner/repo, branch: main, public: true}]
---

Route taken, scripts used, timeline.
