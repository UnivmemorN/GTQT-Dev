# Pollution 1.12.2 构建

使用当前源码开展兼容开发，可直接复跑[七月 Core 兼容组合](july-compat.md)。下面的两个组合用于核对作者原始版本。

当前检查对象为 [Pollution `9ed70ed`](https://github.com/GTQT/Pollution/tree/9ed70ed318c57e350cfcdf725c1eadda8f539789)。Forge 2847、stable_39、Gradle 8.5、RFG 1.4.1 的构建工具复用 [SteamTech 独立开发环境](https://github.com/UnivmemorN/GregTech-SteamTech/tree/6098eee246a59388d32f8c7112f1305143f7c1de/dev/legacy)。先按其说明准备工具仓和 JDK 8、16、17。

在协调仓根目录执行以下 PowerShell 命令。首次构建需要网络。脚本会检查 Pollution 源码和 SteamTech 工具仓的提交、暂存区和工作区中的已跟踪改动，然后向 Pollution 签出的 `libs` 补上缺少的作者 JAR。私有 Gradle 缓存由 `--state` 指定。热缓存可加 `--offline`。

```powershell
git clone https://github.com/GTQT/Pollution.git D:/GTQT-Pollution-1.12.2
git -C D:/GTQT-Pollution-1.12.2 checkout --detach 9ed70ed318c57e350cfcdf725c1eadda8f539789
python -B dev/pollution/build.py --source D:/GTQT-Pollution-1.12.2 --steam-env D:/GTSteam-1.12.2 --state D:/GTQT-Pollution-State build
```

## 当前提交的实测结果

所需 Core 的类名、候选 JAR 哈希、公开测试包调查及复验步骤见[当前 Core 来源核查](core-provenance.md)。

| 当前 Pollution 使用的依赖 | Gradle 编译结果 |
|---|---|
| 7 月 27 日同批 GregTech、Core、GTFO、SteamTech，加上 ModelLoadLib | 19 条 javac 诊断，涉及矿脉、消声仓接口和 Sunnarium 材料 |
| 仅把 GregTech 换为 10 月 31 日快照，其余相同 | 剩 4 条诊断，均源于 Core 缺少同一个公开字段 `GTQTMaterials.Sunnarium` |

当前提交的默认复现命令使用十月 GregTech。两个静态导入和两处使用分别位于 [MagicIntegrationRecipes](https://github.com/GTQT/Pollution/blob/9ed70ed318c57e350cfcdf725c1eadda8f539789/src/main/java/meowmel/pollution/loaders/recipes/MagicIntegrationRecipes.java#L421) 和 [ThaumcraftRecipes](https://github.com/GTQT/Pollution/blob/9ed70ed318c57e350cfcdf725c1eadda8f539789/src/main/java/meowmel/pollution/loaders/recipes/ThaumcraftRecipes.java#L53)。7 月使用 Pollution 自己注册的材料，8 月 30 日的上游提交将工艺改为读取 Core 材料。验收当前提交还需要含有该字段的 Core，或经过独立审查的材料兼容改动。[上游改动](https://github.com/GTQT/Pollution/commit/950137a42a2e6309d6642295438a69cd6bf1cd0e)

脚本固定每个外部 JAR 的提交、长度和 SHA-256。7 月 Core 文件内部声明 `gtqtcore`、`1.9.0`、`1.12.2`，SHA-256 为 `458029f1649d5b08a4e71be5820dddda4a4dc606524e0841996571ba87a09502`。可用 JDK 自带工具检查这份二进制的 API。

```powershell
javap -classpath D:/GTQT-Pollution-1.12.2/libs/gtqtcore-1.9.0.jar meowmel.gtqtcore.api.unification.material.GTQTMaterials | Select-String Sunnarium
```

[7 月 Core、GTFO、SteamTech 和 GregTech](https://github.com/GTQT/Pollution/tree/d1611ce5dec0eac71c2d68cc86975db86c2e3112/libs) · [10 月 GregTech](https://github.com/GTQT/QuantumHue-Visualizer/tree/72e08b4f1b3d64748ca3bbf3e09bf133de0f8405/libs) · [ModelLoadLib](https://github.com/GTQT/DrTech/tree/e530bc957baa05437a3a6c17c6a7f5fe18cbe0bf/libs)

## 7 月历史源码

单独检出 7 月 27 日的 Pollution 与作者当时提交的依赖。脚本按签出版本选择依赖，两个源码目录可分别保留。

此组合的完整 `build` 已通过，23 个任务实际执行。热缓存离线构建、清空项目构建产物后的 `--offline --clean build` 也通过，后者执行了 23 个任务。生产 JAR 的 ZIP CRC、模组 ID、版本号与 Java 8 字节码均已检查。首份 JAR 的 SHA-256 为 `88ade3838d52f57e30b909734eac6a8757219dc0b861b6934e1f27d2d1ce1525`，离线重建的为 `516beb4e72d0ad5de5e6989a0ecb4ac35eda2d15ea057a4a4a2315299b4c2d23`。这两次上游打包产物未达到字节级一致，入包时应锁定实际选用的制品。上游没有测试源码，机器加工未验证。构建时有 5 条源于可选 ZenScript 注解的警告。

```powershell
git -C D:/GTQT-Pollution-1.12.2 worktree add --detach D:/GTQT-Pollution-July d1611ce5dec0eac71c2d68cc86975db86c2e3112
python -B dev/pollution/build.py --source D:/GTQT-Pollution-July --steam-env D:/GTSteam-1.12.2 --state D:/GTQT-Pollution-State build
```

## 7 月服启动结果

2026-11-12 在 Java 8 和 Forge 14.23.5.2860 的隔离回环专服上实测。7 月 Core 的模组注解仅声明 GregTech，启动时还会加载 ModelLoadLib 的 `ModelLoadException`。按作者二进制补上该依赖后，专服进入物品注册。以下两组都在 Forge 报告 `Done` 前退出。

| 专服使用的 GregTech | 首个实际阻塞 |
|---|---|
| 与 Core 同提交的 7 月 JAR | Core 在 `CommonProxy.registerItems:189 → GTQTMetaItems.extraBehavior:545` 给数据存储棒添加 `DataRenderItemBehavior`。该类引用客户端渲染接口 `IBakedModel`，Forge 在专服侧拒绝加载。相同配置复验得到相同栈。[结果与依赖哈希](july-server.json) |
| SteamTech 专服已验证的 8 月生产 JAR | Core 在更早的材料注册阶段从 `GTQTOrePrefix:58` 读取 GregTech 的 `MaterialIconType.oreLean`，抛出 `NoSuchFieldError`。[结果与依赖哈希](august-gt-server.json) |

七月 JAR 的文件名和 `mcmod.info` 将 Pollution 标为 1.9.0，Forge 启动日志实际显示 `pollution 0.0.1-beta`，同批 Core 显示 `gtqtcore 1.9.0`。这是 Pollution 的 `@Mod` 注解指定的运行时版本。[上游声明](https://github.com/GTQT/Pollution/blob/d1611ce5dec0eac71c2d68cc86975db86c2e3112/src/main/java/meowmel/pollution/Pollution.java#L37-L47)

将 `$serverDir` 指向已接受 EULA 的空闲隔离目录。可以使用仅含 `eula.txt` 的目录，也可以使用含有 `server.properties` 的专用测试服。目录名和白名单内容可自定。省略 `--server-dir` 时，脚本读取 SteamTech 环境 `.legacy-dev/settings.json` 的 `server_dir`。第一条测试命令使用同批 JAR，第二条只换八月生产 GregTech。每次测试均使用排他锁、新配置和新世界，记录原目录条目及已有 EULA、白名单、服务端配置在恢复前后的哈希。完整控制台、Forge 崩溃报告和结果在 `<state>/server-checks/`。

```powershell
$serverDir = 'D:/Minecraft-Test/forge-112'
python -B dev/pollution/server.py --source D:/GTQT-Pollution-July --steam-env D:/GTSteam-1.12.2 --state D:/GTQT-Pollution-State --server-dir $serverDir
python -B dev/pollution/server.py --source D:/GTQT-Pollution-July --steam-env D:/GTSteam-1.12.2 --state D:/GTQT-Pollution-State --server-dir $serverDir --august-gt
```
