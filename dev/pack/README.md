# GTQT 1.9 候选的组装和联机验收

本候选使用 Minecraft 1.12.2、Forge 14.23.5.2860、Java 8。模组来自多个日期的作者开发制品。玩家配置、任务、资源和脚本取自 GTQT 1.8.8 公开整合包的固定提交。适用范围是新建世界；历史玩家存档迁移需单独验证。

## 本次验收

专服将五个核心模组与原包附属放在同一世界，存档记录了 198 个模组 ID。两个独立客户端先后用同一玩家身份进入维度 0，均收到区块 `(-8, 4)`，退出到主菜单。两次服务端都完成强制保存后正常停服。第二个专服进程读回首轮的唯一世界标记，133 条矿脉的名称和坐标全部保留。客户端两次均验证了 16 种 BOP 木材的 128 个物品栈。[双端记录](../../evidence/pack19-acceptance.json) · [矿脉存档对照](../../evidence/pack19-veins.json)

BetterQuesting 加载 2,375 项，按最终存档的注册表列出 304 项待处理。其中 256 项含缺失引用，另 48 项只含作者原任务中的占位物。207 项涉及普通任务条件，16 项查到的缺项只有图标。任务可含备选条件与矿辞，单项缺失不能直接用来判定整项任务阻断。FTB Quests 的 18 项任务中另列 2 项，13 张奖池表中另列 1 张。每行可查任务编号、名称、条件或奖励及缺项。[逐项中文清单](../../evidence/pack19-quests.md) · [完整 ID、元数据和备选条件](../../evidence/pack19-quests.json)

两端实际加载前的 8,236 份上游文件已按完整目录树核验。重启后联机还原了同一玩家 UUID 和出生区块。此轮覆盖新世界联机与保存，整条生存科技线、旧存档升级和 AE 网络内实际合成另需实测。

## 组装

