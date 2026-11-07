#!/usr/bin/env python3
"""Validate mycourse.work module-first course content.

Stdlib only (Python 3.9+). One file, so content repos can pin it by tag.

The rules follow what the platform actually reads; see schema/RULES.md in
mycourse-work/skills. Errors are things that break or silently change what a
learner gets. Warnings are things worth a look that the platform tolerates.

Targets can be any mix of:
  - a repo root (has courses/ and/or modules/): every course and every module
  - a course directory or its course.json
  - a module directory or its manifest.json

Or pass --changed with the files a PR touches; the validator works out which
courses and modules they affect.

Exit status: 0 no errors, 1 errors, 2 usage problem.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

VERSION = "1.0.0"

# ─── Rule data (keep in step with schema/*.schema.json) ─────────────────────

PLATFORM_QUESTION_TYPES = {"MULTIPLE_CHOICE", "MULTIPLE_RESPONSE", "MATCHING"}
# Not a platform type. The player falls through to single choice for it.
LEGACY_QUESTION_TYPES = {"TRUE_FALSE"}
LESSON_TYPES = {"content", "quiz", "section"}
REVEAL_MODES = {"immediate", "end-of-quiz", "never"}
EVIDENCE_MODES = {"off", "warn", "enforce"}
FULLSCREEN_VALUES = {"phone", "always", "off"}

COURSE_KEYS = {
    "$schema", "id", "title", "description", "coverImage", "estimatedDuration", "welcomePath", "modules",
    "quizPassingThreshold", "quizMaxAttempts", "quizRevealMode", "contentUnitLabel", "contentUnitLabelPlural",
    "sequentialProgression", "completionRecord", "completionEvidence", "evidenceWordsPerMinute",
}
COMPLETION_RECORD_KEYS = {
    "enabled", "title", "heading", "nameLabel", "referenceLabel", "requireName", "requireCaaId",
}
MODULE_KEYS = {"$schema", "id", "title", "description", "estimatedDuration", "tags", "lessons"}
LESSON_KEYS = {"id", "title", "type", "markdownPath", "quizPath"}
QUIZ_KEYS = {"$schema", "title", "type", "passingScore", "questions"}
QUESTION_KEYS = {
    "id", "questionNumber", "type", "question", "questionHtml", "answers", "matchOptions",
    "feedback", "feedbackHtml", "image", "imageAlt",
}
ANSWER_KEYS = {
    "id", "answerNumber", "text", "textHtml", "correct", "feedback", "feedbackHtml", "matchText", "matchTextHtml",
}

ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MARKDOWN_RESOURCE_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HTML_SOURCE_RE = re.compile(r"\b(?:src|href)=[\"']([^\"']+)[\"']", re.IGNORECASE)
# Same block match as the player's LessonRenderer: name line, then props up to the closing :::.
WIDGET_BLOCK_RE = re.compile(r":::widget\s+([^\n]+?)[ \t]*\n([\s\S]*?):::")
WIDGET_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")
DIRECTIVE_PROP_RE = re.compile(r"^([a-zA-Z0-9_-]+)\s*:\s*(.+)$")
REFLECTION_ID_RE = re.compile(r"class=[\"']reflection[\"'][^>]*data-id=[\"']([^\"']+)", re.IGNORECASE)
FENCE_RE = re.compile(r"^(```|~~~)")
FOCUS_HINT = "recommended for full-screen on phones"


# ─── Reporting ──────────────────────────────────────────────────────────────

class Report:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.issues: List[Dict[str, str]] = []
        self.stats = {"courses": 0, "modules": 0, "contentLessons": 0, "quizzes": 0, "questions": 0}
        self.checked_widgets: Set[Path] = set()

    def rel(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.repo_root).as_posix()
        except ValueError:
            return str(path)

    def add(self, severity: str, path: Path, message: str) -> None:
        self.issues.append({"severity": severity, "file": self.rel(path), "message": message})

    def error(self, path: Path, message: str) -> None:
        self.add("error", path, message)

    def warn(self, path: Path, message: str) -> None:
        self.add("warning", path, message)

    @property
    def errors(self) -> List[str]:
        return [f"{i['file']}: {i['message']}" for i in self.issues if i["severity"] == "error"]

    @property
    def warnings(self) -> List[str]:
        return [f"{i['file']}: {i['message']}" for i in self.issues if i["severity"] == "warning"]


# ─── Helpers ────────────────────────────────────────────────────────────────

def load_json(path: Path, report: Report) -> Optional[Dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        report.error(path, "file not found")
        return None
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        report.error(path, f"not valid JSON: {exc}")
        return None
    if not isinstance(value, dict):
        report.error(path, "JSON root must be an object")
        return None
    return value


def is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def require_text(obj: Dict[str, Any], key: str, path: Path, where: str, report: Report) -> Optional[str]:
    value = obj.get(key)
    if not is_text(value):
        report.error(path, f"{where}{key} must be a non-empty string")
        return None
    return value


def unknown_keys(obj: Dict[str, Any], known: Set[str], path: Path, where: str, report: Report) -> None:
    extra = sorted(k for k in obj if k not in known)
    if extra:
        report.warn(path, f"{where}unknown field(s) the platform does not read: {', '.join(extra)}")


def check_kebab(value: Optional[str], path: Path, where: str, report: Report) -> None:
    if value and not ID_RE.fullmatch(value):
        report.warn(path, f"{where}id should be kebab-case: {value!r}")


def local_path(base: Path, raw: str, repo_root: Path, path: Path, report: Report) -> Optional[Path]:
    """Resolve a relative reference. None for external links, anchors, or paths that escape the repo."""
    cleaned = raw.strip().split("#", 1)[0].split("?", 1)[0]
    if not cleaned or cleaned.startswith(("//", "http://", "https://", "mailto:", "tel:", "data:", "javascript:")):
        return None
    if cleaned.startswith("/"):
        report.error(path, f"path must be relative, got {raw!r}")
        return None
    candidate = (base / cleaned).resolve()
    try:
        candidate.relative_to(repo_root)
    except ValueError:
        report.error(path, f"path escapes the repository: {raw!r}")
        return None
    return candidate


def parse_directive_props(block: str) -> Dict[str, Any]:
    """Python port of the player's parseDirectiveProps (packages/core/utils/directive-props.ts)."""
    props: Dict[str, Any] = {}
    for line in block.split("\n"):
        match = DIRECTIVE_PROP_RE.match(line.strip())
        if not match:
            continue
        raw = match.group(2).strip()
        props[match.group(1)] = True if raw == "true" else False if raw == "false" else raw
    return props


