---
id: hle-oe-sys
name: oe / time / hid / account / socket / vi 杂项
summary: 宿主接管了这些服务的初始化，但新游戏常导入同服务里 D2R 没用到的函数。
kind: hle
host_files:
- dm/host/ts/hle_ts_sys.c
---

宿主接管了这些服务的初始化，但新游戏常导入同服务里 D2R 没用到的函数。
