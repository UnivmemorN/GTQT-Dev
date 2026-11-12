# 当前 Pollution 配合七月 Core

`pollutionJulyCompat` 在作者 Pollution `9ed70ed` 基础上修复材料兼容、网络包的物理端分离及工业注魔的注册和加工。编译使用原始七月 Core。运行时使用经过两处修补的 Core 和十月喵呜版 GregTech 的生产名称 JAR。兼容分支 `117162f` 恢复了魔法聚变反应堆要求的铀-235 压缩块。[依赖锁](../../workspace.lock.json) · [Pollution 兼容分支](https://github.com/UnivmemorN/Pollution/tree/117162fc16b0a6f4e87571ab972c8c1bf9e3a03c) · [Core 补丁](compat/README.md)

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
python -B dev/pollution/compat_server.py @inputs --processing
python -B dev/pollution/compat_server.py @inputs --reactor-altar
python -B dev/pollution/compat_server.py @inputs --legacy-infusion
```

各组验收分别创建新世界。材料测试在建档时写入随机标记，保存并退出后由第二个 JVM 读回，同时核对材料对象和两条已注册的配方。纯运行组仅安装实际运行模组，通过 `level.dat` 核对两次保存的世界名、种子和 26 个 FML 模组条目。下表记录 `d50486c` 的验收。当前锁定版 `117162f` 完成了工业加工、原生祭坛和纯运行三组。[先前六组验收](../../evidence/pollution-july-compat.json) · [当前反应堆验收](../../evidence/pollution-fusion-reactor.json)

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
- 已在 Forge 2860 的真实专服验证阳光化合物粉在魔法化学反应釜中有一个匹配输出，太阳塔罗在魔法组装机中有一个消耗该粉的匹配输入。这两条配方的验证范围是注册表。

## 工业注魔

在同一组生产依赖下，对修复前的 `71d7de1` 枚举 Thaumcraft 原方和 Pollution 要素映射，确认 8 次空流体来自以下 7 张 Thaumcraft 原方。旧 GT 配方构建器会记录空值并跳过该种流体，导致机器少收要素。Pollution 已经提供两种液态材料，现将 `aversio` 映射到 `infused_weapon`、`alienis` 映射到 `infused_alien`。换算沿用 144 mB/要素点。[要素映射](https://github.com/UnivmemorN/Pollution/blob/f8d654daa57136412348eaa8fe8330db6ddd5dfb/src/main/java/meowmel/pollution/api/utils/POAspectToGtFluidList.java)

| Thaumcraft 原方（省略 `thaumcraft:`） | 每次加工补回的流体成本 |
| --- | --- |
| `elementalsword` | 4,320 mB Aversio |
| `voidrobehelm`、`voidrobechest`、`voidrobelegs` | 每件 3,600 mB Alienis |
| `causalitycollapser`、`voidsiphon` | 每件 7,200 mB Alienis |
| `primalcrusher` | 7,200 mB Aversio 和 7,200 mB Alienis |

另一张原方来自 Pollution 自身。IV 魔法电路板使用 1 张 EV 板、3 种符文各 1、1 个稳定框架，以及电容、晶体管、二极管三种贴片各 8 个。旧导入器为这 29 件物品逐件占用配方栏，触发了 25 栏上限。现在 8 种输入仍消耗 29 件，原方研究、四种要素和基础参数 480 EU/t × 960 tick 均保留。每个祭坛位置可以使用其任一匹配物品。缺少整项原料或无法映射要素的配方会带原方 ID 跳过，以免省去原料。[原方](https://github.com/UnivmemorN/Pollution/blob/f8d654daa57136412348eaa8fe8330db6ddd5dfb/src/main/java/meowmel/pollution/loaders/recipes/MagicIntegrationRecipes.java#L518-L537) · [导入器](https://github.com/UnivmemorN/Pollution/blob/f8d654daa57136412348eaa8fe8330db6ddd5dfb/src/main/java/meowmel/pollution/api/recipes/builder/IndustrialInfusionBuilder.java)

### 魔法聚变反应堆的铀-235 压缩块

作者于 2024-05-24 加入原方时，第九个环绕材料便是 `blockUranium235`。同次提交附带的 GTCEu 2.8.8-beta 将铀-235 定义为锭材料，由 GregTech 自动生成压缩块。2024-08-03 的核材料改动移除了其锭属性，保留了粉和熔融流体。原方随仓的 GTQTCore 只为该材料增加核燃料芯块。到可取得的 1.9 开发依赖，七月、八月和十月的喵呜版均将铀-235 定义为粉末，七月 Core 也未恢复压缩块。先前专服因此注册了一个缺少可用原料的祭坛配方，并跳过其工业版本。[最初配方](https://github.com/GTQT/Pollution/blob/b9caaca3fc96655646cb67e1648ce397b9ba14f9/src/main/java/keqing/pollution/loaders/recipes/MagicGCYMRecipes.java#L416-L431) · [原作者随仓 GT 二进制](https://github.com/GTQT/Pollution/blob/b9caaca3fc96655646cb67e1648ce397b9ba14f9/libs/gregtech-1.12.2-2.8.8-beta.jar) · [同期 Core](https://github.com/GTQT/Pollution/blob/b9caaca3fc96655646cb67e1648ce397b9ba14f9/libs/gtqtcore-1.0.jar) · [上游核材料变更](https://github.com/GTQT/GregTech/commit/85834cbe981401d3049fdcda408abeb70b1cc8ae)

公开整合包主线的覆盖文件、1.8.7 分支的脚本及 1.8.8 实例均未找到补注册该块的规则。公开仓的 `1.9.0.json` 是公告测试样例，未发行 1.9 的私有打包脚本无法核验。兼容分支在 Pollution 的材料事件中给已有的 `Materials.Uranium235` 增加 `FORCE_GENERATE_BLOCK`。由 GregTech 自动生成的压缩机配方使用 9 份铀-235 粉，产出 1 个铀-235 压缩块，基础参数为 2 EU/t、300 tick。专服探针调用注册配方的匹配与扣料逻辑，核对少一份粉和错用同位素均失败，再用该配方返回的产物进行注魔。压缩机本身未作为机器实体运行。[公开脚本](https://github.com/GTQT/GT-QuantumTransition/tree/3fd61bb3d9eacef642dd55eedb90bd2de216dec8/overrides/scripts) · [1.9 公告样例](https://github.com/GTQT/GT-QuantumTransition/blob/3fd61bb3d9eacef642dd55eedb90bd2de216dec8/remote/version/1.9.0.json) · [GregTech 压缩机配方生成](https://github.com/GTQT/GregTech/blob/1d6dcad959021ec1530238620211f55aef471daf/src/main/java/gregtech/loaders/recipe/handlers/MaterialRecipeHandler.java#L197-L202) · [兼容修复](https://github.com/UnivmemorN/Pollution/commit/117162fc16b0a6f4e87571ab972c8c1bf9e3a03c)

原生祭坛验证使用真实基座、矩阵和源质罐。完成 `INFUSION@2` 研究后，缺铀块或放入铀-238 块均无法启动。使用正确压缩块时，消耗中心框架、10 件环绕材料和 692 点源质，在 3,765 个祭坛更新 tick 后得到反应堆。成型工业注魔矩阵消耗同样的 11 件物品、99,648 mB 配方要素及 822 mB 聚魔液，在实测结构中用时 822 个加工 tick、耗电 6,312,960 EU。两组均在各自的世界保存重启后读回第一台，第二次加工后实有两台。[专服运行记录](../../evidence/pollution-fusion-reactor.json)

### 加工与存档

在十月 GregTech 上，线圈启用并行时，旧矩阵会将配方交给多个独立的调度槽，随后只推进 Pollution 自己的计时器。专服复现时元素剑消耗了 3,763,200 EU 和 490 mB 聚魔液，槽进度仍为 1/106。现在矩阵以同种配方为一批，沿用线圈并行上限、玻璃加速与逐 tick 供魔。新批次通过 Pollution 的加工逻辑完成和出货。

`--processing` 在服务端世界放置并成型工业注魔矩阵，给测试玩家授予原方研究，使用实际物品仓、要素输入仓、能源仓和专用聚魔仓。脚本逐 tick 调用机器的加工逻辑，从真实输出仓读取成品。保存并启动第二个 JVM 后，先核对上次产物，再投料重复加工。独立的缺料断言逐一减少一个原方物品或 1 mB 配方流体，调用 GT 配方匹配器检查拒绝结果。

测试结构中，单份 IV 板实际耗时 228 个加工 tick，扣 29 件物品、27,648 mB 配方要素和 228 mB 聚魔液。同种配方双并行一次扣 58 件和 55,296 mB 配方要素，单批产出 2 张。该测试特意断聚魔 12 tick，断供期间零耗电、零出货，进度从 5 回退到 1。接回聚魔后整批完成。双并行案例每轮都额外投料，第一次关服时输出仓共有 3 张 IV 板，重启并完成第二轮后共有 6 张。

`--legacy-infusion` 用十月 GT 自带的序列化器生成旧格式的已扣料调度槽，在同一真实机器上检查半程保存、剩余 EU 和聚魔成本、出口堵塞及疏通后的交付。迁移只接续存档内仍存在的槽、进度和预定产物。旧格式没有过去每 tick 的扣费流水，无法计算旧故障已多消耗的 EU 或聚魔液。

实测快照包含 2 个运行槽和 1 个完成待出货的槽。第一次关服前，两个运行槽进度分别为 6 和 9；第二次启动读回同一进度，实扣剩余 288 EU 和 5 mB 聚魔液完成。出口满时保留三份成品，腾出空间后在无电、无聚魔的条件下各交付一次。此项使用生成的旧格式快照，未导入玩家历史世界。[原始验收数值](../../evidence/pollution-july-compat.json)

此最小实例另有三种生物的掉落表引用未安装的 Thermal Foundation 物品，以及重复添加的箱子战利品条目。客户端联机与特效未纳入本次专服验收。
