# GTQT 1.9 新版整包候选

Minecraft 1.12.2、Forge 14.23.5.2860、Java 8。组装起点为 GTQT 组织仓的 `gtqt19` 开发基线，包括 GregTech、GTQTCore、SteamTech、QuantumHue、Pollution 和 GTQTGalaxy。开发锁保存当前 29 服 / 30 客的组合（含 Galacticraft Legacy 4.0.7、AsmodeusCore 1.0.2、GalaxySpace 2.2.0）；加入星组前的 25 服 / 26 客组合见 git 历史。[基线依赖锁](../workspace.lock.json)

## 候选结果

通过联机和保存重启的候选含 **145 个专服 JAR、175 个客户端 JAR**（在 141 / 171 的基础上追加 GTQTGalaxy 与三项太空依赖）。两次真实客户端均在主世界出生区保持 100 tick 后正常退出。重启前核对 89 份存档文件，世界登记 169 个 FML 模组 ID。客户端两次均未报告缺失的世界注册 ID。加入 GTQTGalaxy 组之前，141 / 171 候选另外比对过 29,424 个合成配方注册名，完全一致。[最终运行清单](../evidence/gtqt19-pack/runtime-lock.json) · [配方注册名对照](../evidence/gtqt19-pack/recipe-registry.json)

按 1.8.8 清单计，156 项使用原文件，10 项由开发基线中的新版提供，2 项采用上游替代件，21 项未纳入。BogoSorter 使用作者发布的 1.6.2，客户端配套安装 Key Binding Patch；RandomComplement 使用作者发布的 1.9.10。Future MC 使用原始独立 JAR。DrTech、BOP、匠魂和 Forestry 均未进入最终清单。GT 模块开关保持原包配置。[实际新增文件及分发来源](../evidence/gtqt19-pack/accepted-additions.json)

| 批次 | 专服 / 客户端 | 实际结果 |
| --- | --- | --- |
| 组织仓 DrTech | 25 / 26 为起点 | 两个源分支均未通过编译。 |
| 基础库、通用工具 | 39 / 40 → 58 / 59 | 两批分别通过建档、入服、保存和同档复登。 |
| 工业、魔法与 AE2 | 124 / 125 | 提前加入 Roughly Enough IDs 后通过。 |
| 工具、优化、上游替代件 | 139 / 169 | 完整复测通过，重启前后 30,960 个配方注册名相同。 |
| 世界生成、材料联动 | 153 / 183 → 147 / 177 → 146 / 176 | 分别定位匠魂、BOP 和 Forestry 问题。Forestry 组合虽能复登，配方注册名会改变。 |
| 剩余世界生成模组及官方覆盖文件 | **141 / 171** | 两端原样使用全部 8,236 个覆盖文件，通过两轮验收。 |
| 组织仓 GTQTGalaxy 与太空依赖 | **141 / 171 → 145 / 175** | 加入 GTQTGalaxy 1.9.0（`dd05e337`，客户端关闭 GalaxySpace 标题界面）与 Galacticraft Legacy 4.0.7 / AsmodeusCore 1.0.2 / GalaxySpace 2.2.0；通过建档、入服、保存重启和复登。 |

## 配方脚本和任务

15 个原始 ZenScript 中，专服有 9 个执行失败，客户端有 8 个。专服多出的 `JeiSweep.zs` 调用了客户端 `I18n`。两端的 Groovy 脚本均在 `postInit/BiomesOPlenty.groovy:279` 遇到缺失的蜂蜜流体，求 `fluid('honey') * 1000` 时抛出异常。受影响的配方需要单独适配。[逐脚本记录](../evidence/gtqt19-pack/gameplay-audit.json)

BetterQuesting 两次均加载 2,375 项任务、34 条任务线，存档中的任务 ID 集合与原包相同。实际注册表核查发现 460 项有缺失引用或原始占位提示，其中 49 项只有原包占位，22 项只涉及图标。FTB 两次均加载 18 项任务，3 项任务和 1 张奖池表有引用提示。玩家完成任务和领取奖励仍待实测。[逐项任务与奖池核查](../evidence/gtqt19-pack/gameplay-audit.json)

## 输入与验收

