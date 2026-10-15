# d2r-port-radar：项目说明（给 AI 助手）

追踪基于 [jhaizhou-ops/d2r-mobile](https://github.com/jhaizhou-ops/d2r-mobile) 的衍生移植：其他 Switch 游戏（BotW、Hades、P5R、马里奥奥德赛……）、其他平台（Android、鸿蒙、tvOS），以及通用化工具链。产出一个静态网页 + 一份公开的 JSON 数据。

**最高原则：保持简单。** 一个脚本、一个模板、一份人工备注。不要引入框架、数据库、构建工具或第三方 Python 依赖（只用标准库 + `gh` CLI）。加功能前先问：能不能用 notes.json 解决？

## 结构

```
track.py             抓数据 → dist/index.html + dist/radar.json（唯一的脚本）
site/template.html   页面模板；所有 UI 和交互都在这里，数据通过 /*DATA*/null 注入
data/notes.json      人工备注 + 手动关注列表 + 屏蔽列表（唯一需要人维护的文件）
data/cache.json      增量缓存（按 pushed_at 判断），会提交到仓库供 CI 复用；删掉就全量重扫
dist/                生成物，不提交；CI 部署到 GitHub Pages
.github/workflows/   每 3 小时自动更新并部署
```

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

## “更新一下”的标准流程

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
