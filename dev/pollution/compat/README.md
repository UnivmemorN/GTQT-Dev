# 七月 Core 的运行补丁

输入取自 [Pollution 作者当时提交的 Core 1.9.0](https://github.com/GTQT/Pollution/blob/d1611ce5dec0eac71c2d68cc86975db86c2e3112/libs/gtqtcore-1.9.0.jar)，由协调仓 `artifacts.coreJuly` 锁定。以下两项补丁应用在单独生成的运行 JAR 上。当前 Pollution 的编译输入仍可使用原始七月文件。

- Core 在公共的物品注册事件中调用 `GTQTMetaItems.extraBehavior()`。这个方法给数据棒、数据球、数据模块各添加一个 `DataRenderItemBehavior`，只含渲染回调，类加载时涉及客户端的 `IBakedModel`。补丁在原调用位置检查 Forge 的物理端。物理客户端（含单人游戏）仍在同一事件、同一顺序调用上游方法。专服会跳过这三项渲染组件，并继续余下的物品注册。三个组件和渲染回调的字节码均保留。
- 在实际专服中，修复渲染注册后，又在 `CasingDefinition.fromMap` 读取 Core 的加热线圈时发现 `AbstractMethodError`。该线圈类通过 Minecraft 的生产名称 `func_176610_l()` 返回上游构造器保存的线圈名称，GregTech 的接口调用 `getName()`。为 `BlockWireCoil$Builder$1` 新增一个公开桥接方法，调用原来的 `func_176610_l()` 并直接返回其结果。

在协调仓根目录执行以下 PowerShell 示例。需要 Gradle 8.5 分发的 ASM 9.5 和 JDK 17；两者可以复用准备好的 SteamTech 工具环境。示例中的 `$steamEnv` 可设为本机已有的那个检出路径。

```powershell
$steamEnv = 'D:/GTSteam-1.12.2'
python -B tools/workspace.py fetch coreJuly
python -B dev/pollution/compat/patch_core.py --input work/artifacts/coreJuly/gtqtcore-1.9.0.jar --output work/core-compat/gtqtcore-1.9.0-july-compat.jar --java-home "$steamEnv/.legacy-dev/jdks/java17" --gradle-cache "$steamEnv/.legacy-dev/gradle"
```

脚本核对输入和 ASM 库的 SHA-256，以固定的 ZIP 元数据和存储方式写出新文件。两次独立生成的 JAR 共 9,194,467 字节，SHA-256 均为 `fd2cbe765cb362e4869855ca4244b71f9d8761d7b5af9e68c98cfa178731f046`。重新展开比对原 JAR 的 3,709 个条目，名称和顺序相同，只有 `CommonProxy.class` 与 `BlockWireCoil$Builder$1.class` 的内容有变化。

## 验证 Core 提供 Sunnarium 字段时的行为

专服验收的 `--core-field` 模式会从上述运行 JAR 生成独立的 `TEST-ONLY-gtqtcore-field.jar`，仅将其放入此次测试服。生成器只在 `GTQTMaterials.class` 增添 `public static Material Sunnarium`。两次独立生成的 SHA-256 都为 `20d9692aacd69c633aee01c99e7cd3ead66377cc15ed7fd0dc5c526de1783e07`。[测试制品生成器](../probe/core_field_fixture.py)

探针先注册 ID 30000 的 `gtqtcore:field_fixture_sun`，把该对象写入真实字段。这个注册名使按 `sunnarium` 查找的路径得不到结果。专服新建与重载同一个世界时，都确认 Pollution 使用该对象、按名为 `sunnarium` 的材料数为零、魔力化学反应釜与太阳塔罗各命中一条使用该材料的配方。`--supplier` 单独验证七月 Core 缺少字段、已有同名注册材料时的路径。[探针源码](../probe/SunnariumProbe.java)