def strip_code(text: str) -> str:
    """Blank out fenced code blocks so examples in code are not checked as live content."""
    out, fenced = [], None
    for line in text.split("\n"):
        m = FENCE_RE.match(line.lstrip())
        if fenced is None and m:
            fenced = m.group(1)
            out.append("")
        elif fenced is not None:
            if line.lstrip().startswith(fenced):
                fenced = None
            out.append("")
        else:
            out.append(line)
    return "\n".join(out)


# ─── Lessons, widgets ───────────────────────────────────────────────────────

def validate_markdown(path: Path, repo_root: Path, reflection_ids: Dict[str, Path], report: Report) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        report.error(path, f"cannot read lesson: {exc}")
        return
    if text.startswith("﻿"):
        text = text[1:]
    if not text.strip():
        report.error(path, "lesson is empty")
        return

    first = text.lstrip().split("\n", 1)[0].rstrip()
    if first == "---":
        # LessonRenderer runs marked.parse on the raw file: front matter shows up as text.
        report.error(path, "YAML front matter is not supported (the player shows it as text); "
                           "put metadata in manifest.json")
    elif not re.match(r"^# \S", first):
        report.warn(path, "first line should be the lesson title as '# Title'")

    live = strip_code(text)
    resources = [m.group(1).strip().split(maxsplit=1)[0].strip("<>\"") for m in MARKDOWN_RESOURCE_RE.finditer(live)]
    resources.extend(m.group(1).strip() for m in HTML_SOURCE_RE.finditer(live))
    for raw in resources:
        if raw.startswith("/"):
            # Root-relative URLs (e.g. /courses/...) are legacy-format paths; they are not files in this repo.
            report.warn(path, f"root-relative link {raw!r}: use a path relative to the lesson")
            continue
        candidate = local_path(path.parent, raw, repo_root, path, report)
        if candidate is not None and not candidate.exists():
            report.error(path, f"referenced file does not exist: {raw}")

    for match in WIDGET_BLOCK_RE.finditer(live):
        name = match.group(1).strip()
        where = f"widget {name!r}: "
        if not WIDGET_NAME_RE.fullmatch(name):
            report.error(path, f"{where}widget name must be letters, digits, '-' or '_'")
            continue
        widget_path = repo_root / "widgets" / f"{name}.html"
        if not widget_path.is_file():
            report.error(path, f"{where}not found at widgets/{name}.html")
        else:
            validate_widget_html(widget_path, report)
        props = parse_directive_props(match.group(2))
        for key in ("title", "description"):
            if not isinstance(props.get(key), str):
                report.warn(path, f"{where}missing {key}: prop (the phone activity card shows it)")
        if "fullscreen" in props:
            value = props["fullscreen"]
            if isinstance(value, bool):
                report.warn(path, f"{where}fullscreen: {str(value).lower()} works, but write "
                                  f"{'phone' if value else 'off'} instead")
            elif value.lower() not in FULLSCREEN_VALUES:
                report.error(path, f"{where}invalid fullscreen: {value!r} (use phone, always or off)")

    seen_here: Set[str] = set()
    for reflection_id in REFLECTION_ID_RE.findall(live):
        if reflection_id in seen_here or reflection_id in reflection_ids:
            other = reflection_ids.get(reflection_id, path)
            report.error(path, f"duplicate reflection data-id {reflection_id!r} (also in {report.rel(other)})")
        seen_here.add(reflection_id)
        reflection_ids.setdefault(reflection_id, path)


