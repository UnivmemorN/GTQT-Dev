# Future MC 的两个实现与 BogoSorter 冲突分析

日期：2026-11-19

> **2026-11-19 更新：本分析提出的“改名共存”方案已放弃。** PR #24 已关闭，远端/本地分支已删除。按 cropQT 开发者方向：cropQT 使用 FFD；整包移除独立 Future MC；DrTech 的 `futuremc` 保持原样；cropQT 中紫水晶注册已删除。以下内容仅保留为历史分析，不再作为执行方案。

## 结论

- 独立 Future MC 与 DrTech 内置的 `futuremc` **不是同一个实现**，只共享 `modid = futuremc` 和少量注册名。
- 两者放在一起时，FML 在 mod 发现阶段就会因重复 modid 抛出 `DuplicateModsFoundException`，**游戏无法启动**，不是普通的内容覆盖或版本冲突。
- 即使绕过 FML 的重复检查，两者在 `futuremc:` 注册表命名空间、下游按 modid 探测原版类的逻辑（BogoSorter）、以及内容集合上仍然冲突。
- 两者内容不是包含关系：独立版覆盖 1.13–1.16 内容，DrTech 版是 1.17+ 的新内容子集；交集只有 `chain`、`composter`、`lantern`、`soul_lantern` 四个方块。删掉任意一方都会丢内容。

## 两个实现

| | 独立 Future MC | DrTech 内置 |
| --- | --- | --- |
| 文件 | `Future-MC-0.2.21.jar`（19,985,643 B，SHA-256 `e1e6ec0397ae0479ad1d42557a03b97f9a159628f83829bb5ceab4822af978be`） | `drtech-1.8.9.jar` 内的 `com.drppp.futuremc`（DrTech SHA-256 `6336c89f89a03253233131994c2fff7d9828242af9655282f68e42da110e44cd`） |
| modid | `futuremc` | `futuremc` |
| `@Mod` 版本 | `0.2.6`（mcmod.info 写 `0.2.21`，Kotlin 常量仍是 0.2.6） | `1.0.0` |
| 实现 | Kotlin，`thedarkcolour.futuremc.*`，需要 `forgelin`（`modLanguageAdapter = net.shadowfacts.forgelin.KotlinAdapter`） | Java，`com.drppp.futuremc.*`，不依赖 forgelin |
| 内容规模 | 170 个 blockstate，1.13–1.16 内容：`ancient_debris`、`barrel`、`bamboo`、`bee_nest`、`beehive`、`bell`、`blackstone` 系列、`blast_furnace`、`blue_ice`、`campfire`、`cartography_table`、`composter`、`chain`、`lantern`、`soul_lantern`、`basalt` 等 | 14 个 blockstate：紫水晶系列、`bubble_column`、`calcite`、`smooth_basalt`、`chain`、`composter`、`lantern`、`soul_lantern`、`dried_ghast`，另有 `happy_ghast` 实体 |
| 交集 | `chain`、`composter`、`lantern`、`soul_lantern` | 同左 |
| 独有内容 | 木桶、远古残骸、黑石、竹子、蜂巢、钟、营火、制图台、高炉、蓝冰等 | 紫水晶、方解石、平滑玄武岩、气泡柱、干燥恶魂、快乐恶魂 |

独立版没有紫水晶/方解石/气泡柱/干燥恶魂/快乐恶魂；DrTech 版没有木桶/远古残骸/黑石/竹子/蜂巢等。**两者不是替代关系，也不是包含关系。**

## 冲突机制

### 1. FML 身份层（致命）

Forge/FML 的 `Loader.identifyDuplicates` 会把每个 `ModContainer` 的 modid 收集起来；发现重复时：

```java
FMLLog.log.fatal("Found a duplicate mod {} at {}", e.getElement().getModId(), dupsearch.get(e.getElement()));
dupes.putAll(e.getElement(), dupsearch.get(e.getElement()));
...
if (!dupes.isEmpty()) {
    throw new DuplicateModsFoundException(dupes);
}
```

（`net/minecraftforge/fml/common/Loader.java:443-467`，Forge `14.23.5.2847`）

所以两个 jar 同时存在时，FML 在 `preInit` 之前就终止加载；这与版本号（0.2.6 / 1.0.0）无关，FML 不会按版本选一个。

### 2. 注册表命名空间层

假设绕过 FML 的重复检查，两者仍会向同一个 `futuremc:` 命名空间注册对象。共用的 4 个方块名（`chain`、`composter`、`lantern`、`soul_lantern`）会触发 `ForgeRegistry` 的重复名检查：

```java
if (oldEntry != null) // duplicate name
{
    if (!this.allowOverrides)
        throw new IllegalArgumentException(String.format("The name %s has been registered twice, for %s and %s.", key, getRaw(key), value));
```

