---
id: nvn-shader-pipeline
name: 着色器翻译链
summary: Maxwell 着色器 → SPIR-V（Ryujinx 翻译器）→ MSL（SPIRV-Cross）→ metallib，按控制段哈希匹配。
kind: nvn
host_files:
- dm/gfx/tools/dmsh_xlate
- dm/gfx/tools/ts_shaders.py
- dm/gfx/nvn/nvn_mtl.m
---

Maxwell 着色器 → SPIR-V（Ryujinx 翻译器）→ MSL（SPIRV-Cross）→ metallib，按控制段哈希匹配。