def validate_widget_html(path: Path, report: Report) -> None:
    if path in report.checked_widgets:
        return
    report.checked_widgets.add(path)
    try:
        html = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        report.warn(path, f"cannot read widget: {exc}")
        return
    # Plain substring checks: good enough for warnings.
    if "widget-ready" not in html:
        report.warn(path, "no widget-ready message (the player keeps Start disabled until it arrives)")
    if "widget-focus-optout" in html:
        return
    if "widget-mode" not in html:
        report.warn(path, f"no widget-mode handling ({FOCUS_HINT})")
    if "widget-focus-exit" not in html:
        report.warn(path, f"no Done button posting widget-focus-exit ({FOCUS_HINT})")


# ─── Quiz ───────────────────────────────────────────────────────────────────

def validate_answers(question: Dict[str, Any], qtype: Any, path: Path, where: str, report: Report) -> None:
    answers = question.get("answers")
    if not isinstance(answers, list) or len(answers) < 2:
        report.error(path, f"{where}answers must be an array of at least 2 objects")
        return

    answer_ids: Set[str] = set()
    correct_count = 0
    for index, answer in enumerate(answers, start=1):
        awhere = f"{where}answer {index}: "
        if not isinstance(answer, dict):
            report.error(path, f"{awhere}must be an object")
            continue
        unknown_keys(answer, ANSWER_KEYS | {"isCorrect"}, path, awhere, report)
        answer_id = require_text(answer, "id", path, awhere, report)
        require_text(answer, "text", path, awhere, report)
        if answer_id:
            if answer_id in answer_ids:
                report.error(path, f"{where}duplicate answer id {answer_id!r}")
            answer_ids.add(answer_id)
        if "isCorrect" in answer:
            report.error(path, f"{awhere}isCorrect is not read by the player; use correct")
        if "correct" in answer:
            if not isinstance(answer["correct"], bool):
                report.error(path, f"{awhere}correct must be true or false")
            elif answer["correct"]:
                correct_count += 1
        elif qtype != "MATCHING":
            report.warn(path, f"{awhere}no correct field; the grader treats it as false")
        if qtype == "MATCHING" and not is_text(answer.get("matchText")):
            report.error(path, f"{awhere}MATCHING answers need matchText")

    if qtype in {"MULTIPLE_CHOICE", "TRUE_FALSE"} and correct_count != 1:
        report.error(path, f"{where}{qtype} needs exactly one correct answer, found {correct_count}")
    if qtype == "MULTIPLE_RESPONSE" and correct_count < 1:
        report.error(path, f"{where}MULTIPLE_RESPONSE needs at least one correct answer")


