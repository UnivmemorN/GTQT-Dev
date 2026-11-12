# GTQT-Dev

GTQT 未发行 1.9 系列的 Minecraft 1.12.2 开发协调仓。各模组在自己的仓库用原 Gradle Wrapper 开发和提交 PR。本仓保存源码提交、匹配的依赖、构建入口和专服验收结果。玩家包的配置、脚本、任务与发布由 [GT-QuantumTransition](https://github.com/GTQT/GT-QuantumTransition) 维护。

## 从已跑通的组合开始

需要 Git、Python 3.11+；下列命令在 Windows PowerShell 验证。先按 [SteamTech 工具链说明](https://github.com/UnivmemorN/GregTech-SteamTech/blob/6098eee246a59388d32f8c7112f1305143f7c1de/dev/legacy/README.md) 设置 JDK 8、16、17。第一次准备 Gradle、Minecraft 和 Forge 依赖时需要联网。

```powershell
git clone https://github.com/UnivmemorN/GTQT-Dev.git
cd GTQT-Dev
python -B tools/workspace.py check
python -B tools/workspace.py list
python -B tools/workspace.py checkout steamRunner
python -B tools/steam.py build
```

源码检出落在 `work/src/<名称>`。上面的命令取得构建工具所在提交，并准备旧版源码基线。已有固定提交的 SteamTech 工作区也可以直接复用，例如 `python -B tools/steam.py build --checkout D:/GTSteam-1.12.2 --offline`。从空缓存首次构建请省略 `--offline`。

如需验证 Forge 专服，先指定独立目录。新目录仅需服主已接受的 `eula.txt`，工具会在回环地址建一个新世界，保存并正常停服。以下命令中的路径按本机实际情况填写。

```powershell
python -B tools/steam.py verify --server-dir D:/Minecraft-Test/forge-112
```

要取得作者当时使用的 Core 二进制，可执行以下命令。首次下载会核对文件大小和 SHA-256，第二条可在断网后再次核验。

```powershell
python -B tools/workspace.py fetch coreJuly
python -B tools/workspace.py fetch coreJuly --offline
```

## 已经验证到哪一步

| 组合 | 构建 | 专服与已知差距 |
| --- | --- | --- |
| SteamTech 基线 + 八月喵呜版 GTCEu | 离线清理重建通过。SteamTech 使用作者提交 `2ce5e1e`。紧接着的 `ccbb394` 有两处蒸发池 API 不匹配。 | Java 8 / Forge 2860，新世界保存了 `gregtech` 和 `gtsteam`。[专服实录](evidence/steam-server.json) |
| DrTech + SteamTech | DrTech 的七月、八月 GT 组合均构建成功；八月用于共服。 | 世界保存了 24 个模组 ID。橡胶草提取、作物种子反射登记及部分 Binnie、无人机平台配方有注册错误或警告。[构建与共服复现](dev/drtech/README.md) |
| 七月 Pollution + 七月 Core 1.9.0 | 作者同批源码和依赖可离线重建。 | 补齐 ModelLoadLib 后，Core 在专服注册物品时加载客户端 `IBakedModel` 并崩溃。单换八月 GT 会更早缺少 `MaterialIconType.oreLean`。[两次启动证据](dev/pollution/README.md) |
| 当前锁定的 Pollution + 七月 Core | 换到十月 GT 后，剩下的四条编译诊断都指向 `GTQTMaterials.Sunnarium`。 | 取得含该字段的 Core，才能继续验证这条组合。[具体调用和复现命令](dev/pollution/README.md) |
| Pollution 兼容分支 + 修补的七月 Core + 十月 GT | 当前 Pollution 的独立分支可以从源代码构建。 | Forge 2860 专服已验证 Sunnarium 唯一注册、工业注魔矩阵 9 张配方、双并行和断魔恢复。魔法聚变反应堆可在原生祭坛及工业矩阵中各制得一台，保存重启后均可再次出货。[复跑兼容组合](dev/pollution/july-compat.md) |
| Space、PrismPlan、ApplyGray 和整包 | 各用单独组合。Space 的公开版本锁到 1.8.7，PrismPlan 使用旧 AE，ApplyGray 的主代码和 Supergiant 需要 Java 25。 | ApplyGray 待取得作者的 StructureLib。1.8.8 的 189 文件清单在历史和本次检查中都发现两个 AE JAR 注册相同 ID。[配套依赖与整包预检](docs/pack.md) |

核心发现来自 [Pollution 的七月依赖目录](https://github.com/GTQT/Pollution/tree/d1611ce5dec0eac71c2d68cc86975db86c2e3112/libs)。其中的 Core 自报 1.9.0，主类是 `meowmel.gtqtcore.GTQTCore`。公开 Core 仓的固定提交仍为 1.8.9，主类在 `keqing.gtqtcore`。目前可以基于七月二进制开发下游；维护 1.9 Core 自身仍需对应源码。[公开 Core 源码](https://github.com/GTQT/GTQT-Core/tree/7ab5b236c4839b84de5a65d4b56b5655732740d1)

对 GTQT 组织和 MeowmelMuku 账号下 36 个公开仓库、59 个公开分支的历史按精确路径 `libs/gtqtcore-1.9.0.jar` 查询，只找到 Pollution 在七月加入、八月删除的同一份文件。其他文件名、其他账号和非公开分发仍可能提供更新版本。[删除提交](https://github.com/GTQT/Pollution/commit/b3fc7c626b9ba3e776e2b079f816dd7bb73f2350)

## 仓库与打包分工

- [workspace.lock.json](workspace.lock.json) 记录各检出提交、关键跨模组制品及其下载哈希。各组合另行锁定运行依赖；每次专服记录包含实际入服 JAR 的指纹。上游构建时间戳可使重编后的 JAR 哈希变化。
- GuideQT、SatisMC 在清单中等待可核验的 1.12.2 源码或制品。GTFO、ModelLoadLib 已纳入依赖管理。GCYM、Supercritical、GTTopAddition、BestQuestings、GregTinker、GTMaid、VisualOres 等可由历史包回溯版本；是否进入 1.9 候选按实际使用它们的模组和脚本逐项确认。[历史模组列表](https://github.com/GTQT/GT-QuantumTransition/blob/3fd61bb3d9eacef642dd55eedb90bd2de216dec8/modlist.html)
- 修改上游 API 时，在对应 fork 开分支，用候选 JAR 跑受影响的下游构建及专服。上游合入后更新本仓锁和验收记录，再由整合包仓锁定实际发布文件。各组合使用独立的 `mods`、世界和配置；Java 25 的 Cleanroom 组合单独运行。
- 整包候选先运行 `python -B tools/pack_check.py <实例的mods目录>`，再运行对应专服、客户端加入、关键机器加工与世界重载。当前已通过的共服检查覆盖注册、建档、保存和停服。客户端联机和机器加工仍待验收。

当前 Pollution 的开发可以使用 `pollutionJulyCompat`。取得作者新版 Core 后，再以 `pollutionCurrent` 验证原始组合。SteamTech 与 DrTech 使用各自已通过联调的八月环境。
