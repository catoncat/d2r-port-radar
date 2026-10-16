---
id: hle-os-cache
name: 缓存维护指令
summary: FlushDataCache / __clear_cache 里的 dc/ic 指令在 macOS 用户态非法，需要宿主接管。
kind: hle
host_files:
- dm/host/ts/hle_ts_cache.c
---

FlushDataCache / __clear_cache 里的 dc/ic 指令在 macOS 用户态非法，需要宿主接管。
