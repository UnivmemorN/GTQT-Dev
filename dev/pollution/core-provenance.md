# 当前 Pollution 需要哪一份 GTQT-Core

截至 2026-11-12，在本次可读取的源码、历史依赖与公开分发中，尚未取得能编译 Pollution `9ed70ed` 的 Core。已取得的七月 Core 1.9.0 仍适用于复现七月源码。八月 30 日，作者移除了 Pollution 自己注册的 Sunnarium，把两条配方改为使用 Core 的材料。[上游变更](https://github.com/GTQT/Pollution/commit/950137a42a2e6309d6642295438a69cd6bf1cd0e)

## 可辨认的几个制品

| 来源 | 文件内部证据 |
| --- | --- |
| [Pollution 七月开发依赖](https://github.com/GTQT/Pollution/tree/d1611ce5dec0eac71c2d68cc86975db86c2e3112/libs) | 自报 `gtqtcore 1.9.0`，JAR SHA-256 为 `458029f1649d5b08a4e71be5820dddda4a4dc606524e0841996571ba87a09502`。包含 `meowmel.gtqtcore.api.unification.material.GTQTMaterials`，其公开字段中没有 `Sunnarium`。 |
| 本地 Gradle 转换缓存 | 三个重映射 JAR 的整包哈希各不相同。三份材料类与七月原件的类字节 SHA-256 都是 `3e9a467cc68c475db976acbb87b18dcd1d1169583f69af8b1a13b96840b836ca`。 |
| [CurseForge Core 1.8.8](https://www.curseforge.com/minecraft/mc-mods/gtqtcore/files/7042526) | 作者公开网盘的 1.8.8 包清单指定此文件。实际材料类位于 `keqing.gtqtcore.api.unification.GTQTMaterials`，JAR SHA-256 为 `c13929f5e722b81375d2b842f744a7a17cb58ce96028471a0d7bcd73103cfe41`。 |
| [作者早期 Modrinth 项目](https://api.modrinth.com/v2/project/gtqtcore/version) | 公开接口列出一份 2023 年的 1.0.0。实际 JAR 也是 `keqing` 包，SHA-256 为 `745b059d0fe699c284247ae3556465f2b6c2fadbefa13237f9813005632bfbc8`。 |

## 查过哪些来源

- 对 GTQT 组织、作者和相关 fork 的 60 个可检出仓库读取分支、标签及相关 PR 的历史。按 Git 对象去重后，打开 549 个 JAR 和 17 个 ZIP 的归档目录，搜索材料类、Core 入口类及相应源码路径，并检查了 117 个内嵌归档条目（71 份不同内容）。58 个外层 JAR 命中 Core 类，57 个为旧 `keqing` 包，余下一个就是七月 JAR。这样也覆盖了早期改名的本地依赖和历史测试包。[异名依赖实例](https://github.com/GTQT/Pollution/blob/1309f5599dd788a71a6bf88ab4da9ee215625cf3/libs/gtqtcore-1.0.jar) · [历史 alpha 包](https://github.com/627e/GT-QuantumTransition/blob/3accde1720f4158ebee84a8c7690cc84c20ec9e2/GTQT-alpha%201.0.2.zip)
- 另查协作账号的仓库，读取与上述样本去重后的 29 份七月以来的额外归档。GTQT 组织和作者账号下 36 个仓库的公开发布附件与仍可下载的流水线制品也单独核对，实际检查 13 个 Release JAR、4 个 Actions ZIP 及其中的 16 个 JAR，均未找到目标类。[GTQT 组织](https://github.com/GTQT) · [Supergiant 流水线](https://github.com/GTQT/Applied-Energistics-2-Supergiant/actions)
- 从作者维护的下载文档进入夸克分享，目录列出 22 个归档，最高可见版本为 1.8.8。该包清单引用上表的旧 Core。官方文档的 1.9.x 更新页只有“总述”标题。CurseForge 整合包文件列表最高为 1.8.7，作者在 XyeBBS 的下载页列出 1.8.1。[官方下载页](https://docs.qq.com/aio/DRFhDRXZ5dnV0ZEtu?p=cfkvm9e11SgLDll0qAeKnu) · [夸克分享](https://pan.quark.cn/s/bbdad8b57e9e) · [1.9.x 更新页](https://docs.qq.com/aio/DRFhDRXZ5dnV0ZEtu?p=iTB8ewjS8nyMTeDeTMgpth) · [CurseForge 整合包](https://www.curseforge.com/minecraft/modpacks/gregtech-quantum-transition/files/all) · [XyeBBS](https://www.xyebbs.com/res-id/gtqt/downloads)

58 个历史命中各自的仓库、提交、路径、Git blob 和实际类名已列入[历史制品索引](../../evidence/pollution-core-git.json)。另将异名文件和近期改动扩展到 63 个仓库，检查 9,146 个 Git 对象的文件头，包括无扩展名文件和潜在 LFS 指针，未检出更多候选。

另有一条能定位开发历史的线索。2026-06-15，喵呜版 GregTech 短暂提交了名为 `GTQTCore` 的 Git 子模块指针 `4013576adb9a0087d57e5ca530a9529fb12dd9e5`，没有配套的 `.gitmodules` 地址。当日即移除。尝试向公开的 Core、GregTech 及三个相关 Core 仓直接取此提交，Git 均返回 `not our ref`。这个指针早于八月的 API 迁移，单凭它不能判断哪份源码提供目标字段。[加入指针](https://github.com/GTQT/GregTech/commit/90d910292e6113d338ca923b150aa4c79d6b403b) · [移除指针](https://github.com/GTQT/GregTech/commit/25de6b45c343541506e248cfd2155a8758325576)

查询范围是能够取得的公开历史和本机实例。未公开的测试服、群文件、已失效的临时分享和不可达 Git 对象仍可能有另一份 Core。

## 拿到候选后如何核验

先将 `$candidate` 设为实际 JAR，在有 JDK 的 PowerShell 中运行：

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath $candidate
javap -public -s -classpath $candidate meowmel.gtqtcore.api.unification.material.GTQTMaterials
```

核对类内有名为 `Sunnarium` 的公开静态字段，其值可传入 GregTech 的 `Material` 参数。如果收到的是源码，先确认对应包名、字段声明、注册赋值和提交，再构建 JAR。[塔罗牌调用](https://github.com/GTQT/Pollution/blob/9ed70ed318c57e350cfcdf725c1eadda8f539789/src/main/java/meowmel/pollution/loaders/recipes/MagicIntegrationRecipes.java#L421-L429) · [神秘配方调用](https://github.com/GTQT/Pollution/blob/9ed70ed318c57e350cfcdf725c1eadda8f539789/src/main/java/meowmel/pollution/loaders/recipes/ThaumcraftRecipes.java#L53)

本轮用当前 Pollution、十月喵呜版 GregTech 与七月 Core 重新执行了离线 `compileJava`。两处静态导入与两处使用共报四条诊断，均为找不到 `Sunnarium`。当前组合未生成新的 Pollution JAR，未运行该组合的专服。此前七月控制组在专服加载客户端 `IBakedModel` 的结果有单独记录。[构建命令与专服证据](README.md)

下一份候选应在独立检出中完成当前 Pollution 的完整构建、生产 JAR 加载、专服建档与保存，再将对应来源、哈希和结果写入 `pollutionCurrent`。七月历史组合继续使用自己的依赖。
