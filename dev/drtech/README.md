# DrTech 1.12.2 构建

DrTech 的源码提交为 `e530bc957baa05437a3a6c17c6a7f5fe18cbe0bf`。其产物自报 `drtech 1.8.9`，同一 JAR 另注册 `futuremc 1.0.0`，并要求 GregTech ≥1.9.0。将这个 JAR 纳入整包时，两项 modid 都要参与冲突检查。[DrTech 源码](https://github.com/GTQT/DrTech/tree/e530bc957baa05437a3a6c17c6a7f5fe18cbe0bf)

## 在 Windows PowerShell 复跑

在协调仓根目录执行。示例将源码、环境和缓存放到相邻目录。需要 Git、Python 3.11+ 和 Azul JDK 8、17。将两个 JDK 放在 SteamTech 环境的 `.legacy-dev/jdks/java8`、`.legacy-dev/jdks/java17`，或设置 `GTSTEAM_JAVA8`、`GTSTEAM_JAVA17`。已有这些检出时可直接使用其路径。[SteamTech 环境及 JDK 来源](https://github.com/UnivmemorN/GregTech-SteamTech/blob/6098eee246a59388d32f8c7112f1305143f7c1de/dev/legacy/README.md)

```powershell
git clone https://github.com/GTQT/DrTech.git ../GTQT-DrTech-1.12.2
git -C ../GTQT-DrTech-1.12.2 checkout --detach e530bc957baa05437a3a6c17c6a7f5fe18cbe0bf
git clone -b codex/legacy-dev-env https://github.com/UnivmemorN/GregTech-SteamTech.git ../GTSteam-1.12.2
git -C ../GTSteam-1.12.2 checkout --detach 6098eee246a59388d32f8c7112f1305143f7c1de
$inputs = @('--source', '../GTQT-DrTech-1.12.2', '--steam-env', '../GTSteam-1.12.2', '--state', '../.drtech-dev')
python -B dev/drtech/build.py @inputs build
python -B dev/drtech/build.py @inputs --offline --clean build
```

第一次运行按 SHA-256 准备上游声明的两个本地依赖、RFG 1.4.0 官方插件与 javac 插件，再启动上游 Gradle 8.5。Forge 2847 userdev 和 MCP stable_39 的准备脚本来自固定提交的 SteamTech 环境。可通过 `--gradle-home` 指定现有缓存。已有 RFG 官方下载文件时可使用 `--rfg-seed` 指向含两个 JAR 的文件夹。原始环境中的 RFG 插件标记未能从上游配置的仓库解析，协调脚本在本地生成其 Maven 描述文件。[RFG 官方发布](https://github.com/GTNewHorizons/RetroFuturaGradle/releases/tag/1.4.0)

| 编译依赖 | 已验证来源 | SHA-256 |
| --- | --- | --- |
| gregtech 1.9.0 | [Pollution 2026-07-27 历史依赖](https://github.com/GTQT/Pollution/blob/d1611ce5dec0eac71c2d68cc86975db86c2e3112/libs/gregtech-gtqt-1.12.2-1.9.0.jar) | `b5b190f16858b54560cfac4e3d3c0f796d45dd460c119bb62638ea015533696e` |
| gregtechfoodoption 1.9.0 | [同提交的 GTFO](https://github.com/GTQT/Pollution/blob/d1611ce5dec0eac71c2d68cc86975db86c2e3112/libs/gregtechfoodoption-gtqt-1.12.2-1.9.0.jar) | `f8521a873e5316aaa7d400ab84d532f62cf59d35fb3c0de3af76572a19d66baa` |
| modelloader 1.0.0 | [DrTech 自带的 ModelLoadLib](https://github.com/GTQT/DrTech/blob/e530bc957baa05437a3a6c17c6a7f5fe18cbe0bf/libs/modelloader-1.0.0.jar) | `ca0c44d331b19618181854119220092f5b0188203d1833da95e39d16ce8ad16f` |

## 验收边界

构建取用根目录 [workspace.lock.json](../../workspace.lock.json) 的源码提交和所选组合的编译依赖。上游 `build` 通过了 Java 编译、资源处理与 `reobfJar`。生产文件为源码目录的 `build/libs/drtech-1.8.9.jar`，主类字节码版本为 52（Java 8）。协调脚本把提交、组合、输入摘要及成品哈希写入 `build/drtech-profile.json`。同一检出用于共服验收时，脚本会核对这份记录、当前依赖与传入的生产 JAR。上游 `test` 显示 `NO-SOURCE`。专服使用下述八月共用基线，DrTech 与 Pollution 的共存及机器行为仍待验证。

2026-11-12 使用已有 Gradle 缓存运行协调脚本 `--offline --clean build`，耗时 86 秒，执行 24 个任务。验收产物 SHA-256 为 `354b4b27a668600fd928422b45d8a7320cc35c3d62bfa1a56ed5adee734504a0`。此前普通构建生成的 JAR 哈希不同。入包时应记录所选文件的实际哈希，重新构建后脚本会输出新哈希。

同日用独立 worktree 将 GregTech 换成 SteamTech 锁定的八月版本，保留同一份 GTFO，也通过上游完整 `build`（114 秒）。要复跑这个共用编译基线，请把 `--source` 指向另一份固定提交的 DrTech 检出，运行时增加 `--steam-gregtech`。两种模式均会检查现有 `libs` 文件的哈希。[八月 GregTech JAR](https://github.com/GTQT/VisualOres-Meowmel/blob/a9f5e8e3b83756146796c83bbe39171d26d2a375/libs/gregtech-gtqt-1.12.2-1.9.0.jar)

另行测试的十月 GregTech JAR 同样标为 1.9.0，但编译上游 DrTech 时在 `MetaTileEntityYotHatch.java:75` 找不到 `Textures.ME_INPUT_BUS`。替换 GregTech 基线时请复跑完整构建。[调用位置](https://github.com/GTQT/DrTech/blob/e530bc957baa05437a3a6c17c6a7f5fe18cbe0bf/src/main/java/com/drppp/drtech/common/metaTileEntities/muti/mutipart/MetaTileEntityYotHatch.java#L71-L76) [十月 GregTech JAR](https://github.com/GTQT/QuantumHue-Visualizer/blob/72e08b4f1b3d64748ca3bbf3e09bf133de0f8405/libs/gregtech-gtqt-1.12.2-1.9.0.jar)

## 与 SteamTech 共服

2026-11-12 在仅监听回环地址的 Java 8 / Forge 14.23.5.2860 专服上，使用八月 GregTech 生产版、同基线编译的 DrTech 和 SteamTech，连续两次完成启动、新建世界、保存和正常停服。新世界 `level.dat` 的 FML ModList 实录 24 项，其中含 `gregtech`、`gtsteam`、`drtech`、`futuremc`、`gregtechfoodoption`、`modelloader`。验收读取了存档中的 ID 与版本。用于验收的所有 JAR 的 SHA-256 和完整模组清单见[此次结果](august-server.json)。

复跑前先按 SteamTech 环境说明构建并验证基础专服，以准备 GregTech 生产 JAR。下例使用另一份 worktree 放置八月编译依赖。两个构建脚本会核对源码与工具仓的提交，并检查索引和工作区中的已跟踪文件改动。请将 `$serverDir` 指向已接受 EULA 的空闲专用测试目录。可以使用仅含 `eula.txt` 的目录，也可以使用已有 `server.properties` 的测试服。目录名及白名单内容可自定。省略 `--server-dir` 时，脚本读取 SteamTech 环境 `.legacy-dev/settings.json` 的 `server_dir`。

```powershell
git -C ../GTQT-DrTech-1.12.2 worktree add --detach ../GTQT-DrTech-August e530bc957baa05437a3a6c17c6a7f5fe18cbe0bf
python -B dev/drtech/build.py --source ../GTQT-DrTech-August --steam-env ../GTSteam-1.12.2 --state ../.drtech-dev --steam-gregtech build
$serverDir = 'D:/Minecraft-Test/forge-112'
python -B dev/drtech/server.py --steam-env ../GTSteam-1.12.2 --drtech-source ../GTQT-DrTech-August --drtech ../GTQT-DrTech-August/build/libs/drtech-1.8.9.jar --support-cache ../.drtech-dev/server-support --results-root ../.drtech-dev/server-checks --server-dir $serverDir
```

脚本自动核对 Forestry、Binnie's Mods、BdLib、Gendustry 四个支持 JAR，并复用 SteamTech 已有的五个基础依赖。缺少 Forestry 的试运行在 DrTech 加载工业蜂箱时找不到 `IBeeHousing`。装入 Forestry 而缺少 Binnie 时，GregTech 的蜜蜂集成调用 `getExtraBeesComb` 失败。联调使用独立模组目录和新世界，复用已有排他锁、备份与恢复逻辑。每次结果目录包含控制台日志、世界及原隔离服的恢复检查。

实际启动同时暴露了以下待修行为，均保留上游实现。

| 功能 | 共服日志与源码 |
| --- | --- |
| 橡胶草提取 | 16 个橡胶草产 1 个天然橡胶团和 8 个菊粉。提取机配方表最多接受一个物品输出，注册被拒绝。[MachineRecipes.java](https://github.com/GTQT/DrTech/blob/e530bc957baa05437a3a6c17c6a7f5fe18cbe0bf/src/main/java/com/drppp/drtech/loaders/recipes/MachineRecipes.java#L332-L338) |
| 作物登记 | 对 `BlockCrops.getSeed()` 的反射查找失败 34 次。该路径返回空值并跳过种子登记。源码另有单独登记的特殊作物。[DrtechUtils.java](https://github.com/GTQT/DrTech/blob/e530bc957baa05437a3a6c17c6a7f5fe18cbe0bf/src/main/java/com/drppp/drtech/api/utils/DrtechUtils.java#L39-L80) |
| 配方注册警告 | `drone_pad` 合成键重复。Binnie 集成有三条配方查找 `gregtech:machine` 的 1611／1629 得到空物品，另有三条熔炉配方重复。[CraftingRecipes.java](https://github.com/GTQT/DrTech/blob/e530bc957baa05437a3a6c17c6a7f5fe18cbe0bf/src/main/java/com/drppp/drtech/loaders/recipes/CraftingRecipes.java#L43) [BinneRecipes.java](https://github.com/GTQT/DrTech/blob/e530bc957baa05437a3a6c17c6a7f5fe18cbe0bf/src/main/java/com/drppp/drtech/loaders/recipes/misc/BinneRecipes.java#L30-L175) |
