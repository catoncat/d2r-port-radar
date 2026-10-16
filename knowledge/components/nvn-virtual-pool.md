---
id: nvn-virtual-pool
name: NVN 虚拟（稀疏）内存池
summary: MapVirtual 等虚拟池接口，与宿主「GPU 地址 = CPU 地址、池 = 零拷贝 MTLBuffer」模型冲突。
kind: nvn
host_files:
- dm/gfx/nvn/hle_nvn.c
---

MapVirtual 等虚拟池接口，与宿主「GPU 地址 = CPU 地址、池 = 零拷贝 MTLBuffer」模型冲突。