def validate_quiz(path: Path, report: Report) -> None:
    quiz = load_json(path, report)
    if quiz is None:
        return
    report.stats["quizzes"] += 1
    unknown_keys(quiz, QUIZ_KEYS, path, "", report)
    require_text(quiz, "title", path, "", report)
    if quiz.get("type") != "quiz":
        report.error(path, 'top-level type must be "quiz"')
    if "passingScore" in quiz:
        report.warn(path, "passingScore is ignored; the pass mark is quizPassingThreshold in course.json")

    questions = quiz.get("questions")
    if not isinstance(questions, list) or not questions:
        report.error(path, "questions must be a non-empty array")
        return

    question_ids: Set[str] = set()
    for index, question in enumerate(questions, start=1):
        where = f"question {index}: "
        if not isinstance(question, dict):
            report.error(path, f"{where}must be an object")
            continue
        report.stats["questions"] += 1
        unknown_keys(question, QUESTION_KEYS, path, where, report)
        question_id = require_text(question, "id", path, where, report)
        if question_id:
            where = f"question {question_id!r}: "
            if question_id in question_ids:
                report.error(path, f"duplicate question id {question_id!r}")
            question_ids.add(question_id)
        require_text(question, "question", path, where, report)
        number = question.get("questionNumber")
        if number is not None and (not isinstance(number, int) or isinstance(number, bool) or number < 1):
            report.error(path, f"{where}questionNumber must be a whole number from 1")

        qtype = question.get("type")
        if qtype in LEGACY_QUESTION_TYPES:
            report.warn(path, f"{where}{qtype} is not a platform type; it plays as MULTIPLE_CHOICE, so use that")
        elif qtype not in PLATFORM_QUESTION_TYPES:
            report.error(path, f"{where}type must be one of {', '.join(sorted(PLATFORM_QUESTION_TYPES))}, "
                               f"got {qtype!r}")

        if not is_text(question.get("feedback")) and not is_text(question.get("feedbackHtml")):
            answers = question.get("answers")
            if isinstance(answers, list) and any(isinstance(a, dict) and is_text(a.get("feedback")) for a in answers):
                report.warn(path, f"{where}no question feedback; answer-level feedback is never shown by the player")
            else:
                report.warn(path, f"{where}no feedback; learners see no explanation")
        validate_answers(question, qtype, path, where, report)


# ─── Module, course ─────────────────────────────────────────────────────────

class ModuleResult:
    def __init__(self) -> None:
        self.ok_manifest = False
        self.reflections: Dict[str, Path] = {}


