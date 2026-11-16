# 历史开发与验收记录

2026-11-16 归档。以下结论、待办和命令按当时状态保留，包括尚未取得组织仓源码时的判断。现行开发入口见 [GTQT-Dev](../README.md)。

GTQT 未发行 1.9 系列的 Minecraft 1.12.2 开发协调仓。各模组在自己的仓库用原 Gradle Wrapper 开发和提交 PR。本仓保存源码提交、匹配的依赖、构建入口和专服验收结果。玩家包的配置、脚本、任务与发布由 [GT-QuantumTransition](https://github.com/GTQT/GT-QuantumTransition) 维护。

## 从已跑通的组合开始

需要 Git、Python 3.11+；下列命令在 Windows PowerShell 验证。先按 [SteamTech 工具链说明](https://github.com/UnivmemorN/GregTech-SteamTech/blob/6098eee246a59388d32f8c7112f1305143f7c1de/dev/legacy/README.md) 设置 JDK 8、16、17。第一次准备 Gradle、Minecraft 和 Forge 依赖时需要联网。

```powershell
git clone https://github.com/UnivmemorN/GTQT-Dev.git
cd GTQT-Dev
python -B tools/workspace.py check
python -B tools/workspace.py list
python -B tools/workspace.py checkout steamRunner
python -B tools/steam.py build --historical
```

源码检出落在 `work/src/<名称>`。上面的命令取得构建工具所在提交，并准备旧版源码基线。已有固定提交的 SteamTech 工作区也可以直接复用，例如 `python -B tools/steam.py build --historical --checkout D:/GTSteam-1.12.2 --offline`。从空缓存首次构建请省略 `--offline`。

如需验证 Forge 专服，先指定独立目录。新目录仅需服主已接受的 `eula.txt`，工具会在回环地址建一个新世界，保存并正常停服。以下命令中的路径按本机实际情况填写。

```powershell
python -B tools/steam.py verify --historical --server-dir D:/Minecraft-Test/forge-112
```

要取得作者当时使用的 Core 二进制，可执行以下命令。首次下载会核对文件大小和 SHA-256，第二条可在断网后再次核验。

```powershell
python -B tools/workspace.py fetch coreJuly
python -B tools/workspace.py fetch coreJuly --offline
```

## 已经验证到哪一步

### 十一月 GTQTCore 超导矩阵专服修复

**本地分支已修复（2026-11-15）。** GTQTCore 分支 `codex/fix-matrix-client-overlays` 从 `84bcf504` 建立，唯一提交 `12114207` 将两组分级贴图数组的初始化移至 `GTQTTextures`。不含 Pollution 的三次专服启动均通过矩阵注册。客户端已实测填充模块、供能模块 I–X 和蓄能模块 I–V 的物品图标与独立放置时的正面贴图，16 项全部通过。

下表记录修复前的对照。GTQTCore `96b6eb6` 在专服注册超导矩阵填充模块（`gtqtcore:power_supply.basic`，MTE 3300）时抛出 `NoSuchFieldError: SUPPLY_OVERLAYS`。Forge 剥离了客户端贴图字段，共用类的静态初始化器仍尝试写入。调用栈为 `MetaTileEntityPowerSupplyHatch.<clinit>:71` ← `GTQTMetaTileEntities.initialization:992`。

| 启动方式 | 实测结果 |
| --- | --- |
| 原仓 `runServer`，Forge 14.23.5.2847 | 在建档前崩溃。Gradle 仍返回成功；验收须检查游戏日志和崩溃报告。 |
| 生产 JAR，Forge 14.23.5.2860 专服 | 仅装 GTQTCore、喵呜版 GregTech、MixinBooter、CodeChickenLib、ModularUI、The One Probe 和 ModelLoadLib 即复现，无需安装 Pollution。 |
| 同一提交的原仓 `runClient`，Forge 14.23.5.2847 | 20 个模组完成加载，进入 GTQT 主菜单。运行时有 16 个 `MetaTileEntityPowerSupplyHatch` 实例，确认该类已完成初始化。 |

#### 专服待办

- [ ] **QuantumHue 网络包注册**。保留 QuantumHue 的 Forge 2847 开发专服在 `preInit` 加载客户端专用的 `HighlightPacket$ClientHandler` 时退出。验收时保留 QuantumHue，检查物理专服能通过网络包注册。
- [ ] **GTQTCore 电路部件取名**。移除 QuantumHue 的 Forge 2847 开发专服在 Forge 重建物品统计表时，由 `ItemCircuitComponent.getItemStackDisplayName` 调用了客户端 `I18n`。修复时覆盖基础部件和加工后部件的名称，复测专服统计表与客户端本地化。
- [ ] **GTQTCore 加热线圈生产映射**。移除 QuantumHue 的 Forge 2860 生产服在 GregTech 收集线圈时，因 Core 的 `BlockWireCoil$Builder$1.getName()` 缺失而抛出 `AbstractMethodError`。用重混淆后的发行 JAR 验收线圈注册。

三次启动均未到达 `Done`。本分支的专服建档、保存和重启验收待上述阻断处理后继续，届时用第二个服务端进程读回首个进程写入的存档标记。

### 十一月原仓客户端验收（2026-11-15）

GTQTCore `96b6eb6` 在原仓 `runClient` 的开发环境中能创建普通生存世界。隔离测试确认玩家收到主世界区块，重新启动客户端后能读取同一存档，再从游戏暂停菜单保存退出并回到主菜单。日志仍报告部分生物机器贴图、时空材料模型及音效加载失败。

同一运行时加入 Pollution `9ed70ed` 及其魔法前置，客户端在注册白雏菊配方（`BotaniaRecipes.flower:88`）时抛出 `NoSuchFieldError: BACTERIAL_VAT_RECIPES`，无法进入主菜单。十一月 Core 已移除旧培养缸配方表；原样编译 Pollution 对当前 Core 也会报同一字段缺失。完整历史 Core `d188744e` 能编译原作者的 Pollution 源码；将该产物放回完整十一月 Core 的开发客户端，仍在同一行崩溃。该组合和下表中已验收的七月 Core 兼容组合分别记录。

### 已验收组合

| 组合 | 构建 | 专服与已知差距 |
| --- | --- | --- |
| **1.9 可联机整包候选 `pack19Candidate`** | 十月喵呜 GT、七月 Core、Pollution 兼容件、SteamTech、DrTech 共服。专服 183 个 JAR，客户端 185 个。 | Forge 2860 已实测建档、首次加入、保存关服、同一世界重启和真实客户端再次进入。生存进度仍有脚本、航天、ME 设备和旧任务缺口。[组装与测试](../dev/pack/README.md) · [逐项任务清单](../evidence/pack19-quests.md) · [双端实录](../evidence/pack19-acceptance.json) |
| SteamTech 基线 + 八月喵呜版 GTCEu | 离线清理重建通过。SteamTech 使用作者提交 `2ce5e1e`。紧接着的 `ccbb394` 有两处蒸发池 API 不匹配。 | Java 8 / Forge 2860，新世界保存了 `gregtech` 和 `gtsteam`。[专服实录](../evidence/steam-server.json) |
| DrTech + SteamTech | DrTech 的七月、八月 GT 组合均构建成功；八月用于共服。 | 世界保存了 24 个模组 ID。橡胶草提取、作物种子反射登记及部分 Binnie、无人机平台配方有注册错误或警告。[构建与共服复现](../dev/drtech/README.md) |
| 七月 Pollution + 七月 Core 1.9.0 | 作者同批源码和依赖可离线重建。 | 补齐 ModelLoadLib 后，Core 在专服注册物品时加载客户端 `IBakedModel` 并崩溃。单换八月 GT 会更早缺少 `MaterialIconType.oreLean`。[两次启动证据](../dev/pollution/README.md) |
| 当前锁定的 Pollution + 七月 Core | 换到十月 GT 后，剩下的四条编译诊断都指向 `GTQTMaterials.Sunnarium`。 | 取得含该字段的 Core，才能继续验证这条组合。[具体调用和复现命令](../dev/pollution/README.md) |
| Pollution 兼容分支 + 修补的七月 Core + 十月 GT | 当前 Pollution 的独立分支可以从源代码构建。 | Forge 2860 专服已验证 Sunnarium 唯一注册、工业注魔矩阵 9 张配方、双并行和断魔恢复。原生祭坛与工业矩阵均从 9 份铀-235 粉起步，使用 LV 压缩机实际产出的块制得魔法聚变反应堆，保存重启后各再制一台。[复跑兼容组合](../dev/pollution/july-compat.md) |
| Space、PrismPlan 和 ApplyGray | 各用单独组合。Space 的公开版本锁到 1.8.7，PrismPlan 使用旧 AE，ApplyGray 的主代码和 Supergiant 需要 Java 25。 | ApplyGray 待取得作者的 StructureLib。Space 和 PrismPlan 的旧结构、网络与任务引用已逐项核对。[配套依赖](pack.md) · [待移植玩法](../dev/pack/manifest-porting.md) |

核心发现来自 [Pollution 的七月依赖目录](https://github.com/GTQT/Pollution/tree/d1611ce5dec0eac71c2d68cc86975db86c2e3112/libs)。其中的 Core 自报 1.9.0，主类是 `meowmel.gtqtcore.GTQTCore`。公开 Core 仓的固定提交仍为 1.8.9，主类在 `keqing.gtqtcore`。目前可以基于七月二进制开发下游；维护 1.9 Core 自身仍需对应源码。[公开 Core 源码](https://github.com/GTQT/GTQT-Core/tree/7ab5b236c4839b84de5a65d4b56b5655732740d1)

对 GTQT 组织和 MeowmelMuku 账号下 36 个公开仓库、59 个公开分支的历史按精确路径 `libs/gtqtcore-1.9.0.jar` 查询，只找到 Pollution 在七月加入、八月删除的同一份文件。其他文件名、其他账号和非公开分发仍可能提供更新版本。[删除提交](https://github.com/GTQT/Pollution/commit/b3fc7c626b9ba3e776e2b079f816dd7bb73f2350)

## 仓库与打包分工

- [workspace.lock.json](../evidence/historical-workspace.lock.json) 记录各检出提交、关键跨模组制品及其下载哈希。各组合另行锁定运行依赖；每次专服记录包含实际入服 JAR 的指纹。上游构建时间戳可使重编后的 JAR 哈希变化。
- 作者演示的早期 GuideQT Wiki 已在 QuantumHue 历史源码中定位。SatisMC 已取得作者蓝图样本与预览读取器，独立建造器仍缺源码或 JAR。[视频、源码与整包验证](guide-satis.md)
- GTFO、ModelLoadLib 已纳入依赖管理。GCYM、Supercritical、GTTopAddition、BestQuestings、GregTinker、GTMaid、VisualOres 等可由历史包回溯版本；是否进入 1.9 候选按实际使用它们的模组和脚本逐项确认。[历史模组列表](https://github.com/GTQT/GT-QuantumTransition/blob/3fd61bb3d9eacef642dd55eedb90bd2de216dec8/modlist.html)
- 修改上游 API 时，在对应 fork 开分支，用候选 JAR 跑受影响的下游构建及专服。上游合入后更新本仓锁和验收记录，再由整合包仓锁定实际发布文件。各组合使用独立的 `mods`、世界和配置；Java 25 的 Cleanroom 组合单独运行。
- 整包候选先运行 `python -B tools/pack_check.py <实例的mods目录>`，再运行对应专服与客户端。联机、原始任务引用和机器实作采用独立记录。可从存档注册名查出缺失部件，生存制作与多方块加工则需要在相应机器上复测。[整包组装和双端验收](../dev/pack/README.md) · [Pollution 既有实机测试](../dev/pollution/july-compat.md)

当前 Pollution 的开发可以使用 `pollutionJulyCompat`。取得作者新版 Core 后，再以 `pollutionCurrent` 验证原始组合。SteamTech 与 DrTech 使用各自已通过联调的八月环境。
