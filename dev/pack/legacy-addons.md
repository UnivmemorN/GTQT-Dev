# 旧附属在 1.9 候选中的玩法差异

以原 1.8.8 清单的四个正式 JAR 为输入，使用 JDK 17 `jdeps --multi-release base --ignore-missing-deps -verbose:class -filter:none` 提取类间引用，再与候选 JAR 的 `.class` 条目按完整包名取差集。下表只计不同的直接类引用。一个类存在时，其旧方法签名、机器注册名及配方仍需分别验证。

| 旧模组 | 对 1.9 类表的核对 | 玩家可见的差异 |
| --- | --- | --- |
| GTQTSpace 1.8.7 | 979 类中有 51 类直接引用旧 Core 的 23 类，共 107 对调用者与目标，23 个目标全部缺失。另缺旧喵呜 GT 的 4 个结构 API 类和 2 个无线能源仓相关的 `gtqt.common` 类。后两者在原 189 JAR 中均由 `gregtech-MeowmelMuku-1.12.2-2.9.0-188.jar` 提供。旧 JAR 自身要求 `gregtech@[2.8.7-beta,)`。GCYM 和 Supercritical 在旧构建依赖中出现，发布 JAR 里没有对其包的直接类引用。 | 原宇航、卫星、空间电梯、飞船及行星任务需要独立适配。作者公开 `master` 和未合并 PR #2 均标 1.8.7，GitHub 无 Release，CurseForge 最新发布为 1.8.7。[作者源码](https://github.com/GTQT/GTQTSpace/tree/0e3110f7b9801da60358c1ac6a1dcdb10821edeb) · [作者发行记录](https://www.curseforge.com/minecraft/mc-mods/gtqtspace/files/all) |
| GregTinker 1.8.0 | 98 个类，Forge 声明必需独立的 `gcym` 和 `tconstruct`。另缺少 `keqing.gtqtcore` 下的材料、矿辞前缀和元物品三个类，还缺原 GCYM 和 Pollution 各一个材料类。引用的 27 个 GT 类和 51 个 TiC/Mantle 类名都存在。公开源码 `40aba5b` 仍为 1.8.0。 | 十月 GT 实包已有 38 个 `gregtech/integration/tconstruct` 类，提供工具材料、浇铸和修饰。旧附属另有 `TraitArcane`、`TraitMageHand`、`TraitGravitation` 等独立特性，逐项等价性待验。[旧特性注册](https://github.com/GTQT/GregTinker_CEU/blob/40aba5ba5137ba5777acdc27dd5f3718c5be84d7/src/main/java/cn/gtcommunity/gregtinker/trait/GTinkerTraits.java) · [作者加入 GT 匠魂集成](https://github.com/GTQT/GregTech/commit/70f2f3a98ad1b6dc6b99c4a0847f276fe07145e1) |
| Gregicality Multiblocks 1.8.8 | 80 个类，164 个不同的 GT 目标类中缺 5 个，其中 4 个是旧结构 API，另一个是 `AdvanceMultiMapMultiblockController`。旧 JAR 要求 `gregtech@[2.9.0-188,)`。 | 作者已把 GCYM 并入 GregTech。十月 GT 实包有大型装配机、巨型电高炉等实现。旧 `gcym:*` 物品、旧机器 ID 和任务引用需要映射或调整。[作者合并](https://github.com/GTQT/GregTech/commit/469d74d3cbddfaad13ae9315ae9c16ecb578415c) |
| Supercritical 1.8.8 | 130 个类，168 个不同 GT 目标类中缺 4 个旧结构 API 类。旧 JAR 要求 `gregtech@[2.8.10-beta,)`。 | 十月 GT 有裂变控制器及独立的燃料、冷却剂和堆芯模拟；旧 `supercritical:*` 的机器、燃料棒、任务配方需单独核对。[作者核能模块](https://github.com/GTQT/GregTech/commit/58bcfbe52a26cb51c2b0cb591141c1a20c06d6a9) |

四个缺失的旧 GT 结构类是 `gregtech.api.pattern` 下的 `BlockPattern`、`FactoryBlockPattern`、`PatternMatchContext` 和 `TraceabilityPredicate`。十月 GT 生产 JAR 在 `mcmod.info` 中登记 `gregtech:1.9.0`。曾在此实包运行过的玩法不能自动满足对独立 `gcym`、`supercritical`、`gregtinker` modid 或旧类路径的要求。[历史构建依赖](https://github.com/GTQT/GTQTSpace/blob/0e3110f7b9801da60358c1ac6a1dcdb10821edeb/build.gradle#L137-L152)

## 复核原任务书

`quest_audit.py` 读取固定的 1.8.8 overrides ZIP 和候选服关服保存的 `level.dat`。BetterQuesting 只取 `config/betterquesting/DefaultQuests.json`，含 2,375 个唯一任务 ID；FTB Quests 读取 18 个任务和 13 张独立奖池表。脚本在结果中记录原件、实际存档和 36 个输入文件的哈希，可用 Python 3.11+ 复跑。

通过联机和重启验收的世界记录了 198 个 modid。审计表列出 304 个 BetterQuesting 任务、2 个 FTB 任务和 1 张 FTB 奖池表。BetterQuesting 中有 48 个只含原任务文件已有的占位，16 个只缺图标。[逐项中文表](../../evidence/pack19-quests.md) · [完整对象与判定条件](../../evidence/pack19-quests.json)

```powershell
python -m venv ../quest-audit-env
../quest-audit-env/Scripts/python -m pip install nbtlib==2.0.4
../quest-audit-env/Scripts/python -B dev/pack/quest_audit.py --overrides ../distribution/overrides.pinned.zip --level ../accepted-world/level.dat --output evidence/pack19-quests.json --markdown evidence/pack19-quests.md
```

报告对物品、方块和实体查 Forge 注册表及别名，对桶中流体和液体任务查 `DefaultFluidList`。`sourcePlaceholder` 保留作者写入任务文件时已经丢失的物品 ID 和原损伤值。`poolContainsMissingEntry` 表示可能抽到的奖池条目有缺口，该字段保留对应奖池 ID。`optionalRequirement` 是旧任务实现定义的可选目标。`onlyIconMissing` 区分单纯图片缺失。任务中的 OR 关系、矿物词典候选、损伤值和原件数均保留，任务能否在玩家进度中完成仍需结合这些条件判断。世界注册表不能证明数值型机器子 ID 与原版对应，也不能证明配方可达。

原任务书中有一项明确使用完整 Future MC 的材料。FTB 任务 `8d5d1bf4`《晶金座矿机兑换》以 1 个 `futuremc:ancient_debris` 作消耗式兑换条件。可在报告的 `futuremc` 区块核对实际注册的物品和方块，并与 DrTech 提供的内容逐项对照。[DrTech 的内嵌 Future MC](https://github.com/GTQT/DrTech/blob/e530bc957baa05437a3a6c17c6a7f5fe18cbe0bf/src/main/java/com/drppp/futuremc/FutureMCMain.java)

| 玩家会遇到的任务 | 原定义在候选中的表现 |
| --- | --- |
| BQ `848`《核裂变》 | 判定要求 `supercritical:mte`、损伤值 2。GregTech 已有裂变控制器，旧任务仍指向 Supercritical 注册的物品。 |
| BQ `356235260`《走向太空！》、`1221`《巨构工程3：太空电梯》 | 前者要求 9 个 `advancedrocketry:launchpad`，后者要求 `gtqtspace:space_elevator`。 |
| BQ `2113196928`《阿波罗计划 第二季》 | 使用月面维度 51，图标和空间站传送器奖励也指向宇航包。地点条件另标为需要验证维度提供者。 |
| BQ `755283567`《彩虹社》 | 原任务检查 PrismPlan 的大容量合成存储器和合成协处理器，包括 `prismplan:storage_crafting_65536k`。 |
| FTB `0597e591`《总是最好的》 | 原任务以钱兑换工具。奖励中包含缺失的 `gtqtcore:bending_cylinder` 和 `gtqtcore:small_bending_cylinder`。 |
| FTB 奖池 `261648fa`《晶金座矿物兑换》 | 有一项抽取条目 `gregtech:ore_gashydrate_0` 缺失。其他抽取条目按原奖池单独处理。 |
| BQ `283`《环氧树脂线》 | 查到的缺项只有图标 `gregtech:meta_wrap`。 |
| BQ `9`《大世界探索》 | 1.8.8 原定义本来就把 `thebetweenlands:swamp_dirt` 保存为占位物品；报告保留了原件数 8。 |