def validate_module(module_dir: Path, repo_root: Path, report: Report, cache: Dict[Path, ModuleResult]) -> ModuleResult:
    module_dir = module_dir.resolve()
    if module_dir in cache:
        return cache[module_dir]
    result = ModuleResult()
    cache[module_dir] = result

    manifest_path = module_dir / "manifest.json"
    manifest = load_json(manifest_path, report)
    if manifest is None:
        return result
    result.ok_manifest = True
    report.stats["modules"] += 1
    unknown_keys(manifest, MODULE_KEYS, manifest_path, "", report)

    module_id = require_text(manifest, "id", manifest_path, "", report)
    if module_id and module_id != module_dir.name:
        # sync-to-r2 uploads by folder name but registers the module under manifest.id.
        report.error(manifest_path, f"id {module_id!r} must match the folder name {module_dir.name!r}")
    check_kebab(module_id, manifest_path, "", report)
    require_text(manifest, "title", manifest_path, "", report)
    if not is_text(manifest.get("description")):
        report.warn(manifest_path, "no description (the module card shows it)")
    if "estimatedDuration" in manifest and not is_text(manifest["estimatedDuration"]):
        report.error(manifest_path, "estimatedDuration must be a non-empty string")
    tags = manifest.get("tags")
    if tags is not None and (not isinstance(tags, list) or not all(is_text(t) for t in tags)):
        report.error(manifest_path, "tags must be an array of strings")

    lessons = manifest.get("lessons")
    if not isinstance(lessons, list) or not lessons:
        report.error(manifest_path, "lessons must be a non-empty array")
        return result

    lesson_ids: Set[str] = set()
    for index, lesson in enumerate(lessons, start=1):
        where = f"lesson {index}: "
        if not isinstance(lesson, dict):
            report.error(manifest_path, f"{where}must be an object")
            continue
        lesson_id = require_text(lesson, "id", manifest_path, where, report)
        if lesson_id:
            where = f"lesson {lesson_id!r}: "
            if lesson_id in lesson_ids:
                report.error(manifest_path, f"duplicate lesson id {lesson_id!r}")
            lesson_ids.add(lesson_id)
            if "|||" in lesson_id:
                report.error(manifest_path, f"{where}legacy '|||' lesson id; the platform adds the module prefix")
            else:
                check_kebab(lesson_id, manifest_path, where, report)
        unknown_keys(lesson, LESSON_KEYS, manifest_path, where, report)
        require_text(lesson, "title", manifest_path, where, report)

        lesson_type = lesson.get("type")
        if lesson_type not in LESSON_TYPES:
            report.error(manifest_path, f"{where}type must be content, quiz or section, got {lesson_type!r}")
            continue
        if lesson_type == "section":
            continue
        key = "markdownPath" if lesson_type == "content" else "quizPath"
        raw = require_text(lesson, key, manifest_path, where, report)
        if not raw:
            continue
        target = local_path(module_dir, raw, repo_root, manifest_path, report)
        if target is None:
            continue
        try:
            target.relative_to(module_dir)
        except ValueError:
            # The edge router serves lesson files from inside the module folder only.
            report.error(manifest_path, f"{where}{key} must stay inside the module folder: {raw!r}")
            continue
        if not target.is_file():
            report.error(manifest_path, f"{where}{key} does not exist: {raw}")
        elif lesson_type == "content":
            report.stats["contentLessons"] += 1
            validate_markdown(target, repo_root, result.reflections, report)
        else:
            validate_quiz(target, report)
    return result


def validate_course(course_file: Path, repo_root: Path, report: Report, cache: Dict[Path, ModuleResult]) -> None:
    course = load_json(course_file, report)
    if course is None:
        return
    report.stats["courses"] += 1
    course_dir = course_file.parent
    unknown_keys(course, COURSE_KEYS, course_file, "", report)

    course_id = require_text(course, "id", course_file, "", report)
    if course_id and course_id != course_dir.name:
        # sync-to-r2 uploads by folder name but registers the course under course.id.
        report.error(course_file, f"id {course_id!r} must match the folder name {course_dir.name!r}")
    check_kebab(course_id, course_file, "", report)
    require_text(course, "title", course_file, "", report)
    if not is_text(course.get("description")):
        report.warn(course_file, "no description (the course card shows it)")
    for key in ("estimatedDuration", "coverImage", "contentUnitLabel", "contentUnitLabelPlural"):
        if key in course and not is_text(course[key]):
            report.error(course_file, f"{key} must be a non-empty string")

    threshold = course.get("quizPassingThreshold")
    if threshold is not None and (not is_number(threshold) or not 0 <= threshold <= 100):
        report.error(course_file, "quizPassingThreshold must be a number from 0 to 100")
    attempts = course.get("quizMaxAttempts")
    if attempts is not None and (not isinstance(attempts, int) or isinstance(attempts, bool) or attempts < 1):
        report.error(course_file, "quizMaxAttempts must be a whole number from 1")
    if "quizRevealMode" in course and course["quizRevealMode"] not in REVEAL_MODES:
        report.error(course_file, f"quizRevealMode must be one of {', '.join(sorted(REVEAL_MODES))}")
    if "completionEvidence" in course and course["completionEvidence"] not in EVIDENCE_MODES:
        report.error(course_file, f"completionEvidence must be one of {', '.join(sorted(EVIDENCE_MODES))}")
    wpm = course.get("evidenceWordsPerMinute")
    if wpm is not None and (not is_number(wpm) or wpm <= 0):
        report.error(course_file, "evidenceWordsPerMinute must be a number above 0")
    if "sequentialProgression" in course and not isinstance(course["sequentialProgression"], bool):
        report.error(course_file, "sequentialProgression must be true or false")
    record = course.get("completionRecord")
    if record is not None:
        if not isinstance(record, dict) or not isinstance(record.get("enabled"), bool):
            report.error(course_file, "completionRecord must be an object with enabled: true or false")
        else:
            unknown_keys(record, COMPLETION_RECORD_KEYS, course_file, "completionRecord: ", report)

    welcome = course.get("welcomePath")
    if welcome is not None:
        if not is_text(welcome):
            report.error(course_file, "welcomePath must be a non-empty string")
        else:
            welcome_path = local_path(course_dir, welcome, repo_root, course_file, report)
            if welcome_path is not None:
                if not welcome_path.is_file():
                    report.error(course_file, f"welcomePath does not exist: {welcome}")
                else:
                    validate_markdown(welcome_path, repo_root, {}, report)

    modules = course.get("modules")
    if not isinstance(modules, list) or not modules:
        report.error(course_file, "modules must be a non-empty array of module ids")
        return

    seen: Set[str] = set()
    reflections: Dict[str, Path] = {}
    for index, module_id in enumerate(modules, start=1):
        if not is_text(module_id):
            report.error(course_file, f"modules entry {index} must be a module id string")
            continue
        if module_id in seen:
            report.error(course_file, f"module {module_id!r} is listed twice")
            continue
        seen.add(module_id)
        module_dir = repo_root / "modules" / module_id
        if not (module_dir / "manifest.json").is_file():
            report.error(course_file, f"module {module_id!r} not found at modules/{module_id}/manifest.json")
            continue
        result = validate_module(module_dir, repo_root, report, cache)
        for reflection_id, where in result.reflections.items():
            if reflection_id in reflections:
                report.error(where, f"reflection data-id {reflection_id!r} is also used in "
                                    f"{report.rel(reflections[reflection_id])} in the same course")
            else:
                reflections[reflection_id] = where