（`net/minecraftforge/registries/ForgeRegistry.java:304-313`）

物品、实体、TileEntity 注册同理；即使只保留一个实现，另一个实现的注册代码仍可能继续执行并产生二次注册。

### 3. 实现/API 层

两者类包不同（`thedarkcolour.futuremc.*` vs `com.drppp.futuremc.*`），不会直接重复定义同名类；但下游 mod 往往只检查 `modid`，然后引用原版 Future MC 的类。典型是 BogoSorter：

```java
ldc "futuremc"
invokestatic Loader.isModLoaded
ifeq skip
ldc class thedarkcolour/futuremc/container/ContainerBarrel
...
addCompatSimple(...)
```

DrTech 的 `futuremc` 没有 `thedarkcolour.futuremc.container.ContainerBarrel`，于是 modid 检查通过、类加载失败，`DefaultCompat.init` 抛 `NoClassDefFoundError`。这是“同名但不是同一个东西”的直接后果。

### 4. 内容层

即使解决了前面三层，选边也会丢内容：

- 移除独立版、只用 DrTech 子集 → 丢木桶、远古残骸、黑石、竹子、蜂巢、营火等；旧 183/185 候选正是如此，文档记录“缺少的远古残骸会影响任务兑换”。
- 保留独立版、禁用 DrTech 的 `futuremc` → 丢紫水晶、方解石、平滑玄武岩、气泡柱、干燥恶魂、快乐恶魂。

## BogoSorter `barrelguard` 补丁

`bogosorter-1.6.2-barrelguard.jar` 只改一个类 `com/cleanroommc/bogosorter/compat/DefaultCompat.class`：

- 原版 1.6.2：`7e8edc3137e96f04d8e46a44e66737ec159a503c9e61894b3b3425fbddab12d1`（287,928 B）
- 补丁版：`77c3379239c834070c238a47cd9153be7e4b1aa91277e39a25b5c4eeae084e11`（627,168 B，重打包使用 ZIP_STORED）
- 1.6.4 同款：`08286ce5…` → `b1ba2ef5…`（633,266 B）

补丁在 `futuremc` 加载判断之后追加：

```java
if (DefaultCompat.class.getResource("/thedarkcolour/futuremc/container/ContainerBarrel.class") == null) {
    // 跳过木桶槽位注册
}
```

效果：装独立全量 Future MC 时木桶整理照常；装 DrTech 子集时跳过木桶注册、不再崩溃。**它不能解决 modid 重复，只解决“DrTech 作为 futuremc 提供者”时的下游崩溃。**

## 可选方案

| 方案 | 做法 | 代价 |
| --- | --- | --- |
| A（旧候选先例） | 移除独立 Future MC，使用 DrTech 子集 + `bogosorter-1.6.2-barrelguard.jar` | 丢 1.13–1.16 内容（木桶/远古残骸等），任务需调整 |
| B | 保留独立 Future MC，禁用/剥离 DrTech 的 `futuremc` | 丢 DrTech 的 1.17+ 内容（紫水晶/方解石/气泡柱/干燥恶魂/快乐恶魂），需要改 DrTech 代码 |
| C（长期） | 把 DrTech 的 1.17+ 内容并入独立 Future MC，DrTech 不再内嵌 `futuremc` | 需要上游协调与内容对齐 |
| D | 把 DrTech 的 modid/命名空间改成独立值（如 `drtechfuturemc`） | 可共存，但 `futuremc:` 物品 ID 变化，配方/任务/存档映射都要改，不推荐 |

当前建议：若目标是“先能进整包”，走 A，并在任务侧接受 1.13–1.16 内容缺失；若必须保留完整 Future MC 内容，走 B/C，不能两个 jar 直接并存。

## 证据

- FML 重复 modid 检查：`net/minecraftforge/fml/common/Loader.java:443-467`（Forge 14.23.5.2847）
- 注册表重复名检查：`net/minecraftforge/registries/ForgeRegistry.java:304-313`
- 独立 Future MC：`@Mod(modid = "futuremc", name = "Future MC", version = "0.2.6", dependencies = "required-after:forgelin;required-after:forge@[14.23.5.2847,)", modLanguageAdapter = "net.shadowfacts.forgelin.KotlinAdapter", useMetadata = 1)`；170 个 blockstate；无紫水晶/方解石/气泡柱/干燥恶魂
- DrTech：`FutureMCMain` 的 `@Mod(modid = "futuremc", version = "1.0.0")`；14 个 blockstate；无 `ContainerBarrel`
- BogoSorter：`DefaultCompat.init` 的 `Loader.isModLoaded("futuremc")` 后直接引用 `thedarkcolour/futuremc/container/ContainerBarrel`
