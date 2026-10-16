# d2r-port-radar · 移植雷达

[d2r-mobile](https://github.com/jhaizhou-ops/d2r-mobile) 证明了 Switch 游戏的原生代码可以直接跑在 iPhone / Mac 上。之后很快有人把同一套宿主和图形层拿去移植别的游戏、别的平台。这个页面把这些分散在 800 多个 fork 和各个独立仓库里的进展集中到一处。

- **移植雷达**：https://catoncat.github.io/d2r-port-radar/ ，谁在移植什么
- **移植知识库**：https://catoncat.github.io/d2r-port-radar/atlas.html ，可复现的移植知识，按组件组织
- **给 AI Agent**：https://catoncat.github.io/d2r-port-radar/llms.txt ，静态 JSON 接口和 MCP，格式见 [SPEC.md](SPEC.md)

### 让你的 Agent 接入

```sh
curl -O https://raw.githubusercontent.com/catoncat/d2r-port-radar/main/mcp/atlas_mcp.py
claude mcp add port-atlas -- python3 "$PWD/atlas_mcp.py"
```

工具：`search`、`get_game`、`get_component`、`get_finding`、`list_tasks`、`get_task_bundle`。不用 MCP 的话，直接用 curl 读 `api/*.json` 也一样。

## 收录什么

- **Fork 网络**：上游的 fork 和 fork 的 fork，检查每个分支，统计相对上游改了哪些代码。
- **独立仓库**：通过 GitHub 搜索和人工补充，收录移植或通用化项目（会自动识别并标出镜像）。
- **人工备注**：阶段、完成度（0–100，有固定标尺）、一句话进展，见 [`data/notes.json`](data/notes.json)。

数据每 3 小时由 GitHub Actions 自动刷新。

## 收录政策

只收录源码仓库。**不链接、不收录**任何分发游戏数据、密钥、固件或成品安装包的仓库或链接。本站不托管任何游戏内容。

## 贡献知识

按 [`templates/`](templates/) 写 `knowledge/findings/<id>.md`，运行 `python3 atlas.py validate`，然后提 PR。每条结论都要附证据；没有直接证据的，要写清楚怎么在自己的游戏副本上复现。校验器会自动拒绝游戏字节、密钥、安装包链接和盗版站链接。

## 参与雷达

发现了没收录的移植，或者备注过时了？直接提 PR 修改 `data/notes.json`：

```json
"owner/repo": { "game": "游戏名", "status": "真机出图", "score": 65, "summary": "做到哪了（2026-10-15 核对 README）" }
```

`status` 固定词和 `score` 标尺见 [CLAUDE.md](CLAUDE.md)。

## 本地运行

```sh
gh auth login          # 需要 GitHub CLI
python3 track.py       # 增量更新，--full 全量重扫
open dist/index.html
```

只依赖 Python 3 标准库和 `gh`。

## License

MIT