# ─── Target resolution ──────────────────────────────────────────────────────

def find_repo_root(start: Path) -> Optional[Path]:
    for p in (start, *start.parents):
        if (p / "modules").is_dir() or (p / "courses").is_dir():
            return p
    return None


def list_dirs(path: Path) -> List[Path]:
    return sorted(p for p in path.iterdir() if p.is_dir() and not p.name.startswith(".")) if path.is_dir() else []


def courses_using(repo_root: Path) -> Dict[str, Set[str]]:
    """module id -> course folder names that list it."""
    usage: Dict[str, Set[str]] = {}
    for course_dir in list_dirs(repo_root / "courses"):
        try:
            data = json.loads((course_dir / "course.json").read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError):
            continue
        modules = data.get("modules") if isinstance(data, dict) else None
        for module_id in modules if isinstance(modules, list) else []:
            if isinstance(module_id, str):
                usage.setdefault(module_id, set()).add(course_dir.name)
    return usage


def resolve_changed(changed: Iterable[str], repo_root: Path) -> Tuple[List[Path], List[Path]]:
    """Changed files (repo-relative) -> (course dirs, module dirs) to validate."""
    courses: Set[str] = set()
    modules: Set[str] = set()
    widgets_changed = False
    for raw in changed:
        parts = Path(raw.strip()).parts
        if len(parts) >= 2 and parts[0] == "courses":
            courses.add(parts[1])
        elif len(parts) >= 2 and parts[0] == "modules":
            modules.add(parts[1])
        elif len(parts) >= 2 and parts[0] == "widgets":
            widgets_changed = True
    usage = courses_using(repo_root)
    if widgets_changed:
        # Cheap and safe: any lesson might embed the widget.
        courses |= {d.name for d in list_dirs(repo_root / "courses")}
    for module_id in modules:
        courses |= usage.get(module_id, set())
    course_dirs = [repo_root / "courses" / c for c in sorted(courses) if (repo_root / "courses" / c).is_dir()]
    module_dirs = [repo_root / "modules" / m for m in sorted(modules) if (repo_root / "modules" / m).is_dir()]
    return course_dirs, module_dirs


