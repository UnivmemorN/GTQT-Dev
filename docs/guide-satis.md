# GuideQT 与 SatisMC 的 1.12.2 来源

## GuideQT 的早期实现

作者在 5 月 10 日的演示中展示了 `config/wiki/`、`discoveryTag` 和图片路径 `quantumhue:wiki/img.png`。当天的 QuantumHue 提交包含相同的 JSON 页面、图片、加载器和 `/wiki` 命令。6 月 8 日，作者在本人视频的评论中称这套攻略为 GuideQT；当时的源码还实现了从机器提示按 W 打开攻略。该实现的 Forge 模组 ID 是 `quantumhue`，声明版本为 `1.0.5`。[5 月演示](https://www.bilibili.com/video/BV1BA5j6jEhu/) · [5 月源码](https://github.com/GTQT/QuantumHue-Visualizer/tree/4367435ade4c4707553a3eaa02969f81c8c9c254) · [作者回复](https://www.bilibili.com/video/BV1DWE36cEGQ/#reply302060750849) · [6 月实现](https://github.com/GTQT/QuantumHue-Visualizer/tree/bb58d114a59d36ef9f78d98f96f9e9439b12dbf9)

10 月 31 日，作者从 QuantumHue 删除了 Wiki 和结构预览。后续项目文档仍提到与 GuideQT 统一外观。公开发布的 QuantumHue 1.0.0、1.0.1、1.0.3 和 1.0.4 的 JAR 均无这套 Wiki。复现演示时需要按提交取源码。后续文档没有给出独立版的下载坐标。[移除提交](https://github.com/GTQT/QuantumHue-Visualizer/commit/72e08b4f1b3d64748ca3bbf3e09bf133de0f8405) · [作者的集成说明](https://github.com/GTQT/QuantumHue-Visualizer/blob/7aa190315981717005acc233cbada39c520fe217/docs/Store-Notice.md)

## 与 GTQT-Dev 的兼容性

在 `pack19Candidate` 的隔离副本中，5 月原始源码的 Java 和资源均与提交逐文件比对。用十月 GT、ModularUI 3.1.5 和 Forge 2860 编译重混淆后，原件 SHA-256 为 `18999384e4a290df13c171d0326313793be236267f610aa9e3e27813d204d9de`。专服在 QuantumHue 初始化时抛出 `That channel is already registered`。Wiki 占用了七月 Core 已登记的 `gtqtcore` 网络频道，服务端未能开放联机。[频道注册](https://github.com/GTQT/QuantumHue-Visualizer/blob/4367435ade4c4707553a3eaa02969f81c8c9c254/src/main/java/meowmel/quantumhue/network/PacketHandler.java#L14-L20)

只把频道改为 `qh_wiki` 后，专服在下一阶段因缺少 `SimpleBlurHandler` 退出。其原因是 QuantumHue 在两端都注册了模糊、物品提示和群系信息三个客户端监听器。此外，历史版本的外观集成还会调用候选包 The One Probe 中缺失的 `Config.isJadeTheme()`。[初始化源码](https://github.com/GTQT/QuantumHue-Visualizer/blob/4367435ade4c4707553a3eaa02969f81c8c9c254/src/main/java/meowmel/quantumhue/QuantumHue.java#L65-L70) · [The One Probe 集成](https://github.com/GTQT/QuantumHue-Visualizer/blob/4367435ade4c4707553a3eaa02969f81c8c9c254/src/main/java/meowmel/quantumhue/LateMixin.java#L14-L18)

五月实验补丁将 Wiki 移到独立频道，把三个视觉监听器限于物理客户端，并按当前 The One Probe 是否提供主题接口来启用皮肤。神秘时代的客户端集成独立注册。实验件 SHA-256 为 `6ab64338e282e512c6ca53d58e7b3c1cfebd9250c18d3e9876613aff170ac457`。从固定源码和补丁在新目录离线重建后，JAR 的 110 项文件内容逐项一致，其中含 73 个类。[验收所用源码补丁](../dev/pack/quantumhue-may-wiki.patch)

实测使用完整候选包的隔离副本，两端各加入同一实验件。普通玩家关闭入服公告后执行 `/wiki`，客户端收到一个 `ShowWikiPacket`，读取了 8 个“Wiki 编写指南”页面，欢迎页排出 22 行。两轮与 JAR 逐项比对的 9 个 JSON 含索引和 8 页正文。专服保存后，第二对独立进程读回同一世界和玩家，再次执行命令得到相同结果。两轮双方均正常退出。五月版的验收范围是命令、通信、内置示例和读档重连。[双端验收记录](../evidence/quantumhue-may-wiki.json)

6 月 8 日带 W 快捷键和电力高炉 3D 预览的版本，用作者当日所带 GT 可编出运行 JAR（SHA-256 为 `f886d016d929acca3f5944299c41ce52b96f4e30dfdf49b067ae6590246bc889`）。换成候选包的十月 GT，多方块预览出现 7 条编译错误，涉及 `BlockPatternTemplate`、`MultiblockState`、`PatternMatchContext` 和 `TraceabilityPredicate` 四个旧类型。这个版本需适配结构预览才能在十月组合上验收。[多方块预览源码](https://github.com/GTQT/QuantumHue-Visualizer/blob/bb58d114a59d36ef9f78d98f96f9e9439b12dbf9/src/main/java/meowmel/quantumhue/wiki/gregtech/MultiblockPreviewRenderer.java)

## SatisMC 的蓝图与建造器

5 月 29 日的视频记录了作者受 H-crab 的 RTS Building 启发实现鸟瞰建造。5 月 31 日的演示能看到玩家选择蓝图、旋转、镜像和下单建造。6 月 9 日的 QuantumHue 源码明确把电力高炉示例标为 SatisMC 格式。随附的 `bp_4x_ebf.json` 大小为 9 × 4 × 5，含 116 个方块和 44 条机器实体数据，还列有放置材料。[鸟瞰演示](https://www.bilibili.com/video/BV1oxVa6QEXQ/) · [蓝图放置演示](https://www.bilibili.com/video/BV1agVQ6eEDP/?t=20) · [作者的格式说明](https://github.com/GTQT/QuantumHue-Visualizer/blob/c2d3f1552c69abcb3104cd6ad254e8a9015f7c55/src/main/java/meowmel/quantumhue/wiki/gregtech/EBFPage.java#L39) · [蓝图原件](https://github.com/GTQT/QuantumHue-Visualizer/blob/c2d3f1552c69abcb3104cd6ad254e8a9015f7c55/src/main/resources/assets/quantumhue/wiki/bp_4x_ebf.json)

QuantumHue 的读取器把蓝图加载到 `TrackedDummyWorld` 显示预览。公开样本能用来测试数据兼容性。要验收 SatisMC 的生存建造，仍缺少能让服务端在真实世界放置方块、扣除玩家材料的实现。H-crab 后来发布的 1.12.2 移植登记为 `rtsbuilding`，作者和模组 ID 均可区分。[预览读取器](https://github.com/GTQT/QuantumHue-Visualizer/blob/965572d446dfbeda2a6c61ccdae6dcbe8a0d72d2/src/main/java/meowmel/quantumhue/wiki/util/BlueprintPreviewRenderer.java#L209-L225) · [H-crab 的 1.12.2 版本](https://modrinth.com/mod/rts-building-build-from-above/version/eRqVRZNd)

## 排查范围

| 来源 | 核对方式与结果 |
| --- | --- |
| 作者视频与评论 | 查看作者的 22 条公开视频，在 9 条相关视频中核对可见的 69 条去重评论和回复，以画面文字、资源路径和蓝图字段反查源码。 |
| Git 历史依赖 | 检索 GTQT、作者和相关 fork 共 64 仓的公开分支、标签和 PR 引用，跨仓去重后为 35,086 个提交。核对 3,335 个不同版本的构建与依赖元数据，并读取 567 份历史 ZIP/JAR 和 71 份内容不同的嵌套归档，按 Forge 登记、类与资源核对身份。 |
| 整合包与测试产物 | 核对公开的 1.8.6、1.8.7、1.8.8 分发、1.8.8 仓库清单的 189 个 JAR、更早清单中额外的 24 个 JAR、当前候选客户端的 185 个 JAR，以及 17 项 GitHub 发布或 CI 下载。BetterQuesting 任务也使用 `requiredItems`，逐对象检查确认其含义是任务需求。 |

在以上可取得的文件中，尚未定位到独立 GuideQT 或含 SatisMC 建造器的源码或 JAR。作者公开网盘中可见的最高版本是 1.8.8。未公开的群内测试包和需要授权的制品库不在结论范围内。[整合包仓](https://github.com/GTQT/GT-QuantumTransition) · [作者分发目录](https://pan.quark.cn/s/bbdad8b57e9e)
