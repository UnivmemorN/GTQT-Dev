# GTQT-Dev

本仓协调 GTQT 组织的 Minecraft 1.12.2 开发。自 2026-11-16 起，所有修复、功能开发和整包联调均从组织仓新版及其已验收依赖开始。唯一开发基线为 `gtqt19`。[源码提交和双端 JAR 清单](workspace.lock.json) · [联机验收记录](evidence/gtqt19-acceptance.json)

## 开发入口

使用 Python 3.11+，在仓库根目录运行：

```powershell
python -B tools/workspace.py check
python -B tools/workspace.py list
python -B tools/workspace.py checkout gtqtcore
python -B tools/workspace.py checkout pollution
```

`checkout` 会在 `work/src/<名称>` 检出已验收的组织仓提交。开发新修复前先同步相应组织仓，核对上游已合入的修改，从目标分支新开工作分支。依赖锁区分生产 JAR 的构建提交和后续仅改文档的提交。上游合并或替换 JAR 后，用新制品复验受影响的下游，再更新锁和验收记录。[Pollution 构建说明](dev/pollution/README.md)

## 当前可以复现什么

Forge 14.23.5.2860、Java 8 的开发组合包含新版 GTQTCore、喵呜版 GregTech、QuantumHue 和 Pollution。专服 25 个生产 JAR、客户端 26 个，已实测建档、客户端首次入服、保存停服、重启并重新进入同一存档。锁内逐端记录文件名与 SHA-256。检查实际实例时，把下面的路径换成该实例的生产模组目录：

```powershell
python -B tools/workspace.py check-mods server work/gtqt19/server/mods
python -B tools/workspace.py check-mods client work/gtqt19/client/mods
```

新版整包候选以这套双端组合为起点，按 1.8.8 清单分批加入模组，并单独验收脚本、任务和配置。实际纳入的文件、逐批联机记录及阻断见[新版整包组装与验收](docs/gtqt19-pack.md)。

## 已退役的七月兼容版

七月 Core、为它开发的 Pollution 兼容分支和旧 183/185 件候选已退出开发、打包与验收。遇到依赖缺口或旧问题复现时，在新版对应的组织仓定位和修复。旧产物、存档与当时的测试记录仅供溯源。[历史记录](docs/historical-development.md) · [原依赖锁](evidence/historical-workspace.lock.json)
