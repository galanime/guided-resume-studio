from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_DIR / "scripts"


def run_script(name: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fixtures() -> tuple[dict, dict, dict]:
    profile = {
        "schema_version": "1.0",
        "candidate_id": "zhang-san",
        "identity": {
            "display_name": "张三",
            "contacts": [{"label": "邮箱", "value": "zhangsan@example.com", "public": True}],
            "career_stage": "应届生",
            "locale": "zh-CN",
        },
        "preferences": {
            "default_template": "lapiscv-professional-blue-one-page",
            "one_page": True,
            "do_not_disclose": [],
        },
        "facts": [
            {
                "fact_id": "fact-edu",
                "category": "education",
                "title": "信息管理学士",
                "description": "系统学习统计学与用户研究方法。",
                "status": "user_verified",
                "sources": [],
            },
            {
                "fact_id": "fact-campus",
                "category": "campus",
                "role": "产品负责人",
                "description": "访谈 20 名用户并推动原型迭代。",
                "metrics": ["20 名用户"],
                "status": "user_verified",
                "sources": [],
            },
        ],
    }
    ats_map = {
        "schema_version": "1.0",
        "keywords": [
            {"keyword_id": "kw-research", "term": "用户研究", "status": "covered", "fact_ids": ["fact-edu", "fact-campus"]},
            {"keyword_id": "kw-sql", "term": "SQL", "status": "gap", "fact_ids": []},
        ],
    }
    resume = {
        "schema_version": "1.0",
        "template_id": "lapiscv-professional-blue-one-page",
        "locale": "zh-CN",
        "document_title": "张三 - 产品经理",
        "output_basename": "target-resume",
        "header": {
            "display_name": "张三",
            "headline": "产品经理",
            "contacts": ["zhangsan@example.com"],
            "summary": "关注真实用户问题与 A&B 协作，基于证据推进决策。",
        },
        "sections": [
            {
                "section_id": "education",
                "title": "教育经历",
                "entries": [{
                    "title": "示例大学｜信息管理学士",
                    "meta": "2021.09–2025.06",
                    "bullets": [{
                        "text": "系统学习统计学与用户研究方法，完成多项课程调研。",
                        "fact_ids": ["fact-edu"],
                        "keyword_ids": ["kw-research"],
                        "rewrite_reason": "匹配岗位研究职责",
                        "emphasis": [{"text": "用户研究", "kind": "keyword"}],
                    }],
                }],
            },
            {
                "section_id": "campus",
                "title": "校园经历",
                "entries": [{
                    "title": "学生产品团队｜产品负责人",
                    "meta": "2023.03–2024.01",
                    "bullets": [{
                        "text": "用户洞察｜通过访谈 20 名用户收集反馈，整理需求优先级并推动原型迭代。",
                        "fact_ids": ["fact-campus"],
                        "keyword_ids": ["kw-research"],
                        "rewrite_reason": "采用问题、方法与结果结构",
                        "emphasis": [
                            {"text": "用户洞察｜", "kind": "label"},
                            {"text": "20 名用户", "kind": "metric"},
                        ],
                    }],
                }],
            },
        ],
    }
    return profile, ats_map, resume


class InitWorkspaceTests(unittest.TestCase):
    def test_init_is_non_destructive(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            result = run_script(
                "init_workspace.py", "--root", str(root), "--candidate-id", "zhang-san",
                "--name", "张三", "--contact", "邮箱=zhangsan@example.com",
                "--career-stage", "应届生",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            profile_path = root / "resume-workspace" / "zhang-san" / "knowledge" / "profile.json"
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            profile["identity"]["career_stage"] = "已修改"
            write_json(profile_path, profile)
            second = run_script(
                "init_workspace.py", "--root", str(root), "--candidate-id", "zhang-san",
                "--name", "张三", "--contact", "邮箱=other@example.com", "--career-stage", "覆盖尝试",
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            preserved = json.loads(profile_path.read_text(encoding="utf-8"))
            self.assertEqual(preserved["identity"]["career_stage"], "已修改")

    def test_rejects_unsafe_candidate_id(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            result = run_script(
                "init_workspace.py", "--root", raw, "--candidate-id", "../escape",
                "--name", "A", "--contact", "email=a@example.com", "--career-stage", "student",
            )
            self.assertEqual(result.returncode, 2)
            self.assertFalse((Path(raw).parent / "escape").exists())


class RenderTests(unittest.TestCase):
    def prepare(self, root: Path) -> tuple[Path, Path, Path, Path]:
        profile, ats_map, resume = fixtures()
        profile_path = root / "profile.json"
        ats_path = root / "ats-map.json"
        resume_path = root / "resume.json"
        output = root / "preview"
        write_json(profile_path, profile)
        write_json(ats_path, ats_map)
        write_json(resume_path, resume)
        return profile_path, ats_path, resume_path, output

    def test_preview_dynamic_sections_theme_and_html_escape(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            profile, ats_map, resume, output = self.prepare(Path(raw))
            result = run_script(
                "render_lapiscv.py", "--input", str(resume), "--profile", str(profile),
                "--ats-map", str(ats_map), "--output-dir", str(output), "--preview-only",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            rendered = (output / "target-resume.html").read_text(encoding="utf-8")
            self.assertIn("#1a56db", rendered)
            self.assertIn("Noto Sans CJK SC", rendered)
            self.assertIn('class="emphasis-label"', rendered)
            self.assertIn('class="emphasis-metric"', rendered)
            self.assertIn("A&amp;B", rendered)
            self.assertNotIn("项目经历", rendered)
            self.assertNotRegex(rendered, r"<strong[^>]*>[^<]*(?:2021|2025|example\.com)")
            self.assertFalse((output / "target-resume.pdf").exists())

    def test_formal_render_rejects_missing_approval(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            profile, ats_map, resume, output = self.prepare(Path(raw))
            result = run_script(
                "render_lapiscv.py", "--input", str(resume), "--profile", str(profile),
                "--ats-map", str(ats_map), "--output-dir", str(output),
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("requires --approval", result.stderr)
            self.assertFalse((output / "target-resume.pdf").exists())

    def test_formal_render_rejects_stale_approval_hash(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            profile, ats_map, resume, output = self.prepare(root)
            preview = run_script(
                "render_lapiscv.py", "--input", str(resume), "--profile", str(profile),
                "--ats-map", str(ats_map), "--output-dir", str(output), "--preview-only",
            )
            self.assertEqual(preview.returncode, 0, preview.stderr)
            manifest = json.loads((output / "preview-manifest.json").read_text(encoding="utf-8"))
            approval = manifest["approval_template"]
            approval.update({"approved": True, "approved_at": "2026-08-26T00:00:00Z", "approved_by": "test"})
            approval["content_sha256"] = "0" * 64
            approval_path = root / "approval.json"
            write_json(approval_path, approval)
            result = run_script(
                "render_lapiscv.py", "--input", str(resume), "--profile", str(profile),
                "--ats-map", str(ats_map), "--approval", str(approval_path), "--output-dir", str(output),
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("stale", result.stderr)
            self.assertFalse((output / "target-resume.pdf").exists())

    def test_gap_keyword_cannot_enter_resume(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            profile, ats_map, resume, output = self.prepare(root)
            content = json.loads(resume.read_text(encoding="utf-8"))
            content["sections"][0]["entries"][0]["bullets"][0]["keyword_ids"] = ["kw-sql"]
            write_json(resume, content)
            result = run_script(
                "render_lapiscv.py", "--input", str(resume), "--profile", str(profile),
                "--ats-map", str(ats_map), "--output-dir", str(output), "--preview-only",
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("gap", result.stderr)

    def test_unverified_fact_and_over_emphasis_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            profile, ats_map, resume, output = self.prepare(root)
            profile_value = json.loads(profile.read_text(encoding="utf-8"))
            profile_value["facts"][0]["status"] = "unverified"
            write_json(profile, profile_value)
            result = run_script(
                "render_lapiscv.py", "--input", str(resume), "--profile", str(profile),
                "--ats-map", str(ats_map), "--output-dir", str(output), "--preview-only",
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("not user_verified", result.stderr)

            profile_value["facts"][0]["status"] = "user_verified"
            write_json(profile, profile_value)
            resume_value = json.loads(resume.read_text(encoding="utf-8"))
            bullet = resume_value["sections"][0]["entries"][0]["bullets"][0]
            bullet["emphasis"] = [{"text": "系统学习统计学与用户研究方法", "kind": "keyword"}]
            write_json(resume, resume_value)
            result = run_script(
                "render_lapiscv.py", "--input", str(resume), "--profile", str(profile),
                "--ats-map", str(ats_map), "--output-dir", str(output), "--preview-only",
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("one third", result.stderr)

    def test_english_preview_and_safe_filename(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            profile, ats_map, resume = fixtures()
            profile["identity"].update({"display_name": "Alex Zhang", "locale": "en"})
            profile["identity"]["contacts"][0]["value"] = "alex@example.com"
            resume["locale"] = "en"
            resume["output_basename"] = "../unsafe"
            resume["header"].update({"display_name": "Alex Zhang", "headline": "Product Manager", "contacts": ["alex@example.com"]})
            paths = [root / name for name in ("profile.json", "ats-map.json", "resume.json")]
            for path, value in zip(paths, (profile, ats_map, resume)):
                write_json(path, value)
            result = run_script(
                "render_lapiscv.py", "--input", str(paths[2]), "--profile", str(paths[0]),
                "--ats-map", str(paths[1]), "--output-dir", str(root / "out"), "--preview-only",
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("safe filename", result.stderr)


if __name__ == "__main__":
    unittest.main()
