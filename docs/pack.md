# 1.12.2 整包核验

## 打包前查重复模组

在协调仓根目录运行下面的命令，把路径换成要打包的实例 `mods` 目录。

```powershell
python -B tools/pack_check.py 'D:/Minecraft-Test/instance/mods'
```

检查器只读扫描 `mods/*.jar` 和 `mods/1.12.2/*.jar`。它从 JAR 根目录的 `mcmod.info` 读取多个 modid，支持数组和带 `modList` 的对象。若描述字段有旧模组常见的未转义换行，工具会提示元数据不规范，并继续使用可读的 ID。不同 JAR 中的相同 ID 会逐项列出文件名。

| 退出码 | 含义 |
| --- | --- |
| 0 | 已读取的元数据中未发现跨 JAR 重复。仍需检查输出里的 `INCOMPLETE` 条目。 |
| 1 | 已发现跨 JAR 重复的声明。有其他读取异常时也会一并列出。 |
| 2 | 路径无效、目录为空，或存在无法打开、读取的 JAR 且未发现重复。 |

Forge 也能从类注解注册模组。缺少 `mcmod.info` 的 JAR 可能正常加载。静态检查只读取 ZIP 目录及描述文件，不能验证所有 class 的完整性、`@Mod` 声明、coremod、依赖版本、Java 字节码和启动过程。打包候选还需在目标 Java 和加载器下实测。

## 1.8.8 清单与 1.9 候选

作者 1.8.8 清单锁定 189 个文件。实测原始输入，检查器退出 1。两个 JAR 均声明 `appliedenergistics2`。另有 3 个 JAR 没有根描述文件，5 个描述文件的字符串包含字面控制字符。Forge 14.23.5.2860 在原始清单的独立启动记录中也因这两个文件报出 `Duplicate Mods`，在建档前退出。[原始 manifest](https://github.com/GTQT/GT-QuantumTransition/blob/3fd61bb3d9eacef642dd55eedb90bd2de216dec8/manifest.json)

| 文件 | CurseForge 项目 / 文件 | SHA-256 |
| --- | --- | --- |
| `appliedenergistics2-rv6-stable-7.jar` | 223794 / 2747063 | `e7f7fbf6caaf6206dbd958fb8f9185f874a405289e62ae3e97209b455a89fb1a` |
| `ae2-uel-v0.56.7.jar` | 570458 / 6302098 | `dfca9f74cfebb4e79806ae77cd6bcedc30649be2b0e505e06d629386b0c3074e` |

另一次试验在 1.8.8 清单上换入 1.9 的 GregTech、SteamTech 构建件及配套依赖。该候选同样遇到 AE 重复。只在这份候选里移走 rv6 后，Forge 报告 12 项未满足的版本要求，包括旧 GTQT-Core 要求 GregTech ≥2.9.0-beta、旧 GCYM 要求 ≥2.9.0-188，以及 BogoSorter 和 ModularUI 的版本范围冲突。此候选未进入主世界。维护者的旧审计在 `legacy-build/distribution/legacy-real-forge-audit.json`，原始清单的崩溃记录在 `legacy-build/runtime/runs/source-lock-188-control/instance/crash-reports/`。

十月 GT 的联机候选保留 AE2 UEL 0.56.7，纳入七月 Core、兼容分支 Pollution、SteamTech 和 DrTech。可从锁重新组装客户端和专服，在新世界复跑首次加入、保存、关服及重启重连。原 189 项的每个取舍及 12 条 Forge 诊断均可独立查阅。[组装与验收入口](../dev/pack/README.md) · [189 个文件](../evidence/pack19-manifest-audit.json) · [12 条依赖诊断](../dev/pack/manifest-dependency-audit.json)

## AE 和太空模组的联调组合

| 组合 | 已核对的输入 | 纳入整包前要验证什么 |
| --- | --- | --- |
| GTQTSpace 1.8.7 | 公开源码使用 GTCEm 2.9.0-185、Core 1.8.5、SteamTech/GCYM/GTFO/Supercritical 1.8.4、AE2 UEL 0.56.6 和 ModularUI 2.5.0-rc4。作者发布页可取 1.8.7 JAR。 | 先复现历史运行环境。要进入 1.9 候选，还需确认兼容源码或制品，并实测依赖注册和维度加载。 |
| PrismPlan 1.9.0 | 作者仓库存有 GTCEm 2.9.0-190、AE2 v1.0.5-gtqt（ID `appliedenergistics2`）、AE2FC 2.7.10 和 NAE2 1.9.0。构建使用 ModularUI 3.0.7。 | 使用这四个实际依赖单独启动，验证 AE 网络和相关多方块。 |
| ApplyGray 1.0.0 | 主工程以 Java 25 为编译目标，使用 Cleanroom 0.5.14-alpha。它指定 GTCEm 1.9.0、AE2 Supergiant 1.1.0（ID `ae2`）和作者的 `structurelib-1.0.0.jar`。 | 使用独立的 Cleanroom/Java 25 实例。Supergiant 正式 JAR 可取。仍需取得匹配的 `meowmel.structurelib`，然后实编 ApplyGray，验证物品、网络和专服同步。 |

GTQTSpace 1.8.7 的正式文件 SHA-256 为 `b21025fa17dd7347534dec686771d2e238ab8fa3b54ccb4db12e43d9856bc3e1`。在核对的上游分支、发布和 CurseForge 文件中尚未找到 GTQTSpace 1.9。[构建依赖](https://github.com/GTQT/GTQTSpace/blob/0e3110f7b9801da60358c1ac6a1dcdb10821edeb/build.gradle#L134-L147) · [作者文件列表](https://www.curseforge.com/minecraft/mc-mods/gtqtspace/files/all)

PrismPlan 留存的 AE2 v1.0.5-gtqt JAR 的 SHA-256 为 `36ae14312ab08944c646bf31ee3d5612b7d011fa792db0153e8a7b3bd8d22ec0`。ApplyGray 对应的 Supergiant 1.1.0 正式文件为 `1f15fcda479f6b6a15e0640e0bf0f8a86e88c08c2bbd20e63b4145ea7e5efe26`，其中 3,108 个 AE 项目类均为 Java 25 字节码。[PrismPlan 留存依赖](https://github.com/GTQT/PrismPlan/tree/8dbed095e346ac421f263a1a95ffccbed859543d/libs) · [ApplyGray 依赖文件名](https://github.com/GTQT/ApplyGray/blob/413a9ddd7897f420dd0077604f4777fc3603f85e/gradle.properties#L28-L31) · [主代码编译目标](https://github.com/GTQT/ApplyGray/blob/413a9ddd7897f420dd0077604f4777fc3603f85e/build.gradle#L282-L285) · [StructureLib 的接口来源](https://github.com/GTQT/ApplyGray/blob/413a9ddd7897f420dd0077604f4777fc3603f85e/docs/AE2-GTIntegration-移植说明.md#L54-L66) · [Supergiant 正式文件](https://www.curseforge.com/minecraft/mc-mods/applied-energistics-2-supergiant/files/9342033)

合并候选时，先锁定一种 AE 实现和相匹配的附属，依次运行重复检查、目标专服建档与正常停服、客户端加入、网络存取和存档重启。把通过的模组哈希、加载器、Java 及配置写入同一份候选清单，再交给整合包仓库打包。
