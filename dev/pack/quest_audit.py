"""Audit the original BQ/FTB quest definitions against a saved Forge 1.12.2 registry (nbtlib==2.0.4)."""
import argparse
from collections import Counter, defaultdict
import hashlib
from html import escape
import json
import os
from pathlib import Path
import re
from zipfile import ZipFile
from urllib.parse import quote

import nbtlib


def plain(obj):
    if isinstance(obj, dict):
        return {re.sub(r":\d+$", "", k): plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [plain(v) for v in obj]
    return obj


def title(value):
    return re.sub(r"§[0-9a-fk-or]", "", str(value), flags=re.I)


def item(value):
    if isinstance(value, str):
        fields = value.split()
        return {"id": fields[0], "Count": int(fields[1]) if len(fields) > 1 else 1,
                "Damage": int(fields[2]) if len(fields) > 2 else 0}
    return value


class Registry:
    def __init__(self, level):
        world = nbtlib.load(level)
        self.mods = {str(r["ModId"]): str(r["ModVersion"]) for r in world["FML"]["ModList"]}
        self.names = {}
        self.aliases = {}
        for kind in ("items", "blocks", "entities"):
            entry = world["FML"]["Registries"]["minecraft:" + kind]
            self.names[kind] = {str(row["K"]) for row in entry["ids"]} - set(map(str, entry["dummied"]))
            self.aliases[kind] = {str(row["K"]): str(row["V"]) for row in entry["aliases"]}
        fluids = {str(name) for name in world["forge"]["DefaultFluidList"]}
        self.names["fluids"] = fluids | {name.partition(":")[2] for name in fluids if ":" in name}

    def missing(self, kind, name):
        resolved = self.aliases.get(kind, {}).get(name, name)
        return bool(name) and resolved not in self.names[kind]


class Quest:
    def __init__(self, reg, qid, name, chapters):
        self.reg = reg
        self.record = {"id": qid, "name": title(name), "chapters": chapters}
        self.refs = []

    def add(self, role, kind, identifier, group=None, **details):
        self.refs.append({"role": role, "kind": kind, "id": str(identifier),
                          **({"group": group} if group is not None else {}), **details})

    def stack(self, role, raw, group=None, **details):
        stack = item(raw)
        name = stack.get("id", "")
        if not name:
            return
        tag = stack.get("tag", {})
        details = {"count": int(stack.get("Count", 1)), "meta": int(stack.get("Damage", 0)), **details}
        if stack.get("OreDict"):
            details["oreAlternative"] = stack["OreDict"]
        if name == "betterquesting:placeholder":
            self.add(role, "sourcePlaceholder", tag.get("orig_id", "unknown"), group,
                     **{**details, "meta": int(tag.get("orig_meta", 0))})
            return
        if self.reg.missing("items", name):
            self.add(role, "missingItem", name, group, **details)
        fluid = tag.get("FluidName")
        if fluid and self.reg.missing("fluids", fluid):
            self.add(role, "missingFluidInStack", fluid, group, container=name, **details)
        facade = tag.get("item")
        if name == "appliedenergistics2:facade" and isinstance(facade, str) and self.reg.missing("items", facade):
            self.add(role, "missingFacadeItem", facade, group, container=name, **details)

    def result(self):
        if not self.refs:
            return None
        concrete = [r for r in self.refs if r["kind"] not in ("sourcePlaceholder", "spaceTravelRequiresReview")]
        roles = sorted({r["role"] for r in concrete})
        kinds = {r["kind"] for r in self.refs}
        return {**self.record, "missingRoles": roles, "onlyIconMissing": roles == ["icon"],
                "onlySourcePlaceholder": kinds == {"sourcePlaceholder"}, "findings": self.refs}


def quest_files(archive):
    prefix = "overrides/config/"
    files = {name[len(prefix):]: archive.read(name) for name in archive.namelist()
             if name == prefix + "betterquesting/DefaultQuests.json" or
             (name.startswith(prefix + "ftbquests/normal/") and name.endswith(".snbt"))}
    if "betterquesting/DefaultQuests.json" not in files or "ftbquests/normal/chapters/index.snbt" not in files:
        raise ValueError("Expected the pack overrides archive with primary BetterQuesting and FTB Quests definitions")
    return files


def better_quests(data, reg, crates):
    root = plain(json.loads(data))
    chapters = defaultdict(list)
    for line in root["questLines"].values():
        chapter = title(line["properties"]["betterquesting"]["name"])
        for entry in line["quests"].values():
            chapters[entry["id"]].append(chapter)
    rows = []
    seen = set()
    for source in root["questDatabase"].values():
        ident = source["questID"]
        if ident in seen:
            raise ValueError(f"Duplicate BetterQuesting quest ID {ident}")
        seen.add(ident)
        props = source["properties"]["betterquesting"]
        q = Quest(reg, ident, props["name"], chapters[ident])
        q.record["taskLogic"] = props.get("tasklogic", "AND")
        if source.get("preRequisites"):
            q.record["prerequisites"] = source["preRequisites"]
            q.record["prerequisiteLogic"] = props.get("questlogic", "AND")
        q.stack("icon", props["icon"])
        for task in source["tasks"].values():
            typ, group = task["taskID"], task["index"]
            role = "optionalRequirement" if ":optional_" in typ else "requirement"
            details = {"taskType": typ, "entryLogic": task.get("entryLogic", "AND")}
            for stack in task.get("requiredItems", {}).values():
                q.stack(role, stack, group, ignoreNBT=bool(task.get("ignoreNBT", False)),
                        partialMatch=bool(task.get("partialMatch", True)), **details)
            for fluid in task.get("requiredFluids", {}).values():
                if reg.missing("fluids", fluid["FluidName"]):
                    q.add(role, "missingFluid", fluid["FluidName"], group, amount=fluid["Amount"], **details)
            for block in task.get("blocks", {}).values():
                if reg.missing("blocks", block["blockID"]):
                    q.add(role, "missingBlock", block["blockID"], group, meta=block["meta"], **details)
            if "target" in task and reg.missing("entities", task["target"]):
                q.add(role, "missingEntity", task["target"], group, **details)
            if typ == "bq_standard:location" and "advancedrocketry" not in reg.mods and 51 <= task["dimension"] <= 60:
                q.add(role, "spaceTravelRequiresReview", task["dimension"], group, location=task["name"], **details)
        for reward in source.get("rewards", {}).values():
            for key in ("rewards", "choices"):
                for stack in reward.get(key, {}).values():
                    role = "rewardChoice" if key == "choices" else "reward"
                    q.stack(role, stack, reward["index"])
                    crate = stack.get("tag", {}).get("type")
                    if stack.get("id") == "ftbquests:lootcrate" and crate in crates:
                        q.add("rewardPool", "poolContainsMissingEntry", crate, reward["index"], table=crates[crate])
        if row := q.result():
            rows.append(row)
    return len(seen), rows


def ftb_quests(files, reg):
    base = "ftbquests/normal/"

    def read(relative):
        return nbtlib.parse_nbt(files[base + relative].decode("utf-8-sig")).unpack()

    tables = []
    crates = {}
    table_ids = read("reward_tables/index.snbt")["index"]
    for ident in table_ids:
        table = read(f"reward_tables/{ident}.snbt")
        q = Quest(reg, ident, table.get("title", ""), [])
        for i, entry in enumerate(table["rewards"]):
            if "item" in entry:
                q.stack("rewardPool", entry["item"], i, count=int(entry.get("count", 1)))
        if row := q.result():
            tables.append(row)
            if crate := table.get("loot_crate", {}).get("string_id"):
                crates[crate] = ident
    count = 0
    rows = []
    for chapter in read("chapters/index.snbt")["index"]:
        directory = f"chapters/{chapter}/"
        chapter_name = title(read(directory + "chapter.snbt").get("title", chapter))
        for name in sorted(n[len(base):] for n in files if n.startswith(base + directory)):
            ident = Path(name).stem
            if ident in ("chapter", "index"):
                continue
            count += 1
            source = read(name)
            q = Quest(reg, ident, source.get("title", ""), [chapter_name])
            if not q.record["name"]:
                q.record["titleSource"] = "FTB generated; no title in the source file"
            if "icon" in source:
                q.stack("icon", source["icon"])
            for group in source.get("tasks", []):
                for entry in group.get("items", []):
                    q.stack("requirement", entry["item"], group["uid"], taskType=group["type"],
                            consumeItems=bool(group.get("consume_items", False)),
                            alternatives=len(group["items"]))
            for entry in source.get("rewards", []):
                if "item" in entry:
                    q.stack("reward", entry["item"], entry["uid"], count=int(entry.get("count", 1)))
                    stack = item(entry["item"])
                    crate = stack.get("tag", {}).get("type")
                    if stack.get("id") == "ftbquests:lootcrate" and crate in crates:
                        q.add("rewardPool", "poolContainsMissingEntry", crate, entry["uid"], table=crates[crate])
            if row := q.result():
                rows.append(row)
    return count, rows, len(table_ids), tables, crates


ROLE_NAMES = {"requirement": "需求", "optionalRequirement": "可选需求", "reward": "奖励",
              "rewardChoice": "可选奖励", "rewardPool": "奖池", "icon": "图标"}


def markdown_table(rows):
    lines = ["| 任务 ID | 名称 | 涉及内容 | 原定义中的对象（每类一例） |",
             "| --- | --- | --- | --- |"]
    for row in sorted(rows, key=lambda r: r["id"]):
        examples = {}
        for f in row["findings"]:
            role = ROLE_NAMES[f["role"]]
            if f["kind"] == "sourcePlaceholder":
                role = "原占位·" + role
            elif f["kind"] == "spaceTravelRequiresReview":
                role = "维度待核"
            elif f["kind"] in ("missingFluidInStack", "missingFluid"):
                role += "·流体"
            elif f["kind"] == "poolContainsMissingEntry":
                role = "关联奖池缺项"
            elif f["kind"] == "missingEntity":
                role += "·实体"
            value = "`" + str(f["id"]) + "`"
            if f.get("meta", 0):
                value += "@" + str(f["meta"])
            if f.get("count", 1) != 1:
                value += " × " + str(f["count"])
            if "amount" in f:
                value += " × " + str(f["amount"]) + " mB"
            if f.get("oreAlternative"):
                value += "（矿辞 `" + f["oreAlternative"] + "`）"
            examples.setdefault(role, [])
            if value not in examples[role]:
                examples[role].append(value)
        roles = "、".join(examples)
        example_text = "<br>".join(f"{role} {values[0]}" + (f" 等 {len(values)} 项" if len(values) > 1 else "")
                                   for role, values in examples.items())
        name = escape(row["name"]).replace("|", "&#124;").replace("\n", " ") or "（原文件未单写标题）"
        lines.append(f"| `{row['id']}` | {name} | {roles} | {example_text} |")
    return lines


def write_markdown(path, report, json_name):
    c = report["counts"]
    bq = report["betterQuesting"]
    confirmed = sum(bool(q["missingRoles"]) for q in bq)
    lines = ["# 1.8.8 任务书在 1.9 联机候选中的缺项", "",
             f"按验收存档的 {c['worldModIds']} 个模组 ID 核对。BetterQuesting 的 {c['betterQuesting']:,} 个任务中，"
             f"下表列出 {len(bq)} 个。{confirmed} 个存在具体对象或关联奖池缺项，其中 {c['betterQuestingOnlyIconMissing']} 个只缺图标。"
             f"另有 {c['betterQuestingOnlySourcePlaceholder']} 个只含原任务书已经写入的占位。", "",
             "角色按原定义标注，同一个任务可同时涉及需求、奖励和图标。可选需求、OR 条件及矿辞允许其他判定路径。"
             "维度待核条目保留旧地点名和维度编号。仅缺图标、部分奖励或个别抽奖条目均不能据以认定整项任务无法完成。"
             f"全部对象、数量、元数据、任务前置和原始文件摘要见[机器可读清单]({json_name})。", "",
             f"## BetterQuesting（{len(bq)} 个任务）", "", *markdown_table(bq), "",
             f"## FTB Quests（{c['ftbQuests']} 个任务中列出 {c['ftbQuestsListed']} 个）", "",
             *markdown_table(report["ftbQuests"]), "",
             f"## FTB 奖池（{c['ftbRewardTables']} 张表中列出 {c['ftbRewardTablesListed']} 张）", "",
             *markdown_table(report["ftbRewardTables"]), ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("overrides", "level", "output"):
        parser.add_argument("--" + arg, type=Path, required=True)
    parser.add_argument("--markdown", type=Path, help="companion Markdown table alongside the JSON")
    args = parser.parse_args()
    if args.markdown and args.markdown.resolve() == args.output.resolve():
        parser.error("Choose distinct Markdown and JSON output files")
    with ZipFile(args.overrides) as archive:
        files = quest_files(archive)
    reg = Registry(args.level)
    ftb_count, ftb, table_count, tables, crates = ftb_quests(files, reg)
    better_count, bq = better_quests(files["betterquesting/DefaultQuests.json"], reg, crates)
    with args.overrides.open("rb") as handle:
        archive_sha = hashlib.file_digest(handle, "sha256").hexdigest()
    status = {}
    for role in ("requirement", "optionalRequirement", "reward", "rewardChoice", "rewardPool", "icon"):
        status[role] = sum(role in row["missingRoles"] for row in bq)
    kind_counts = Counter(kind for row in bq for kind in {f["kind"] for f in row["findings"]})
    namespaces = defaultdict(set)
    for row in [*bq, *ftb, *tables]:
        for finding in row["findings"]:
            if finding["kind"] in ("missingItem", "missingBlock", "missingEntity", "missingFacadeItem"):
                name = finding["id"]
                namespaces[name.partition(":")[0]].add(name)
    registries = reg.names["blocks"] | reg.names["items"] | reg.names["entities"]
    available_namespaces = {key.partition(":")[0] for key in registries}
    report = {"inputs": {"nbtlib": nbtlib.__version__, "overridesSha256": archive_sha,
                         "levelDatSha256": hashlib.sha256(args.level.read_bytes()).hexdigest(),
                         "questFileSha256": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}},
              "counts": {"worldModIds": len(reg.mods), "betterQuesting": better_count, "betterQuestingListed": len(bq),
                         "betterQuestingWithMissingRole": status, "ftbQuests": ftb_count, "ftbQuestsListed": len(ftb),
                         "betterQuestingByFinding": dict(sorted(kind_counts.items())),
                         "betterQuestingOnlyIconMissing": sum(r["onlyIconMissing"] for r in bq),
                         "betterQuestingOnlySourcePlaceholder": sum(r["onlySourcePlaceholder"] for r in bq),
                         "ftbRewardTables": table_count, "ftbRewardTablesListed": len(tables)},
              "method": "Direct object IDs and aliases are checked against Forge registry and fluid snapshots. "
                        "A sourcePlaceholder comes from the original quest file. A poolContainsMissingEntry flags a possible draw. "
                        "Reported task types, OR alternatives and ore dictionary keys do not establish that a whole quest is blocked. "
                        "Dimension travel entries require independent provider checks. Metadata and recipe attainability were not tested.",
              "futuremc": {"loaded": "futuremc" in reg.mods,
                           "registeredItems": sorted(n for n in reg.names["items"] if n.startswith("futuremc:")),
                           "registeredBlocks": sorted(n for n in reg.names["blocks"] if n.startswith("futuremc:"))},
              "missingObjectIdsByNamespace": {name: {"listedAsMod": name in reg.mods,
                                      "hasOtherRegisteredObjects": name in available_namespaces, "missingIds": sorted(ids)}
                                      for name, ids in sorted(namespaces.items())},
              "betterQuesting": bq, "ftbQuests": ftb, "ftbRewardTables": tables}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.markdown:
        link = Path(os.path.relpath(args.output.resolve(), args.markdown.resolve().parent)).as_posix()
        write_markdown(args.markdown, report, quote(link))
    print(json.dumps(report["counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
