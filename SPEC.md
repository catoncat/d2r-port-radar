# Port Knowledge Spec v0.1

The format for porting knowledge: how to make one Switch game's native code run on other platforms (iOS / macOS / tvOS / Android …) on top of the d2r-mobile route. It is written for **AI agents first**: every object can be machine-read, every conclusion can be reproduced, and no game content is involved.

> Chinese and English mixed: field names and enum values are fixed English; prose (title / summary / body) may be in any language.

## 1. Object model

```
knowledge/
  games/<titleId>.md        one game: identity, technical profile, port status
  components/<id>.md        one reusable component: an HLE service, an NVN feature, a middleware, an engine, a host mechanism
  findings/<id>.md          one finding: a fact, a pitfall, a technique, or a fix
```

Every file is **Markdown + YAML front matter**. The front matter is machine-readable; the body is free prose for both humans and agents.

Knowledge is organised **by component**, and a game is just "which components it uses". A fix for CRIWARE audio helps every game that uses CRIWARE.

Tasks are **not written by hand**. They are generated from findings with `fix.state: open` (see §5).

### 1.1 Game `games/<titleId>.md`

| Field | Required | Meaning |
|---|---|---|
| `id` | ✓ | titleId of the base game, 16 hex digits uppercase, e.g. `0100CC80140F8000` |
| `name` | ✓ | display name |
| `summary` | ✓ | ≤ 200 characters: where the port stands |
| `builds` | ✓ | list of `{version, sdk?, build_id_sha256?}`. **Hash** of the build ID only, never the raw value |
| `engine` | | `ue4` / `unity` / `in-house:<name>` … |
| `middleware` | | component ids, e.g. `mw-criware` |
| `uses` | | other component ids this game relies on |
| `profile` | | free key/value technical facts (rendering mode, shader counts, scripting runtime …) |
| `status` | ✓ | list of `{platform, stage, device?, date, evidence, by}` |
| `ports` | | where the port code lives: `{repo, branch?, public: bool}` |

`stage` is an ordered ladder: `none` → `analysed` → `rewritten` → `boots` → `first-frame` → `title-screen` → `in-game` → `playable` → `complete`.

### 1.2 Component `components/<id>.md`

| Field | Required | Meaning |
|---|---|---|
| `id` | ✓ | kebab-case with a prefix: `hle-` (system service), `nvn-` (graphics API), `mw-` (middleware), `engine-`, `host-` (host mechanism), `plat-` (target platform) |
| `name` | ✓ | |
| `summary` | ✓ | ≤ 200 characters |
| `kind` | ✓ | `hle` / `nvn` / `middleware` / `engine` / `host` / `platform` |
| `host_files` | | source paths in the d2r-mobile tree that implement it |

Which games use a component, and which findings concern it, are computed; don't write them.

### 1.3 Finding `findings/<id>.md`

| Field | Required | Meaning |
|---|---|---|
| `id` | ✓ | `<game-or-scope>-<4 digits>`, e.g. `ts-0007`, `gen-0003` |
| `title` | ✓ | one line |
| `summary` | ✓ | ≤ 200 characters, enough for an agent to decide whether to read the body |
| `kind` | ✓ | `blocker` (stops progress) / `pitfall` (silent wrong behaviour) / `technique` (a reusable way to solve something) / `fact` (a property of a game or SDK) |
| `games` | | titleIds this applies to; empty = applies to the route in general |
| `components` | ✓ | component ids |
| `builds` | | the builds the addresses in this finding refer to, e.g. `["1.1.1"]` |
| `status` | ✓ | see §2 |
| `evidence` | ✓ | list of `{type, ref, note?}`; `type` ∈ `disasm` / `runtime` / `source` / `config` / `report` |
| `reproduce` | | a command or procedure that lets another agent re-derive the claim **on their own copy of the game** |
| `fix` | | `{state: open / done / wontfix, approach?, where?: {repo, branch?, path?, public: bool}, size?: S/M/L/XL}` |
| `needs` | | what someone needs to work on it: `generic` (nothing), `game:<titleId>`, `device:<mac/iphone/appletv/android>` |
| `related` | | other finding ids |
| `updated` | ✓ | `YYYY-MM-DD` |
| `by` | ✓ | who contributed: `{agent?, model?, human?}` |

## 2. Evidence rule

**No reproduction path or citable evidence, no finding.** Status:

| `status` | Meaning |
|---|---|
| `inferred` | reasoned from static reading, not confirmed |
| `verified` | confirmed by disassembly, a runtime trace, or running code; evidence cites where |
| `replicated` | ≥ 2 independent contributors reproduced it on their own copies |
| `contradicted` | later evidence disproved it; keep it and point `related` at the correction |
| `superseded` | still true but replaced by a better finding |

Never delete a wrong finding: mark it `contradicted`. Wrong turns are knowledge too.

## 3. Content boundary (enforced by `atlas.py validate`)

| Allowed | Forbidden |
|---|---|
| addresses / offsets tied to a build, symbol names, counts, config key names and values | any bytes of the game: code, data, shaders (original or translated) |
| scripts and tools | keys, `prod.keys`, title keys, firmware |
| descriptions in words | textures, audio, video, screenshots of game content |
| hashes of build IDs | installers (IPA / APK / NSP / XCI) or links to them, links to piracy sites |

Short instruction sequences named in prose ("`mrs ctr_el0` then `dc civac`") are fine; dumps are not. The validator rejects long hex runs, base64 blobs, key-like strings, binary files and blocked domains.

## 4. Agent interface

Static JSON, served at `https://catoncat.github.io/d2r-port-radar/`:

| Path | Content |
|---|---|
| `llms.txt` | start here |
| `api/index.json` | endpoints, counts, spec version |
| `api/search.json` | every object as `{type, id, title, summary, tags}`: load once, filter locally |
| `api/games/<titleId>.json` | game + its findings (summaries) + components + open tasks |
| `api/components/<id>.json` | component + games using it + findings |
| `api/findings/<id>.json` | the full finding including body |
| `api/tasks.json` | open work, filterable by `needs` and `size` |
| `api/titles.json` | all Switch base games `[titleId, name, publisher, year]` with port stage where known |
| `api/task/<id>.json` | **task bundle**: the finding, its components, related findings and host files, everything needed to start, with a token estimate |
| `radar.json` | port repos (forks and independent repos) |

Contributing: write files by the templates in `templates/`, run `python3 atlas.py validate` (errors come back as JSON: `{file, field, error, hint}`), open a PR.

## 5. Tasks

Every finding with `fix.state: open` is a task. Its id is the finding id. A task inherits `needs` and `fix.size`. Claim it by commenting `/claim <id>` on the tracking issue; a claim without progress for 48 hours lapses.

Acceptance: a task is done when the finding is updated to `fix.state: done` with `fix.where` pointing at the code, and at least one `runtime` evidence entry.
