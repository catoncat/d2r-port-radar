---
id: engine-ue4
name: Unreal Engine 4
summary: UE4 的 Switch 平台层：自管虚拟内存、旧版 SwitchAudio、前向/延迟渲染由项目 ini 决定。
kind: engine
---

识别方法：RomFS 里有 `UE4CommandLine.txt` 和 `*/Config/*.ini`。渲染路径看 `DefaultEngine.ini` 的 `r.ForwardShading`。
