# 当前 Pollution 配合七月 Core

`pollutionJulyCompat` 在作者 Pollution `9ed70ed` 基础上增加材料兼容和网络包的物理端分离。编译仍使用原始七月 Core。运行时使用经过两处修补的 Core 和十月喵呜版 GregTech 的生产名称 JAR。两份派生产物的 SHA-256 见 [workspace.lock.json](../../workspace.lock.json)。[Pollution 兼容分支](https://github.com/UnivmemorN/Pollution/tree/71d7de118d3b5278b2f8caaec567449c6d1f4d62) · [Core 补丁](compat/README.md)

## 复跑

使用 Python 3.11+、Git 和 JDK 8、16、17。先按协调仓首页的 SteamTech 步骤完成基础构建及一次专服验证，以准备 Forge 2860 和公共依赖。以下命令在协调仓根目录执行。已有环境可将 `$steam` 指向原检出。首次勿加 `--offline`。请把 `$rig` 换成服主已接受 EULA 的独立空闲测试服目录。

```powershell
python -B tools/workspace.py checkout steamRunner
python -B tools/workspace.py checkout pollutionCompat
$steam = 'work/src/steamRunner'
$source = 'work/src/pollutionCompat'
$state = 'work/pollution-compat'
$runtime = 'work/verified-compat-runtime'
$rig = 'D:/Minecraft-Test/forge-112'
python -B dev/pollution/build.py --source $source --steam-env $steam --state $state build
python -B dev/pollution/prepare_compat.py --source $source --steam-env $steam --gradle-home "$state/gradle" --output $runtime
$inputs = @('--steam-env', $steam, '--source', $source, '--state', $state, '--core', "$runtime/gtqtcore-1.9.0-july-compat.jar", '--gregtech', "$runtime/gregtech-1.9.0-october-srg.jar", '--server-dir', $rig)
python -B dev/pollution/compat_server.py @inputs
python -B dev/pollution/compat_server.py @inputs --supplier
python -B dev/pollution/compat_server.py @inputs --core-field
python -B dev/pollution/compat_server.py @inputs --runtime-only
```

四组验收分别创建新世界。前三组在建档时写入随机标记，保存并退出后由第二个 JVM 读回，同时核对材料对象和两条已注册的配方。第四组仅安装实际运行模组。两次启动均完成保存，且从 `level.dat` 读回相同的世界名、种子和 26 个 FML 模组条目。[四组实测记录](../../evidence/pollution-july-compat.json)

| 专服场景 | 两次启动的结果 |
| --- | --- |
| 七月 Core 缺少 Sunnarium | 创建 `pollution:sunnarium`，ID 14 |
| 其他注册者已提供同名材料 | 复用 `gtqtcore:sunnarium`，ID 30000 |
| 测试 Core 提供公共字段 | 复用该字段指向的 `gtqtcore:field_fixture_sun`，ID 30000。特意使用不同注册名，以验证字段优先 |
| 纯运行组合 | 建档、保存、重启和再次保存均成功 |

实测 Pollution JAR 的 SHA-256 来自独立检出的完整构建。同一源码在另一工作树增量构建时生成了不同的 JAR 哈希。复跑脚本核验源码提交、依赖哈希和本次构建产物的回执。两份派生运行库另按锁定的固定哈希校验。

## 运行行为

- Core 若提供已注册的 `GTQTMaterials.Sunnarium`，Pollution 优先复用该对象。没有有效字段值时，先查找已注册的同名材料；确实缺少才创建 `pollution:sunnarium`。回退材料保持七月的 `Su` 元素定义、`0xFAF20E` 颜色、SHINY 图标及粉和流体形态。七月的 ID 6 在当前源码已归 `WhiteMansus`，回退使用空闲 ID **14**。此验收使用新世界，旧版本存档的材料 ID 迁移尚未验证。
- 物理专服跳过七月 Core 给三种数据物品安装渲染器的步骤。物理客户端仍在原时机安装。为 Core 线圈补上 `getName()` 的生产名称桥接。十月 GregTech 使用固定工具恢复三个桥接方法，其余注册数据来自原始 JAR。
- Pollution 的扭曲效果与龙摇晃共五种客户端消息。双方沿用原频道、消息类型及编号。物理客户端安装原处理器，专服保留发送编码所需的注册。
- 已在 Forge 2860 的真实专服验证阳光化合物粉在魔法化学反应釜中有一个匹配输出，太阳塔罗在魔法组装机中有一个消耗该粉的匹配输入。未启动图形客户端；机器实加工和客户端特效另行验收。

最小实例的启动日志还报告 8 次空流体参数、一条工业注魔配方的物品输入数超过上限（29 项，上限 25）、三种生物的掉落表引用未安装的 Thermal Foundation 物品，以及重复添加箱子战利品条目。两条 Sunnarium 配方均在注册表中匹配成功。[验收记录](../../evidence/pollution-july-compat.json)