1.8.8 原始清单含 189 项。按 CurseForge 的项目与文件编号核对原件，再与新版双端的模组 ID 和 SHA-256 比较。一个 JAR 可以提供多个模组 ID。AE2 UEL 和原版 rv6 均注册 `appliedenergistics2`，扩展使用 UEL 的 API，因此每端只放 UEL。官方配置、脚本、任务与资源来自相同提交，8,236 个文件逐一匹配 Git blob。[原始清单](https://github.com/GTQT/GT-QuantumTransition/blob/3fd61bb3d9eacef642dd55eedb90bd2de216dec8/manifest.json) · [189 项对照](../evidence/gtqt19-pack/manifest-audit.json)

每批在独立实例中运行。Forge 专服在回环地址建档，真实客户端加入并收到主世界的出生区块。专服写入世界标记、执行 `save-all flush` 并正常退出。验证器核对存档文件，再用第二个专服和客户端进程复登，检查同一标记、玩家存档和 FML 注册清单。测试探针仅加入隔离客户端。运行记录分别列出建档失败和成功跑完两轮的批次。[逐批实测](../evidence/gtqt19-pack/batches.json)

## 重组已验收的双端候选

在协调仓根目录运行。将 `$baseline` 指向已经 `check-mods` 核验的新版双端目录，将缓存指向保存原件的目录。支持扁平缓存和按文件 ID 分目录的布局。`--output` 需要一个新的目录。

从原包仓库导出覆盖文件，再从协调仓运行组装和双端验证。组装器按文件内容校验原包配置，归档压缩参数可以不同。

```powershell
git -c core.autocrlf=false -C D:/GTQT-Pack archive --format=zip -o D:/pack-input/overrides-git.zip 3fd61bb3d9eacef642dd55eedb90bd2de216dec8 overrides
$baseline = 'work/gtqt19'
python -B dev/pack/stage_batch.py --base $baseline --rows evidence/gtqt19-pack/accepted-additions.json --cache D:/pack-input/cf-downloads --cache D:/pack-input/upstream --overrides D:/pack-input/overrides-git.zip --overrides-tree 960bc1791fd0857bb3b190c1cad88649874c36a3563ebcdb586eb3fc0aabe7a2 --output work/candidate-replay
python -B dev/pack/verify_batch.py --instance work/candidate-replay --runtime-lock evidence/gtqt19-pack/runtime-lock.json --label replay --steam-env D:/GTSteam-1.12.2 --client-cache D:/pack-input/forge-client-cache --server-dir D:/Minecraft-Test/forge-112
```

专服测试目录须有服主已接受的 EULA。客户端在 Windows 的独立桌面运行。测试中曾遇到回执序列化错误、探针过早卸载客户端世界导致的实体包异常。两次失败均有单独记录；修正验收器后用同一批输入从新世界重新验收。

## 已定位的不兼容

| 模组或组合 | 检查结果 |
| --- | --- |
| DrTech | 组织仓 `main` 的 `e530bc95` 与较新的 `cropQT` 分支 `83bf12af` 都实际执行了干净构建。唯一编译错误是 YOT 流体仓 `MetaTileEntityYotHatch.java:75` 调用了当前 GT 已移除的 `Textures.ME_INPUT_BUS`。未生成可入包的生产 JAR。[两分支实编](../evidence/gtqt19-pack/drtech-build.json) |
| GTQTSpace、GTMaid、PrismPlan | 原件要求 GregTech 2.8.x 或以上，基线向 Forge 注册 1.9.0。组织仓对应源码仍有版本约束。 |
| GCYM、Supercritical、GregTinker | 旧独立 GCYM、Supercritical 的版本要求排除基线。GregTinker 要求存在单独注册的 `gcym`。新版 GT 的内置实现与这些独立模组的注册名、任务引用须逐项对照。 |
| VisualOres | 旧发行件要求更高的 GT 版本号。组织仓源码引用 `gregtech.api.worldgen.vein.OreVeinHandler`，基线 JAR 提供的类位于 `gregtech.api.worldgen.bedrockOres`。 |
| RandomComplement 1.6.9 | 专服实际拒绝加载。它将已安装的 JEI 锁定为 4.29.7，基线 HEI 注册 4.32.0。 |
| 内容批缺少 Roughly Enough IDs | 方块数量到达 4096 时，Forge 在注册 HarvestCraft 方块期间退出。原始清单含 Roughly Enough IDs，测试将其提前与内容模组一同加载。 |
| 匠魂及其附属 | 153 服 / 183 客候选在专服注册阶段抛出 `TinkerAPIException`。LibNine 已登记铝的 `head` 属性，GregTech 的 `TiCModule.registerBlocks` 再次提交该属性。 |
| Biomes O’ Plenty | 去掉匠魂组后，147 服 / 177 客候选在专服配方注册阶段退出。GTFO 的 `BiomesOPlentyWoodRecipe.getDefaultEntries:37` 传入空木板，GT 的 `WoodTypeEntry.Builder.build:417` 抛出 `Planks cannot be empty`。 |
| Forestry、Extra Trees 及依赖项 | 146 服 / 176 客能建档和复登，但两次实际握手各有 837 条缺失的合成配方名。对比两次 33,534 项的注册表，重启后 837 个旧名消失、另增 837 个新名，涉及 Forestry 413 项和 Extra Trees 424 项。GT 木材联动在生成配方 ID 时加入了随机字符串。该组退出候选。[两次握手的完整差异](../evidence/gtqt19-pack/forestry-recipe-diff.json) |

### 匠魂恢复待办

本轮保留 `gregtech:tic_integration` 的默认值 `true`。候选暂缺匠魂本体，以及 Tinker Tool Leveling、Construct’s Armory、Tinkers’ JEI、PlusTiC、Tinkers’ Evolution 五个附属。GregTinker 另有独立 GCYM 前置缺口。

后续在组织仓 `GTQT/GregTech` 修复已有匠魂材料的属性合并。回归时保留 LibNine，验证铝的 `head` 属性只登记一次且合并后的数值符合预期，再用六件组合验证专服建档、客户端入服、保存重启和复登。[GregTech 材料合并入口](https://github.com/GTQT/GregTech/blob/748c944bc811f99c1d534c05c3ac1b9cbae634e4/src/main/java/gregtech/integration/tconstruct/materials/ToolMaterialRegistrar.java#L178)