准备 [1.8.8 公开清单](https://github.com/GTQT/GT-QuantumTransition/blob/3fd61bb3d9eacef642dd55eedb90bd2de216dec8/manifest.json) 对应的 JAR 缓存、当前候选采用的升级件及本地构建件。所有最终文件名、SHA-256 和运行端见 [候选锁](candidate.json)。组装脚本按内容匹配，允许缓存中的原文件名与分发文件名不同。两侧分别输出到新目录，配置和任务均从上游原件解压。

候选的 185 项中，177 项给出分发文件直链，其余 8 项给出构建来源或基础制品。源码构建会受 Gradle 写入的 ZIP 元数据影响；按哈希重组此组合时使用已验收的确切字节。使用自行重编的不同 JAR 时，应保留自己的文件锁和联机记录。

```powershell
git -C D:/GTQT-Pack archive -o D:/candidate-input/overrides.pinned.zip 3fd61bb3d9eacef642dd55eedb90bd2de216dec8 overrides
python -B dev/pack/assemble.py --overrides D:/candidate-input/overrides.pinned.zip --cache D:/candidate-input/mod-jars --cache D:/candidate-input/built-jars --output work/pack19-instance
```

七月 Core 和十月 GregTech 的基础生产名称转换见 [Pollution 兼容构建](../pollution/july-compat.md)。整包使用单独派生的 GregTech 和 GTFO，可用 JDK 17、ASM 9.5 重现。将下面的 JAR 路径换成相应基础组合的实际产物。

```powershell
$asm = 'D:/gradle-8.5/lib/asm-9.5.jar'
$asmTree = 'D:/gradle-8.5/lib/asm-tree-9.5.jar'
java -cp $asm dev/pack/PatchTicMaterial.java gregtech-1.9.0-october-srg.jar gregtech-1.9.0-october-pack.jar
java -cp "$asm;$asmTree" dev/pack/PatchBopWood.java gregtechfoodoption-gtqt-1.12.2-1.9.0.jar gregtechfoodoption-1.9.0-bop.jar
```

- GregTech 在合并已有匠魂材料属性时，保留原实现计算的合并数值，再写回已有属性。首次登记属性继续沿用匠魂的注册检查。Forestry 和 Extra Trees 的木材配方改从木板注册名和元数据生成稳定 ID。修复前的核心服存档重启后，客户端报告 837 条旧木材配方 ID 无法识别。
- GTFO 的 BOP 木材适配与十月 GT 的物品查找参数次序一致，使用 BOP 实际提供的冷杉栅栏。客户端验收核对 16 种木材的 128 个实物堆栈。
- DrTech 在物理专服登记滑翔翼、翅膀和抓钩的客户端方向消息编号。BogoSorter 只对确实存在完整版 Future MC 木桶类的实例登记该木桶，因而可以与 DrTech 提供的 Future MC 子集共存。[DrTech 与 BogoSorter 构建](drtech-october.md)
- GTMaid 与 VisualOres 按十月 GT 重新编译。VisualOres 使用新版矿脉注册入口和对应版本的 Xaero 地图。生产构建可分别运行 `manifest_addons.py gtmaid` 和 `manifest_addons.py visualores`，`--help` 列出原包模组目录、SteamTech 工具环境与构建缓存参数。[构建脚本](manifest_addons.py) · [锁定的上游与依赖](manifest-addon-sources.json)

## 从 1.8.8 到此候选的文件差异

原清单的 189 个文件中，170 个沿用原件，12 个替换，7 个原 JAR 未装入。另加按键绑定修补、ModelLoadLib、XaeroLib 三个文件，得到 185 个客户端 JAR。专服去掉 BetterChat 和 FancyMenu，剩 183 个。每个旧文件均记录 CurseForge 项目、文件号、哈希、实际选择和运行端。[189 项对照](../../evidence/pack19-manifest-audit.json)

| 原试装的问题 | 当前选择 | 玩家可见的影响 |
| --- | --- | --- |
| AE2 两个实现声明同一 ID | 使用 AE2 UEL 0.56.7，移除 rv6-stable-7 | 客户端与专服只注册一份 `appliedenergistics2` |
| BogoSorter、ModularUI 的两个版本诊断 | BogoSorter 1.6.2，加木桶类存在检查；ModularUI 3.1.5 | 整理背包可随包加载。DrTech 内嵌 Future MC 和原独立 JAR 同名，缺少的远古残骸会影响任务兑换 |
| DrTech、GTFO、GTQTCore、Pollution 的四个旧 GT 版本诊断 | 使用十月环境构建的 DrTech、七月 GTFO 与 Core 兼容件、已验收的 Pollution | 与七月 SteamTech 同服。各核心的实际制品以候选锁为准 |
| GTMaid、VisualOres 的两个旧 GT 版本诊断 | 针对十月版本实编，地图依赖随 VisualOres 更新 | 保留这两个附属的实际实现 |
| GCYM、Supercritical 的两个旧 GT 版本诊断 | 使用十月 GT 并入的大型机器、裂变堆等实现 | 独立模组的旧物品名、任务、工业多方块及燃料尚需逐条映射。GregTinker 还依赖独立 GCYM，旧专有工具特性存在缺口 |
| GTQTSpace、PrismPlan 的两个旧 GT 版本诊断 | 留待源码适配 | 航天与行星进度、旧 AE 多方块及相应任务受影响 |

这 12 项是历史混装启动时 Forge 给出的依赖诊断。与按原始文件比较得到的 12 个替换件分别统计，AE2 重复也单列。[12 条原始诊断和处置](manifest-dependency-audit.json) · [旧附属玩法逐项核对](legacy-addons.md) · [航天和大型 ME 设备的移植清单](manifest-porting.md)

## 仍影响游玩的脚本和配方

1.8.8 的 15 个 ZenScript 随原包原样载入。十月 GregTech 缺少旧脚本使用的 `mods.gregtech.recipe.RecipeMap` ZenScript 接口。专服对下列七个脚本报告执行失败。表中列的是受影响的改动范围，同一机器在 Java 或其他脚本中登记的配方需另查。

| 脚本 | 受影响的内容 |
| --- | --- |
| `enderio/conduit.zs`、`enderio/enderio.zs` | Ender IO 导管，以及使用 GT 机器制作 Ender IO 部件、设备的配方 |
| `TConstruct/Cast.zs` | 匠魂材料、铸件与 GT 压缩机、模压机的配方 |
| `IronChest.zs`、`StorageDrawers.zs` | 升级箱子、储物抽屉相关的 GT 加工配方 |
| `thaumcraft/thaumstic.zs` | 神秘相关部件在装配、切割、激光和流体固化设备上的配方 |
| `JeiSweep.zs` | 脚本引用客户端 `I18n`，专服执行失败，影响 JEI 整理 |

此外，`TConstruct/TConstruct.zs` 第 67 行引用的 `gtqtcore:misc` 无法解析。Groovy 报告 BOP 配方与既有登记冲突，涉及切割机、研磨机、装配机和电弧炉。脚本日志的错误行数含同一错误衍生的多条诊断，逐脚本计数见验收记录。

`JeiSweep.zs` 第 120、121 行在客户端使用 `removeAndHide` 移除探测器及其说明书。专服执行该脚本失败，联机同步仍报告 `theoneprobe:probe` 和 `theoneprobe:probenote` 两个配方 ID 在客户端缺失。处理这份脚本时需要将双端的配方移除与客户端的显示设置拆开验证。

Java 侧还有配方被拒绝。筛选机有 16 条配方给出 7 种输出，当前上限为 6。热力化学反应釜两次重复添加 `heat=15`。工业注魔有两条配方分别使用 9、10 种输入流体，当前上限为 8。提取机还有一条配方提供 2 个物品输出，当前上限为 1。独立 Pollution 环境的魔法聚变反应堆两条实机记录可供回归，完整候选仍需逐项实测这些工艺。[Pollution 专服实机记录](../../evidence/pollution-fusion-reactor.json)

## 验收方法

Windows 客户端验收使用 Python 3.11+、pywin32、JDK 8 和隔离的 Win32 桌面。Forge 客户端从回环地址连接专服，读取服务器下发的地形并核对玩家身份，再正常退出。脚本只复制模组和整包覆盖文件到临时实例。测试服使用已有的 EULA 授权，关闭外网监听与在线身份验证，用户名固定为 `Pack19Probe`。专服端核对玩家登录事件、玩家存档、世界种子、FML 模组清单和跨 JVM 保留的世界标记。两次启动都必须正常保存和停服。

```powershell
python -B dev/pack/verify.py --instance work/pack19-instance/server --client-instance work/pack19-instance/client --steam-env D:/GTSteam-1.12.2 --server-dir D:/Minecraft-Test/forge-112 --state work/pack19-acceptance --client-cache work/pack19-client-cache
```

`--boot-only` 只检查一次专服启动，产出的记录带有 `fullVerification=false`。完整验收使用两个独立的专服 JVM 和两个真实客户端 JVM。[旧附属的接口与缺失玩法](legacy-addons.md)
