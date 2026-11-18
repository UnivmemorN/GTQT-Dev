# DrTech 接入状态与已知问题

更新日期：2026-11-18
上游：`GTQT/DrTech` `cd1668d6`（YOT/TFFT 移除 #22 已合入，构建脚本改用 RFG 1.4.9）
上游 issue：[GTQT/DrTech#23 资源与配方已知问题](https://github.com/GTQT/DrTech/issues/23)
开发工具：`dev/drtech/build.py` 与 `work/gtqt19-drtech-new/tool-maven` 已升级到 RFG 1.4.9。

## 已验证

- `build` 通过；产物 `drtech-1.8.9.jar`，SHA-256 `6336c89f89a03253233131994c2fff7d9828242af9655282f68e42da110e44cd`
- dev `runClient`：40 个 mod 加载到主菜单；`runServer`：38 个 mod，`Done (1.487s)` 后正常停服
- dev 环境依赖：GT `bbfe1b58`、GTFO `f8521a87`、Forestry 5.8.2.426、Binnie's 2.5.1.203、EnderIO 5.3.72、EnderCore 0.5.78
- dev `runClient`/`runServer` 需要把 `AutoConfig-1.12.2-1.0.2.jar`、`AutoSave-1.12.2-1.0.11.jar`、`EnderCore-1.12.2-0.5.78-core.jar` 单独放到 `run/mods`；生产实例由 Forge LibraryManager 从 EnderIO/EnderCore 的 `META-INF/libraries` 解出
- 上游 PR #22 合入后，本地旧的 `codex/remove-yot` 分支已删除

## 不阻断启动/合并的已知问题

| 问题 | 位置 | 表现 | 建议 |
| --- | --- | --- | --- |
| 聚变堆控制器贴图路径多一层 `blocks` | `client/Textures.java:89` 的 `SimpleSidedCubeRenderer("drtech:blocks/fusion/...")`，用于 `MetaTileEntityAdvancedFusionReactor.getBaseTexture` | 控制器显示缺失贴图；外壳方块本身正常 | 改为渲染器约定的相对路径 |
| 砖砌/元素外壳落到 `gregtech` 域 | `Textures.BRICKED_AGRICULTURAL_CASING`、`ELEMENT_CONSTRAINS_MACHINE_CASING`；实际文件在 `assets/drtech/textures/blocks/` | 工业农场控制器缺失贴图；元素外壳 renderer 实际未被使用，仅日志报错 | 贴图移到 `assets/gregtech/textures/blocks/` 或改用 drtech 域 renderer；未使用的元素 renderer 可删 |
| futuremc 灯笼贴图 16×48 无 `.mcmeta` | `assets/futuremc/textures/blocks/lantern.png`、`soul_lantern.png` | 灯笼/灵魂灯笼可能出现拉伸或错帧 | 补 `.mcmeta` 或改成 16×16 |
| 作物合成器激活覆盖层 16×128 无 `.mcmeta` | `assets/gregtech/textures/blocks/machines/crop_synthesizer/overlay_front_active.png` | 激活覆盖层显示异常 | 补 `.mcmeta`（同目录 `_emissive` 已有） |
| `uti_golem` 战利品表引用不存在的物品 | `assets/drtech/loot_tables/entities/uti_golem.json` 的 `gregtech:meta_block_compressed_1531` | JEI MobInfo 插件加载时 `JsonSyntaxException`；掉落表无法解析 | 改成有效物品/`set_data` 形式或删除该 pool |
| LootGames 音效缺失 | `sounds.json` 的 `gol_*`/`ms_*`/`bomb_activated` 引用的 `sounds/lootgames/*.ogg` 不存在 | 对应事件无声音 | 补 ogg 或删条目 |
| 部分音效事件缺 `sounds.json` 条目 | `plasma_charge_sound`、`laser_bullet_shoot`、`lighter_place`、`plasma_launch`（ogg 文件存在） | 事件无声音 | 补 `sounds.json` 条目 |
| GT 无效配方日志 | 客户端 18 条：`LaserBending.init`、`BinneRecipes.init`、`MachineRecipes.load`、`CraftingRecipes.load`；专服当前复现 1 条 extractor | GT 记录 `Invalid recipe ...` 堆栈，不影响启动 | 逐条按 recipe map 与 DrTech 栈定位并修正/加 guard |
| `modelloader` 缺模型/贴图 | 依赖 `modelloader-1.0.0`：`multiblock_controller`、`textures/block/tree.png` | 日志报错，非 DrTech 资源 | 上游处理或忽略 |
| 级联世界生成、`Potentially Dangerous alternative prefix` | GT/DrTech 加载新区块；GT 对附属注册 meta item 前缀的提示 | 日志噪音 | 可在 `forge.cfg` 关闭级联日志；前缀提示无害 |

以上问题不影响 `build`、`runClient` 到主菜单、`runServer` 启动和停服。

## 阻断并入 GTQT 全体的问题（按当前顺序）

1. **Future MC 同名 + BogoSorter 冲突**
   - 全量候选含 `Future-MC-0.2.21.jar`（modid `futuremc`）；DrTech 内嵌 `futuremc:1.0.0`，两者同名。
   - DrTech 的 Future MC 子集缺少 `thedarkcolour.futuremc.container.ContainerBarrel`；原版 BogoSorter 1.6.2 / 1.6.4 只要看到 `futuremc` 已加载就登记该类，会在 `DefaultCompat.init` 失败。
   - 旧 183/185 候选的做法：移除原版 Future MC，改用 `bogosorter-1.6.2-barrelguard.jar`（`dev/pack/patch_bogo.py`）。代价是古残骸/木桶等原版内容缺失，会影响任务兑换。
2. **Forestry / Binnie's 依赖（使用 145/175 精简候选时）**
   - DrTech 的 `MetaTileEntutyLargeBeeHive`、`MetaTileEntityIndustrialApiary` 在 preInit 无条件注册并直接 import `forestry.*`；精简候选没有 Forestry/Binnie's，会 `NoClassDefFoundError`。
   - 把 Forestry 组加回来会重新触发下面的配方 ID 问题。
3. **Forestry / Extra Trees 配方 ID 随机化**
   - GT 的 `WoodRecipeLoader.registerWoodTypeRecipe(true, entry)` 使用 `entry.modid + "_pf" + GTUtility.generateRandomString(6)`；重启后 837 个配方名变化，批次被 quarantine。
   - 需在 `GTQT/GregTech` 改成稳定后缀后再恢复 Forestry 组。
4. **`@Mod` 依赖声明**
   - 目前只声明 `required-after:gregtech`；建议补 `required-after:enderio`、`required-after:endercore`、`required-after:forestry`、`after:genetics`、`after:gregtechfoodoption`。
5. **EnderIO 库（生产与 dev 的差异）**
   - 生产实例由 Forge LibraryManager 解出 AutoConfig/AutoSave/EnderCore-core；dev 环境必须手动放 `run/mods`（见上）。

## 复现与验收

```powershell
python -B dev/drtech/build.py --historical --source <DrTech-worktree> --steam-env D:\GTSteam-1.12.2 \
  --state work/gtqt19-drtech-new --gradle-home D:\GTSteam-1.12.2\.legacy-dev\gradle --offline compileJava
```

dev 客户端/专服：

```powershell
python -B work/gtqt19-drtech-new/run_client.py <DrTech-worktree> work/gtqt19-drtech-new/runclient-console.log
python -B work/gtqt19-drtech-new/run_server.py <DrTech-worktree> work/gtqt19-drtech-new/runserver-console.log
```

判断非阻断问题是否修复：对比 `run/logs/latest.log` 中 `[FML.TEXTURE_ERRORS]`、`Invalid recipe for recipe map`、`JsonSyntaxException` 的条目数；贴图类问题以客户端日志为准，专服不报。
