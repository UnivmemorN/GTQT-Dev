# 从 1.8.8 清单迁移的玩法与构建入口

## GTQTSpace

原包的 `gtqtspace-1.8.7.jar`（SHA-256 `b21025fa17dd7347534dec686771d2e238ab8fa3b54ccb4db12e43d9856bc3e1`）同时含 GTQTSpace、Advanced Rocketry 和 LibVulpes 的实现。以下内容在旧 JAR 的机器类、配方加载器和语言文件中都有对应入口。本候选没有装载该 JAR。

| 玩法 | 移植和验收的具体对象 |
| --- | --- |
| 太空电梯 | 控制器、输送与接收仓配合采矿、抽采和装配模块。原方的电梯仓使用旧 Core 的电路与超导材料，矿机和钻机也引用旧 Core 机器。需重新确认部件的实物 ID、仓间传输及加工产物。[电梯配方注册](https://github.com/GTQT/GTQTSpace/blob/0e3110f7b9801da60358c1ac6a1dcdb10821edeb/src/main/java/meowmel/gtqtspace/loaders/recipes/hanlder/SpaceElevatorLoader.java) |
| 小行星与空间站 | 小行星系统有独立控制器、搜索、解析及钻取装置。船坞有管理器、造船厂及船坞单元。应分别验证玩家能完成目标选择、开采和造船。[小行星设备](https://github.com/GTQT/GTQTSpace/tree/0e3110f7b9801da60358c1ac6a1dcdb10821edeb/src/main/java/meowmel/gtqtspace/common/metatileentities/multiblock/standard/SpaceStation/AsteroidSystem) · [船坞设备](https://github.com/GTQT/GTQTSpace/tree/0e3110f7b9801da60358c1ac6a1dcdb10821edeb/src/main/java/meowmel/gtqtspace/common/metatileentities/multiblock/standard/SpaceStation/SpaceDockSystem) |
| 航天配方 | 旧 JAR 提供火箭与卫星配方、卫星装配机配方和二锂工艺。恢复时还需验证材料前置、控制器和相应任务的领取条件。[航天配方](https://github.com/GTQT/GTQTSpace/tree/0e3110f7b9801da60358c1ac6a1dcdb10821edeb/src/main/java/meowmel/gtqtspace/loaders/recipes/advancedRocket) · [卫星装配](https://github.com/GTQT/GTQTSpace/blob/0e3110f7b9801da60358c1ac6a1dcdb10821edeb/src/main/java/meowmel/gtqtspace/loaders/recipes/machine/GTQTSSatelliteAssembler.java) |

## PrismPlan

旧包 `prismplan-1.8.5.jar`（SHA-256 `365d97c6222526ed67efc57ffc2f4003ccf0633709da9da3091847e07be12552`）带有以下设备及配方。候选中运行的 AE2 可提供自己的终端、存储和合成，这些 PrismPlan 专用设备和渐进配方仍有缺口。

| 玩法 | 移植和验收的具体对象 |
| --- | --- |
| 大型 ME 存储 | 存储单元控制器、存储仓、储能单元和网络存储仓与 ME 网络协作；原包还提供高性能晶格存储矩阵。应验证物品写入、断网重连及读档后重读。[存储系统](https://github.com/GTQT/PrismPlan/tree/8dbed095e346ac421f263a1a95ffccbed859543d/src/main/java/meowmel/prismplan/common/metatileentities/multi/multiblock/estorage) |
| 多方块合成计算 | 计算单元控制器用网络计算仓口、计算单元仓、线程单元和并行单元参与 AE 合成。应验证提交任务、分配线程与合成交付。[计算系统](https://github.com/GTQT/PrismPlan/tree/8dbed095e346ac421f263a1a95ffccbed859543d/src/main/java/meowmel/prismplan/common/metatileentities/multi/multiblock/ecalculator) |
| 电路与 AE 扩展配方 | 并行电路基板、福鲁伊克斯逻辑部件，以及存储元件、NAE2、Lazy AE2 等配方按各自开关载入。应分别验证默认开关及替代配方的生存入口。[电路路线](https://github.com/GTQT/PrismPlan/blob/8dbed095e346ac421f263a1a95ffccbed859543d/src/main/java/meowmel/prismplan/loaders/recipes/CircuitChain.java) · [装载开关](https://github.com/GTQT/PrismPlan/blob/8dbed095e346ac421f263a1a95ffccbed859543d/src/main/java/meowmel/prismplan/loaders/recipes/PrismPlanRecipes.java) |

以作者 PrismPlan 提交 `8dbed09` 配十月 GT、ModularUI 3.1.5 以及项目自带的 AE2 `v1.0.5-gtqt`、AE2FC 2.7.10、NAE2 1.9.0 实编，javac 报出 41 处诊断。其中旧结构构造 API 和 `createStructurePattern` 需要迁移，`OPTICAL_PIPES` 已从数组变为映射；计算网络使用的 `MetaTileEntityHolder` 与 `IGridHost`、`MetaTileEntity.getProxy()` 和 `gridChanged` 也需要适配。生产源码中未搜到对 `keqing.gtqtcore` 或 `meowmel.gtqtcore` 的直接引用。可先迁移 GT 结构与 AE 网络接口，再分别试验上表两类控制器。[作者源码](https://github.com/GTQT/PrismPlan/tree/8dbed095e346ac421f263a1a95ffccbed859543d)

## 已恢复的 GTMaid 和 VisualOres

`manifest_addons.py` 校验固定提交的源码 ZIP、构建模板和每个依赖 JAR 的 SHA-256，应用同目录中的对应补丁后执行 RFG clean build。GTMaid 保留女仆前置，并将 GT 依赖与十月版对齐。VisualOres 对接十月 GT 的矿床注册与旧存档的矿名查找，使用 XaeroLib 1.1.0、Xaero's Minimap 25.3.13 和 World Map 1.40.16 三件套。锁定的原件和构建依赖见 [manifest-addon-sources.json](manifest-addon-sources.json)。

```powershell
python -B dev/pack/manifest_addons.py gtmaid --work ../build-gtmaid --cache ../addon-archives --mods ../original-1.8.8/mods --steam-env ../GTSteam-1.12.2 --rfg-maven ../rfg-1.4.0-maven
python -B dev/pack/manifest_addons.py visualores --work ../build-visualores --cache ../addon-archives --mods ../original-1.8.8/mods --steam-env ../GTSteam-1.12.2 --rfg-maven ../rfg-1.4.0-maven
```

两个 `--work` 参数均指向新的构建目录。`--steam-env` 指向已准备好的 1.12.2 开发环境，`--rfg-maven` 使用 `dev/drtech/build.py` 已准备的 RFG 1.4.0 插件仓库。发布时按候选文件锁校验最终 JAR，独立重编时还可逐项核对解压后的条目，以区分 ZIP 时间戳与内容差异。

## 复核 VisualOres 矿脉存档

`verify.py` 分别在创建世界的专服和重载该世界的专服退出后保存主世界 `data/visualores.dat`。使用与任务审计相同的 Python 3.11+、nbtlib 2.0.4 环境，传入该次验收的结果目录即可复查。

```powershell
python -B dev/pack/vein_audit.py --run ../checks/<run-id> --output ../checks/vein-comparison.json
```

程序先核对双 JVM 验收回执与两份 `level.dat` 的哈希，再解析每个 48 × 48 网格内的矿脉名称和坐标。空主世界索引、重复矿脉、坐标落在错误网格及重启丢失旧记录都会导致失败；重启后新发现的矿脉另行计数。报告保存原文件哈希、规范排序后的全量记录哈希、各矿种计数与坐标样例。
