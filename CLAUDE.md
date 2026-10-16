# d2r-port-radar：项目说明（给 AI 助手）

基于 [jhaizhou-ops/d2r-mobile](https://github.com/jhaizhou-ops/d2r-mobile) 路线的 Switch 原生移植，本站做两件事：

1. **移植雷达**（`track.py`）：谁在移植什么，数据从 GitHub 自动抓取。
2. **移植知识库**（`atlas.py`）：可复现的移植知识。**Agent 是第一用户**，所以产出静态 JSON 接口、`llms.txt` 和 MCP 服务器，网页只是给人看的视图。规范见 `SPEC.md`，那是知识格式的唯一权威。

**最高原则：保持简单。** git 仓库就是数据库，PR 就是审核流程。不引入框架、数据库或服务器。Python 只用标准库，唯一例外是 `atlas.py` 用到的 PyYAML。加功能前先问：能不能用现有文件格式解决？

## 结构

```
SPEC.md              知识格式规范（对象模型、证据规则、内容边界、接口、任务协议）
knowledge/           知识本体：games/<titleId>.md、components/<id>.md、findings/<id>.md
templates/           三种对象的模板
atlas.py             validate（JSON 报错）/ build（→ dist/api/*、llms.txt、atlas.html）/ titles（刷新游戏列表）
mcp/atlas_mcp.py     MCP 服务器，只用标准库，读线上的静态接口
site/atlas.html      知识库网页；site/llms.txt 是 Agent 入口模板
track.py             雷达抓取 → dist/index.html + dist/radar.json
site/template.html   雷达页面
data/notes.json      雷达的人工备注、手动关注、屏蔽列表
data/cache.json      雷达增量缓存（提交到仓库供 CI 复用）
data/titles.json     Switch 游戏列表（来自 blawar/titledb，只取白名单文字字段）
dist/                生成物，不提交；CI 部署到 GitHub Pages
.github/workflows/   每 3 小时：track.py → atlas.py build → 部署
```

## 知识库：写结论的规矩

- 先读 `SPEC.md`。写完必须让 `python3 atlas.py validate` 通过，报错是 JSON，按 `hint` 改。
- **以代码和运行证据为准，不以报告为准。** 报告会过时，比如三角战略的 SUMMARY.md 写于跑通之前。
- 知识按组件组织：先看能不能挂到已有组件上，确实没有再新建组件。
- 错的结论不删，标成 `contradicted`。
- 修复代码没公开时，`fix.where.public: false`，并在正文里说清楚。

## 三角战略（第一份 dogfood 数据）

- 移植代码在本机 `~/d2r-mobile` 的 `ts-port` 分支，主要是 `dm/host/ts/`，**另一个 Claude 会话正在改它**：只读，不写，不切分支。
- 工作区 `~/ts-work`：`reports/`（移植前普查）、`scripts/`（只输出名字和计数的扫描脚本）、`run/log/`（运行日志）。
- 更新知识时：先读 `dm/host/ts/*.c` 的头注释（作者用【核】标注反汇编核实过的内容）和最新运行日志，再改 `knowledge/`。

## 数据源

自动抓取（`track.py`）：
1. **Fork 网络**：上游的 fork，以及 fork 的 fork（一层）。只看 fork 后推送过的仓库，**检查每个分支**：真正的移植经常不在默认分支上（例如 botw-mobile 的 `botw-host-boot`），而且很多 fork 不改仓库描述（hades-ios 的描述仍然是 D2R 原文）。
2. **独立仓库**：用 GitHub 仓库搜索（`SEARCH` 常量）加上 notes.json 里列出但不在 fork 网络里的仓库。如果最近提交的标题全都在上游出现过，就判定为镜像。

只能人工跟进的信息源（看到有价值的就写进 notes.json）：
- 上游 Issues，例如 #53 Apple TV 社区移植；上游没有开 Discussions
- 作者的 X 账号 @happyjoejiang：BotW 等进展最早出现在这里
- Hacker News（Algolia API）、A9VG、B站、V2EX、Linux.do
- scarin-corporations/ports-lib：同类泛移植目录，有 catalog.json，可以交叉核对

GitHub 代码搜索不会索引新仓库和 fork，按代码特征找副本的办法基本失效，不要在这上面花时间。

## 雷达：“更新一下”的标准流程

1. `python3 track.py`：增量运行，只重查有新推送的仓库，约 10–30 秒。
2. 在 `dist/radar.json` 里找出这两类：①没有 note 的非 trivial 仓库；②note 写的日期早于它最后一次推送的仓库。
3. 对每个这样的仓库，用 `gh api` 读 README / STATUS 文件和最近的提交（**不要 clone**），然后更新 notes.json。
4. 再跑一次 `python3 track.py`，必要时用浏览器打开 `dist/index.html` 检查。
5. 向用户汇报：新出现了什么、谁有进展、谁停滞了。

## notes.json 字段

```json
"owner/repo": {
  "game": "显示用的游戏或平台名（会覆盖自动关键词标签）",
  "status": "阶段，用下面的固定词",
  "score": 0-100,
  "summary": "一两句：做了什么、卡在哪；写清楚核对日期，例如（2026-10-15 核对 README）",
  "hide": true, "why": "屏蔽原因"
}
```

**status 固定词**（模板按这些词着色）：`方案验证` `研究阶段` `早期启动` `早期基础设施` `图形调试` `调试卡死` `真机出图` `真机可用` `可玩` `通用化`

**score 标尺**（要求可复核，依据只能是 README、提交记录或实测记录里写明的内容，不能只凭项目自己宣传）：
- 0–20：重新发布、换皮，或者只有方案文档
- 20–40：研究阶段，或只有代码骨架
- 40–60：程序能解析和改写，开始启动
- 60–80：真机能出图，或已经通用化到可以接入多款游戏
- 80–100：能进入游戏并操作，100 = 完整可玩

## 收录政策（公开发布，必须遵守）

- 只收录**源码仓库**。不链接 Release 资产、IPA、APK、网盘或 torrent。
- **分发游戏数据、密钥或固件的仓库一律屏蔽**（`hide` + `why`），比如 jiayx/d2r-mobile-build。发现 README 里有游戏数据下载方式的，也一样屏蔽。
- 不复制别人 README 里的截图，不转载游戏素材。
- 备注里只写技术进展，不评价个人。

## 环境注意

- 当前网络访问 api.github.com 偶尔会报一张 bilibili 证书的 TLS 错误。`track.py` 已经内置重试，失败的仓库不会写入缓存，下次运行会自动重查。
- 在 CI 里用 `GH_TOKEN=${{ secrets.GITHUB_TOKEN }}`，配额是每小时 1000 次请求，增量运行通常只需要几十次。
