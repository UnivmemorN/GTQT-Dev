# GTQT 开发工作区

本仓协调 GTQT 的 Minecraft 1.12.2 开发（基线 `gtqt19`，见 `README.md`）。相邻仓库：`D:\GTQT-Core-1.12.2`、`D:\GTQT-DrTech-1.12.2`、`D:\GTQT-FoodOption-1.12.2`、`D:\GTQT-Galaxy-1.12.2`、`D:\GTQT-Pollution-1.12.2`、`D:\GTSteam-1.12.2`，以及 `work\src\` 下的锁定检出。

## 先加载 gtqt skill

只要任务属于本工作区的 GTQT 开发（模组代码、构建、联机联调、整包组装与验收、多方块/StructureChannel、GT5U 移植、依赖锁与 JAR 哈希等），在动手前必须先用 `skill` 工具加载 `gtqt`，然后按它的完整说明执行；不要只凭技能目录里的摘要行动，也不应等用户手动输入 `/gtqt`。

`gtqt` 覆盖：多仓依赖同步；GT5U→GTQT 机器与多方块移植规则；多方块 pattern/channel/orientation 检查；把分叉后的 jar 重建进 GTQTCore/libs；GTQTCore 构建与 headless 测试。

## 通用约定

- 先确认目标属于哪个仓与检出：从任务目录用 `git rev-parse --show-toplevel`、`git remote -v`、`git worktree list` 定位，并读取该仓的 `AGENTS.md`（若存在）。
- 1.12.2 的外部 API 以本地依赖 JAR 或源码为准，不要按更新版本的 Forge/GT 经验猜测。
- 修改后按任务风险跑验证：编译、单元测试、专服启动或双端联机；结论要给出实际执行过的命令与结果。
- 不发布、不打 tag、不改版本号；提交与推送只在用户明确要求时进行。
