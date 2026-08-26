#!/usr/bin/env python3
"""Create a private, non-destructive Guided Resume Studio workspace."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


CANDIDATE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
TEMPLATE_ID = "lapiscv-professional-blue-one-page"


def fail(message: str) -> "NoReturn":
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def write_json_if_missing(path: Path, payload: object) -> bool:
    if path.exists():
        return False
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def parse_contact(raw: str) -> dict[str, object]:
    if "=" not in raw:
        fail(f"contact must be LABEL=VALUE, got {raw!r}")
    label, value = (part.strip() for part in raw.split("=", 1))
    if not label or not value:
        fail(f"contact label and value must both be non-empty: {raw!r}")
    return {"label": label, "value": value, "public": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Current private project/workspace root")
    parser.add_argument("--candidate-id", required=True, help="Lowercase safe id, e.g. li-ming")
    parser.add_argument("--name", required=True)
    parser.add_argument("--contact", action="append", required=True, help="Repeatable LABEL=VALUE")
    parser.add_argument("--career-stage", required=True)
    parser.add_argument("--locale", choices=("zh-CN", "en"), default="zh-CN")
    args = parser.parse_args()

    if not CANDIDATE_ID_RE.fullmatch(args.candidate_id):
        fail("candidate-id must match ^[a-z0-9][a-z0-9-]{0,62}$")

    contacts = [parse_contact(item) for item in args.contact]
    workspace = args.root.resolve() / "resume-workspace" / args.candidate_id
    knowledge = workspace / "knowledge"
    for directory in (knowledge, workspace / "jobs", workspace / "drafts", workspace / "outputs"):
        directory.mkdir(parents=True, exist_ok=True)

    profile = {
        "schema_version": "1.0",
        "candidate_id": args.candidate_id,
        "identity": {
            "display_name": args.name.strip(),
            "contacts": contacts,
            "career_stage": args.career_stage.strip(),
            "locale": args.locale,
        },
        "preferences": {
            "default_template": TEMPLATE_ID,
            "one_page": True,
            "do_not_disclose": [],
        },
        "facts": [],
    }
    source_manifest = {
        "schema_version": "1.0",
        "candidate_id": args.candidate_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "privacy": {
            "local_only": True,
            "copy_full_sources": False,
            "global_memory": False,
        },
        "sources": [],
    }

    created: list[str] = []
    profile_json = knowledge / "profile.json"
    if write_json_if_missing(profile_json, profile):
        created.append(str(profile_json))
    manifest_json = knowledge / "source-manifest.json"
    if write_json_if_missing(manifest_json, source_manifest):
        created.append(str(manifest_json))

    ledger = knowledge / "fact-ledger.jsonl"
    if not ledger.exists():
        ledger.touch()
        created.append(str(ledger))

    profile_md = knowledge / "profile.md"
    if not profile_md.exists():
        template_path = Path(__file__).resolve().parents[1] / "assets" / "candidate-profile-template.md"
        template = template_path.read_text(encoding="utf-8")
        contact_lines = "\n".join(f"- {item['label']}: {item['value']}" for item in contacts)
        heading = (
            f"# {args.name.strip()} 的候选人资料库\n\n"
            f"- 求职阶段：{args.career_stage.strip()}\n"
            f"- 默认语言：{args.locale}\n"
            f"- 联系方式：\n{contact_lines}\n\n"
            "> 仅在本工作区保存。填写后，逐条核对并同步到 profile.json；未经确认的数字、角色和成果不得进入正式简历。\n\n"
        )
        profile_md.write_text(heading + template, encoding="utf-8")
        created.append(str(profile_md))

    result = {
        "workspace": str(workspace),
        "created": created,
        "preserved_existing": not bool(created),
        "next": "Import or fill facts, then verify them before researching one target job.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
