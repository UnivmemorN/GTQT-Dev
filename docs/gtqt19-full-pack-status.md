# GTQT 1.12.2 全包运行状态

记录时间：2026-11-20

## 结论

**全包可以启动、客户端可以进入服务器，但还不能判定为“正常运行”。**

当前状态是“启动/进服已验证”，仍存在配方注册失败、CraftTweaker 脚本失败、配方 ID 缺失和日志错误，部分内容会缺配方或行为不正确。

## 当前组合

| 项目 | 状态 |
|---|---|
| 实例 | `work/gtqt19-pack-new/player-allmods` |
| 服务端 mods | 158 |
| 客户端 mods | 188 |
| 客户端实际 Forge mods | 223 |
| GT | `master-gtqt` `c44ca65`（PR #40 已合并） |
| GT 运行 JAR SHA-256 | `c5726857c06a89b7598925d5abc8efb19bf4b9b81e47522df07bdc2b42257ea0` |
| GTFO | PR #1（未合并） |
| GTFO JAR SHA-256 | `3b7fdddfde689e4a1ede9ad469a2a7483bf08ae2de9a2a2173d99f909d01960b` |
| `gregtech:tic_integration` | `true` |
| BOP 木材集成 | 已启用，修复版 GTFO |

## 已验证

- 专服启动：

```text
Done (4.218s)! For help, type "help" or "?"
```

- BOP 128 栈断言：

```text
GTQT_BOP_WOOD_OK species=16 stacks=128 dead_log=ok
```

- 客户端加载：

```text
Forge Mod Loader has successfully loaded 223 mods
GTQT_PACK_CLIENT_OK phase=create ... chunk=45,-11 validChunkTicks=100
```

- 无 `Planks cannot be empty`
- 无 `TinkerAPIException`

## 未验证

- 客户端 **reload** 阶段尚未完成验收
- 保存退出后重新进入世界
- BOP / 匠魂内容的实际配方可用性（目前只验证了栈和启动）
- 长时间运行与完整玩法回归

## 已知问题

### P1：CraftTweaker 客户端脚本失败

客户端 create 阶段出现 7 个脚本错误：

- `enderio/conduit.zs`
- `enderio/enderio.zs`
- `IronChest.zs`
- `JeiSweep.zs`
- `StorageDrawers.zs`
- `TConstruct/Cast.zs`
- `thaumcraft/thaumstic.zs`

典型错误：

```text
[crafttweaker]: Error executing ...: Bad type on operand stack
```

影响：对应脚本中的配方调整可能没有生效。

### P1：GT 配方注册失败

服务端 create 阶段仍有：

| RecipeMap | 次数 |
|---|---:|
| `sifter` | 16 |
| `industrial_infusion_recipes` | 5 |
| `heat_chemical_reactor` | 2 |
| `replicator` | 1 |

`sifter` 的已知原因是高筛产配方实际生成 7 个输出，而 `SIFTER_RECIPES` 上限为 6；其余需要逐项定位。

影响：对应机器会缺少配方，或配方被跳过。

### P1：客户端配方 ID 缺失

create 阶段出现 2 个：

```text
theoneprobe:probe
theoneprobe:probenote
```

不影响进入世界，但属于配方注册表不一致。

### P2：TiC 弓 drawspeed 语义反向

PR #40 评论已指出：

- Tinkers 显示的是 `1f / drawspeed`
- drawspeed 越大，拉弓越快
- 当前 `mergeMaterial` 使用 `Math.min`，`calcBowStats` 也使用递减公式，两者都会选择更慢的拉弓速度

示例：aluminium 从 `1.0 -> 0.625`，拉弓时间从 1.0s 变成 1.6s。

建议后续单独 PR 修复：

- 合并改为 `Math.max`
- 修正 `MaterialStatCalc.calcBowStats`
- 数值断言 aluminium 的 drawspeed / 拉弓时间

### P2：PR #40 Javadoc / import 遗留

- `replaceStats` Javadoc 应说明 `Material#addStats` 不会重新触发 `MaterialEvent.StatRegisterEvent`，这是合并时避免其他 Mod 倍率监听器重复生效的合理取舍
- `IMaterialStats` 可以改为显式 import

### P2：Loot 表错误

服务端日志仍有：

- `Couldn't add GTLootEntryItem ... duplicate entry`：28
- `pollution:entities/blitz|blizz` 加载失败：4
- `Couldn't find resource table`：2

客户端也有大量 `Couldn't find resource table` 警告（约 103 条），主要来自第三方模组资源缺失，不阻断启动。

### P3：验收探针退出问题

全模组客户端 create 成功后，探针在 `returningToMenu` 等待连接关闭时可能挂住，导致验收脚本无法进入 reload 阶段。

这是测试探针清理路径的问题，不影响实际进服判定，但会影响完整 create/reload 自动化。

## 下游同步状态

已同步到 PR #40 合并提交 `c44ca6546e19fd2aa9844629bb53f9b983a41577`：

- `workspace.lock.json`
  - `gregtech.rev`: `c44ca6546e19fd2aa9844629bb53f9b983a41577`
  - runtime GT SHA-256: `c5726857c06a89b7598925d5abc8efb19bf4b9b81e47522df07bdc2b42257ea0`
- `GTQTCore/libs/gregtech-gtqt-1.12.2-1.9.0.jar`
  - 已替换为主混淆 JAR
  - `GTQTCore`: `.local-dev\gradle.cmd assemble test` 通过（47s）
- `work/gtqt19` 与 candidate 的 GT JAR 已替换
- candidate create 阶段使用新 JAR 通过：`chunk=-5,153`

注意：完整 baseline/candidate create+reload 仍未重跑，原因是验收探针退出问题；这与配方错误无关，但 evidence 的 `runtimeSetSha256` 已按新 JAR 更新。

## 下一步建议

1. 修复 7 个 CraftTweaker 脚本错误
2. 修复 GT sifter / industrial infusion / heat chemical / replicator 无效配方
3. 清理 `theoneprobe` 两个缺失配方 ID
4. 单独 PR 修复 TiC 弓 drawspeed 语义
5. 修复验收探针退出，补跑完整 create/reload，并复核 evidence

## 证据

- [启动日志](D:/GTQT-Dev/work/gtqt19-pack-new/player-allmods/evidence/bop-fix-server-probe.log)
- [客户端日志](D:/GTQT-Dev/work/gtqt19-pack-new/player-allmods/evidence/bop-fix-client-create.log)
- [BOP 验证](D:/GTQT-Dev/work/gtqt19-pack-new/player-allmods/README.md)
