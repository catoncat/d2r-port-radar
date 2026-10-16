---
id: host-game-coupling
name: 宿主与 D2R 的耦合点
summary: 宿主核心里写死给 D2R 的默认行为、地址与玩法层调用；移植任何新游戏都先撞上它们。
kind: host
host_files:
- dm/host/main.c
- dm/host/hle_oe.c
- dm/host/hle_fs.c
- dm/host/loader.c
- dm/host/ts/ts_stubs.c
- dm/host/ts/gen_stubs.sh
---

上游 README「Taking it to other games」一节列出了已知的 D2R 专用默认值（渲染缩放、存档节流补丁、argv[0]、分辨率、`.d2s` 识别等）。上游建议的方向是把它们挪进按游戏的配置。

三角战略的做法：另编一个宿主 `tshost`，用 `g_game_d2r` 开关隔开 D2R 专用路径，玩法层符号用 `ts_stubs.c`（手写）+ `ts_stubs.S`（`gen_stubs.sh` 按链接缺的符号自动生成「返回 0」桩）顶上。