def classify(target: Path) -> Tuple[str, Path]:
    """Return (kind, directory) where kind is course, module or repo."""
    if target.is_file():
        if target.name == "course.json":
            return "course", target.parent
        if target.name == "manifest.json":
            return "module", target.parent
        raise ValueError(f"not a course.json or manifest.json: {target}")
    if (target / "course.json").is_file():
        return "course", target
    if (target / "manifest.json").is_file() and target.parent.name == "modules":
        return "module", target
    if (target / "modules").is_dir() or (target / "courses").is_dir():
        return "repo", target
    if target.parent.name == "modules":
        return "module", target  # manifest.json missing: report it
    if target.parent.name == "courses":
        return "course", target  # course.json missing: report it
    raise ValueError(f"cannot tell what this is (no course.json, manifest.json, courses/ or modules/): {target}")


# ─── CLI ────────────────────────────────────────────────────────────────────

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("targets", nargs="*", type=Path, help="repo root, course dir/course.json, module dir/manifest.json")
    parser.add_argument("--repo-root", type=Path, help="repository root holding courses/, modules/ and widgets/")
    parser.add_argument("--changed", nargs="*", default=None, metavar="FILE",
                        help="repo-relative changed files; validates the courses and modules they affect")
    parser.add_argument("--changed-from", type=Path, metavar="LIST",
                        help="file with one changed path per line (same as --changed)")
    parser.add_argument("--json", action="store_true", help="print JSON")
    parser.add_argument("--github", action="store_true", help="also print GitHub Actions annotations")
    parser.add_argument("--version", action="version", version=f"validate_course.py {VERSION}")
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> Tuple[Dict[str, Any], int]:
    targets = [t.expanduser().resolve() for t in args.targets]
    changed: Optional[List[str]] = None
    if args.changed is not None or args.changed_from is not None:
        changed = list(args.changed or [])
        if args.changed_from:
            changed += [ln for ln in args.changed_from.read_text(encoding="utf-8").splitlines() if ln.strip()]

    if args.repo_root:
        repo_root = args.repo_root.expanduser().resolve()
    else:
        start = targets[0] if targets else Path.cwd().resolve()
        repo_root = find_repo_root(start if start.is_dir() else start.parent) or Path.cwd().resolve()
    if not targets and changed is None:
        raise ValueError("give a target or --changed")

    report = Report(repo_root)
    cache: Dict[Path, ModuleResult] = {}
    course_dirs: List[Path] = []
    module_dirs: List[Path] = []
    for target in targets:
        kind, directory = classify(target)
        if kind == "course":
            course_dirs.append(directory)
        elif kind == "module":
            module_dirs.append(directory)
        else:
            course_dirs += list_dirs(directory / "courses")
            module_dirs += list_dirs(directory / "modules")
    if changed is not None:
        extra_courses, extra_modules = resolve_changed(changed, repo_root)
        course_dirs += extra_courses
        module_dirs += extra_modules

    for course_dir in dict.fromkeys(course_dirs):
        validate_course(course_dir / "course.json", repo_root, report, cache)
    for module_dir in dict.fromkeys(module_dirs):
        validate_module(module_dir, repo_root, report, cache)

    result = {
        "ok": not report.errors,
        "version": VERSION,
        "errors": report.errors,
        "warnings": report.warnings,
        "issues": report.issues,
        "stats": report.stats,
    }
    return result, 0 if result["ok"] else 1


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    try:
        result, status = run(args)
    except (ValueError, OSError) as exc:
        print(f"validate_course.py: {exc}", file=sys.stderr)
        return 2
    if args.github:
        for issue in result["issues"]:
            level = "error" if issue["severity"] == "error" else "warning"
            message = issue["message"].replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
            print(f"::{level} file={issue['file']}::{message}")
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        s = result["stats"]
        print(f"{'PASS' if result['ok'] else 'FAIL'}: {s['courses']} courses, {s['modules']} modules, "
              f"{s['contentLessons']} lessons, {s['quizzes']} quizzes, {s['questions']} questions; "
              f"{len(result['errors'])} errors, {len(result['warnings'])} warnings")
        for message in result["errors"]:
            print(f"ERROR: {message}")
        for message in result["warnings"]:
            print(f"WARNING: {message}")
    return status


if __name__ == "__main__":
    sys.exit(main())
