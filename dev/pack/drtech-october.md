# 十月 GregTech 的 DrTech 与 SteamTech

`drtechOctober` 使用 DrTech 作者 `main` 的 `e530bc957baa05437a3a6c17c6a7f5fe18cbe0bf`。YOT 流体仓原先引用 `Textures.ME_INPUT_BUS`，十月 GregTech 已删除该字段和原贴图。此构建将仓口正面渲染改用同一版 GT 的 `FLUID_HATCH_INPUT_OVERLAY`。补后的 Java 文件按 LF 计算 SHA-256 为 `6d5b0c13a618decd4d8a130cba3ed1efc6303fb92c558441e37380a1ed5eda88`。[上游 YOT 仓](https://github.com/GTQT/DrTech/blob/e530bc957baa05437a3a6c17c6a7f5fe18cbe0bf/src/main/java/com/drppp/drtech/common/metaTileEntities/muti/mutipart/MetaTileEntityYotHatch.java#L70-L77) · [依赖锁](../../workspace.lock.json)

## 复跑构建

在协调仓根目录运行。`--source` 应为此组合单独检出的工作树，`--october-gregtech` 会校验并写入仓面与三个网络频道的适配。以下示例复用已经准备的 SteamTech 和 DrTech 工具环境，也可按原流程创建新的缓存。首次填充缓存时省略 `--offline`。[DrTech 工具准备](../drtech/README.md)

```powershell
git -C ../GTQT-DrTech-1.12.2 worktree add --detach ../GTQT-DrTech-October e530bc957baa05437a3a6c17c6a7f5fe18cbe0bf
$steam = '../GTSteam-1.12.2'
python -B dev/drtech/build.py --october-gregtech --source ../GTQT-DrTech-October --steam-env $steam --state ../.drtech-dev --gradle-home "$steam/.legacy-dev/gradle" --clean build
```

编译输入为 `gtOctober`、`gtfoJuly` 和 `model100`。构建成功后，`build/libs/drtech-1.8.9.jar` 是生产 JAR。`build/drtech-profile.json` 记录源码、适配文件、输入和当前产物的 SHA-256。带网络修复的生产 JAR 为 `8ad8ed5d064533269309009e5a5a766a57a1bbd1384daca14d22ead0e0954915`。上游构建器会写入不同的 ZIP 元数据，重复构建应分别记录当前 JAR 摘要。

专服跟踪玩家时需要编码三个发往客户端的包。旧版仅在物理客户端注册这三个 discriminator，专服发送时出现 `Undefined discriminator`。现在 `drtech_glider` 和 `drtech_wings` 都为 `SyncPacket` 登记原 ID 1，`drtech_hooked` 为 `PacketHookCapSync` 登记原 ID 4。专服在客户端方向登记编码所需的映射，物理客户端继续使用原消息处理器。其余三个频道已有相应方向的注册。[滑翔翼](https://github.com/GTQT/DrTech/blob/e530bc957baa05437a3a6c17c6a7f5fe18cbe0bf/src/main/java/com/drppp/drtech/common/glider/GliderNetwork.java#L21-L29) · [钩索](https://github.com/GTQT/DrTech/blob/e530bc957baa05437a3a6c17c6a7f5fe18cbe0bf/src/main/java/com/drppp/drtech/hooked/HookNetwork.java#L31-L40)

DrTech 还注册 `futuremc:1.0.0`，含紫水晶、灯笼、堆肥桶和快乐恶魂等可用内容。它和原版 Future MC 占用同一 modid。DrTech 的实现缺少原版 `thedarkcolour.futuremc.container.ContainerBarrel`。原版 BogoSorter 1.6.2 和 1.6.4 都仅凭 `futuremc` 已加载就登记该类，因而会在 `DefaultCompat.init` 失败。[DrTech 内嵌实现](https://github.com/GTQT/DrTech/blob/e530bc957baa05437a3a6c17c6a7f5fe18cbe0bf/src/main/java/com/drppp/futuremc/FutureMCMain.java)

`patch_bogo.py` 接受已校验的两个 BogoSorter 原件。补丁沿用原版 modid 判断，并检查原版木桶 class 资源存在后才登记其槽位布局。对两版产物逐项比对，只有 `com/cleanroommc/bogosorter/compat/DefaultCompat.class` 的内容变化。补后 JAR 支持用固定输入和 Gradle 8.5 中的 ASM 9.5 再生成同一 SHA-256。将对应补后 JAR 放入候选的 `mods`，每次只装一份 `bogosorter`。[生成器](patch_bogo.py) · [具体改动](PatchBogoBarrel.java)

```powershell
python -B dev/pack/patch_bogo.py --input ../downloads/bogosorter-1.6.2.jar --output ../candidate/bogosorter-1.6.2-barrelguard.jar --java-home "$steam/.legacy-dev/jdks/java17" --gradle-cache "$steam/.legacy-dev/gradle"
```

| 版本 | 原件 SHA-256 | 补后 SHA-256 |
| --- | --- | --- |
| 1.6.2 | `7e8edc3137e96f04d8e46a44e66737ec159a503c9e61894b3b3425fbddab12d1` | `77c3379239c834070c238a47cd9153be7e4b1aa91277e39a25b5c4eeae084e11` |
| 1.6.4 | `08286ce5971766c02e7ae522357b5ef4aa35b15bf9ee226053932c34582a8a53` | `b1ba2ef5d22cb5923ea2a83e6b962f2d5476793c91b889abc11c609a96d7add8` |

第一轮 SteamTech 使用已通过 Pollution 专服验收的作者七月 JAR `9f02c92878f91c113cc3edc2dc3c40ed0161edc731f2558a7ec1cfad07bd18ad`。另用十月 GT 清洁实编 SteamTech 上游 `ccbb394cfc155b8df24cff064cfa9c75ed7af9c1`，热力蒸发池第 70 和 273 行的两个 `StructureDefinition.builder()` 均编译失败。十月 GT 的该方法要求三个 `RelativeDirection` 实参。选用其他 SteamTech 构建需重新核对结构方向与实机成形。[上游蒸发池](https://github.com/GTQT/GregTech-SteamTech/blob/ccbb394cfc155b8df24cff064cfa9c75ed7af9c1/src/main/java/meowmel/gtsteam/common/metatileentities/multi/heat/MetaTileEntityHeatEvaporationPond.java#L65-L76) · [作者七月 JAR](https://github.com/GTQT/Pollution/blob/d1611ce5dec0eac71c2d68cc86975db86c2e3112/libs/gtsteam-1.9.0.jar)
