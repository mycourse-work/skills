"""Tests for validate_course.py. Stdlib unittest; the schema-agreement tests need `jsonschema` and skip without it.

Run: python3 -m unittest discover -s course-validator/tests -v
"""

from __future__ import annotations

import copy
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "validate_course.py"
SCHEMA_DIR = HERE.parent.parent / "schema"

spec = importlib.util.spec_from_file_location("validate_course", SCRIPT)
vc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vc)

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - CI installs it
    Draft202012Validator = None

GOOD_WIDGET = (
    "<div id='app'></div><script>"
    "window.addEventListener('message',function(e){if(e.data.type==='widget-mode'){}});"
    "parent.postMessage({type:'widget-focus-exit'},'*');parent.postMessage({type:'widget-ready'},'*');"
    "</script>"
)

COURSE = {
    "id": "demo-course",
    "title": "Demo course",
    "description": "A course for tests.",
    "estimatedDuration": "1 hour",
    "welcomePath": "welcome.md",
    "quizPassingThreshold": 80,
    "quizRevealMode": "end-of-quiz",
    "modules": ["demo-module"],
}
MANIFEST = {
    "id": "demo-module",
    "title": "Demo module",
    "description": "A module for tests.",
    "tags": ["demo"],
    "lessons": [
        {"id": "intro", "title": "Intro", "type": "content", "markdownPath": "01-intro.md"},
        {"id": "quiz", "title": "Quiz", "type": "quiz", "quizPath": "quiz.json"},
    ],
}
QUIZ = {
    "title": "Demo quiz",
    "type": "quiz",
    "questions": [
        {
            "id": "q1",
            "type": "MULTIPLE_CHOICE",
            "question": "Pick one.",
            "feedback": "Because.",
            "answers": [
                {"id": "q1_a", "text": "Right", "correct": True},
                {"id": "q1_b", "text": "Wrong", "correct": False},
            ],
        },
        {
            "id": "q2",
            "type": "MULTIPLE_RESPONSE",
            "question": "Pick some.",
            "feedback": "Because.",
            "answers": [
                {"id": "q2_a", "text": "Yes", "correct": True},
                {"id": "q2_b", "text": "Also yes", "correct": True},
                {"id": "q2_c", "text": "No", "correct": False},
            ],
        },
        {
            "id": "q3",
            "type": "MATCHING",
            "question": "Match them.",
            "feedback": "Because.",
            "answers": [
                {"id": "q3_a", "text": "A", "matchText": "1", "correct": True},
                {"id": "q3_b", "text": "B", "matchText": "2", "correct": True},
            ],
        },
    ],
}
LESSON = (
    "# Intro\n\nHello.\n\n![A picture](./assets/pic.png)\n\n"
    ":::widget demo-widget\ntitle: Demo\ndescription: Try it.\n:::\n\n"
    '<div class="reflection" data-id="demo-reflection"><div class="reflection-prompt">Why?</div></div>\n'
)


class Repo:
    """A throwaway content repo built from the dicts above."""

    def __init__(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.course = copy.deepcopy(COURSE)
        self.manifest = copy.deepcopy(MANIFEST)
        self.quiz = copy.deepcopy(QUIZ)
        self.lesson = LESSON
        self.extra_files: dict[str, str] = {}

    def write(self) -> Path:
        c = self.root / "courses" / "demo-course"
        m = self.root / "modules" / "demo-module"
        (m / "assets").mkdir(parents=True, exist_ok=True)
        c.mkdir(parents=True, exist_ok=True)
        (self.root / "widgets").mkdir(exist_ok=True)
        (c / "course.json").write_text(json.dumps(self.course), encoding="utf-8")
        (c / "welcome.md").write_text("# Welcome\n\nHi.\n", encoding="utf-8")
        (m / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")
        (m / "quiz.json").write_text(json.dumps(self.quiz), encoding="utf-8")
        (m / "01-intro.md").write_text(self.lesson, encoding="utf-8")
        (m / "assets" / "pic.png").write_bytes(b"png")
        (self.root / "widgets" / "demo-widget.html").write_text(GOOD_WIDGET, encoding="utf-8")
        for rel, text in self.extra_files.items():
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        return self.root

    def run(self, *argv: str) -> dict:
        self.write()
        args = vc.parse_args([*(argv or [str(self.root)]), "--repo-root", str(self.root)])
        result, _ = vc.run(args)
        return result

    def close(self) -> None:
        self.tmp.cleanup()


def messages(result: dict, severity: str) -> list[str]:
    return [i["message"] for i in result["issues"] if i["severity"] == severity]


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Repo()

    def tearDown(self) -> None:
        self.repo.close()

    def assertError(self, result: dict, fragment: str) -> None:
        errs = messages(result, "error")
        self.assertTrue(any(fragment in e for e in errs), f"no error with {fragment!r} in {errs}")

    def assertWarning(self, result: dict, fragment: str) -> None:
        warns = messages(result, "warning")
        self.assertTrue(any(fragment in w for w in warns), f"no warning with {fragment!r} in {warns}")

    def assertClean(self, result: dict) -> None:
        self.assertEqual(messages(result, "error"), [])


class GoodPackage(Base):
    def test_valid_package_has_no_errors_or_warnings(self) -> None:
        result = self.repo.run()
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["warnings"], [])
        self.assertEqual(result["stats"]["courses"], 1)
        self.assertEqual(result["stats"]["modules"], 1)
        self.assertEqual(result["stats"]["questions"], 3)

    def test_course_module_and_file_targets(self) -> None:
        root = self.repo.write()
        for target in (root / "courses" / "demo-course", root / "courses" / "demo-course" / "course.json",
                       root / "modules" / "demo-module", root / "modules" / "demo-module" / "manifest.json"):
            result, status = vc.run(vc.parse_args([str(target)]))
            self.assertEqual(status, 0, (target, result["errors"]))


class QuizRules(Base):
    """The quiz rules where the two old validators disagreed."""

    def test_passing_score_is_a_warning_not_an_error(self) -> None:
        self.repo.quiz["passingScore"] = 70
        result = self.repo.run()
        self.assertClean(result)
        self.assertWarning(result, "passingScore is ignored")

    def test_passing_score_out_of_range_is_still_only_a_warning(self) -> None:
        self.repo.quiz["passingScore"] = 150
        self.assertClean(self.repo.run())

    def test_missing_passing_score_and_question_number_are_fine(self) -> None:
        result = self.repo.run()
        self.assertFalse([w for w in result["warnings"] if "questionNumber" in w or "passingScore" in w])

    def test_question_number_must_be_positive_integer_when_present(self) -> None:
        self.repo.quiz["questions"][0]["questionNumber"] = "1"
        self.assertError(self.repo.run(), "questionNumber")

    def test_quiz_type_is_a_warning(self) -> None:
        del self.repo.quiz["type"]
        result = self.repo.run()
        self.assertClean(result)
        self.assertWarning(result, 'top-level type should be "quiz"')
        self.repo.quiz["type"] = "lesson"
        self.assertWarning(self.repo.run(), 'top-level type should be "quiz"')

    def test_quiz_image_missing_is_a_warning(self) -> None:
        self.repo.quiz["questions"][0]["image"] = "diagram one.png"
        result = self.repo.run()
        self.assertClean(result)
        self.assertWarning(result, "image not found at courses/demo-course/assets/diagram one.png")
        self.repo.extra_files["courses/demo-course/assets/diagram one.png"] = "png"
        self.assertEqual(self.repo.run()["warnings"], [])

    def test_quiz_image_in_module_assets_is_not_enough(self) -> None:
        # QuizPlayer reads <course>/assets/<image>, never the module folder.
        self.repo.quiz["questions"][0]["image"] = "pic.png"
        self.assertWarning(self.repo.run(), "image not found at courses/demo-course/assets/pic.png")

    def test_is_correct_is_an_error(self) -> None:
        self.repo.quiz["questions"][0]["answers"][0]["isCorrect"] = True
        self.assertError(self.repo.run(), "isCorrect")

    def test_correct_must_be_boolean(self) -> None:
        self.repo.quiz["questions"][0]["answers"][0]["correct"] = "true"
        self.assertError(self.repo.run(), "correct must be true or false")

    def test_true_false_is_a_warning(self) -> None:
        self.repo.quiz["questions"][0]["type"] = "TRUE_FALSE"
        result = self.repo.run()
        self.assertClean(result)
        self.assertWarning(result, "TRUE_FALSE is not a platform type")

    def test_unknown_question_type(self) -> None:
        self.repo.quiz["questions"][0]["type"] = "ESSAY"
        self.assertError(self.repo.run(), "type must be one of")

    def test_multiple_choice_needs_exactly_one_correct(self) -> None:
        self.repo.quiz["questions"][0]["answers"][1]["correct"] = True
        self.assertError(self.repo.run(), "exactly one correct")

    def test_multiple_response_needs_a_correct_answer(self) -> None:
        for a in self.repo.quiz["questions"][1]["answers"]:
            a["correct"] = False
        self.assertError(self.repo.run(), "at least one correct")

    def test_matching_needs_match_text(self) -> None:
        del self.repo.quiz["questions"][2]["answers"][0]["matchText"]
        self.assertError(self.repo.run(), "matchText")

    def test_matching_does_not_need_correct(self) -> None:
        for a in self.repo.quiz["questions"][2]["answers"]:
            del a["correct"]
        result = self.repo.run()
        self.assertClean(result)
        self.assertEqual(result["warnings"], [])

    def test_duplicate_ids(self) -> None:
        self.repo.quiz["questions"][0]["answers"][1]["id"] = "q1_a"
        self.repo.quiz["questions"][1]["id"] = "q1"
        result = self.repo.run()
        self.assertError(result, "duplicate answer id")
        self.assertError(result, "duplicate question id")

    def test_answers_need_two(self) -> None:
        self.repo.quiz["questions"][0]["answers"] = self.repo.quiz["questions"][0]["answers"][:1]
        self.assertError(self.repo.run(), "at least 2")

    def test_feedback_is_a_warning_and_answer_feedback_is_flagged(self) -> None:
        q = self.repo.quiz["questions"][0]
        del q["feedback"]
        for a in q["answers"]:
            a["feedback"] = "Shown nowhere."
        del self.repo.quiz["questions"][1]["feedback"]
        result = self.repo.run()
        self.assertClean(result)
        self.assertWarning(result, "answer-level feedback is never shown")
        self.assertWarning(result, "no feedback; learners see no explanation")

    def test_feedback_html_alone_is_enough(self) -> None:
        q = self.repo.quiz["questions"][0]
        del q["feedback"]
        q["feedbackHtml"] = "<p>Because.</p>"
        self.assertEqual(self.repo.run()["warnings"], [])

    def test_empty_questions(self) -> None:
        self.repo.quiz["questions"] = []
        self.assertError(self.repo.run(), "questions must be a non-empty array")

    def test_bad_json(self) -> None:
        self.repo.write()
        (self.repo.root / "modules" / "demo-module" / "quiz.json").write_text("{nope", encoding="utf-8")
        result, status = vc.run(vc.parse_args([str(self.repo.root)]))
        self.assertEqual(status, 1)
        self.assertTrue(any("not valid JSON" in e for e in result["errors"]))


class StructureRules(Base):
    def test_ids_must_match_folders(self) -> None:
        self.repo.course["id"] = "other-course"
        self.repo.manifest["id"] = "other-module"
        result = self.repo.run()
        self.assertError(result, "id 'other-course' must match the folder name")
        self.assertError(result, "id 'other-module' must match the folder name")

    def test_missing_module(self) -> None:
        self.repo.course["modules"].append("ghost")
        self.assertError(self.repo.run(), "module 'ghost' not found")

    def test_duplicate_module_in_course(self) -> None:
        self.repo.course["modules"].append("demo-module")
        self.assertError(self.repo.run(), "listed twice")

    def test_course_optional_fields(self) -> None:
        for key in ("description", "estimatedDuration", "welcomePath"):
            del self.repo.course[key]
        result = self.repo.run()
        self.assertClean(result)
        self.assertWarning(result, "no description")

    def test_course_settings_ranges(self) -> None:
        self.repo.course.update(quizPassingThreshold=101, quizRevealMode="sometimes", quizMaxAttempts=0,
                                completionEvidence="maybe")
        result = self.repo.run()
        for fragment in ("quizPassingThreshold", "quizRevealMode", "quizMaxAttempts", "completionEvidence"):
            self.assertError(result, fragment)

    def test_welcome_path_must_exist(self) -> None:
        self.repo.course["welcomePath"] = "nope.md"
        self.assertError(self.repo.run(), "welcomePath does not exist")

    def test_module_description_is_a_warning(self) -> None:
        del self.repo.manifest["description"]
        result = self.repo.run()
        self.assertClean(result)
        self.assertWarning(result, "no description")

    def test_unknown_fields_warn(self) -> None:
        self.repo.course["quizPasingThreshold"] = 80
        self.assertWarning(self.repo.run(), "quizPasingThreshold")

    def test_section_lesson_is_a_warning(self) -> None:
        self.repo.manifest["lessons"].insert(1, {"id": "part-two", "title": "Part two", "type": "section"})
        result = self.repo.run()
        self.assertClean(result)
        self.assertWarning(result, "renders as an empty lesson in the learner player")

    def test_url_lesson_paths_are_errors(self) -> None:
        bad = ["https://example.com/01.md", "http://example.com/q.json", "//cdn.example.com/01.md",
               "mailto:a@b.c", "#intro", "javascript:alert(1)"]
        for value in bad:
            with self.subTest(value=value):
                self.repo.manifest["lessons"][0]["markdownPath"] = value
                self.repo.manifest["lessons"][1]["quizPath"] = value
                self.repo.course["welcomePath"] = value
                errs = messages(self.repo.run(), "error")
                for key in ("markdownPath", "quizPath", "welcomePath"):
                    self.assertTrue(any(key in e and "must be a relative file path" in e for e in errs),
                                    (key, errs))

    def test_lesson_rules(self) -> None:
        lessons = self.repo.manifest["lessons"]
        lessons.append({"id": "intro", "title": "Dup", "type": "content", "markdownPath": "01-intro.md"})
        lessons.append({"id": "m|||l", "title": "Legacy", "type": "section"})
        lessons.append({"id": "abs", "title": "Abs", "type": "content", "markdownPath": "/courses/x/01.md"})
        lessons.append({"id": "out", "title": "Out", "type": "content", "markdownPath": "../../courses/demo-course/welcome.md"})
        lessons.append({"id": "nofile", "title": "No file", "type": "quiz", "quizPath": "missing.json"})
        lessons.append({"id": "nopath", "title": "No path", "type": "content"})
        lessons.append({"id": "bad-type", "title": "Bad", "type": "video"})
        result = self.repo.run()
        for fragment in ("duplicate lesson id", "legacy '|||'", "must be a relative file path",
                         "inside the module folder", "quizPath does not exist",
                         "markdownPath must be a non-empty string", "type must be content or quiz"):
            self.assertError(result, fragment)


class MarkdownRules(Base):
    def test_front_matter_is_an_error(self) -> None:
        self.repo.lesson = "---\ntitle: Intro\n---\n# Intro\n"
        self.assertError(self.repo.run(), "front matter")

    def test_first_line_must_be_title(self) -> None:
        self.repo.lesson = "Intro text first.\n\n# Intro\n"
        result = self.repo.run()
        self.assertClean(result)
        self.assertWarning(result, "first line should be the lesson title")

    def test_leading_blank_lines_are_fine(self) -> None:
        self.repo.lesson = "\n\n" + LESSON
        self.assertEqual(self.repo.run()["warnings"], [])

    def test_empty_lesson(self) -> None:
        self.repo.lesson = "  \n"
        self.assertError(self.repo.run(), "lesson is empty")

    def test_missing_asset(self) -> None:
        self.repo.lesson = LESSON + '\n<video><source src="./assets/clip.mp4"></video>\n'
        self.assertError(self.repo.run(), "referenced file does not exist: ./assets/clip.mp4")

    def test_links_in_code_blocks_are_ignored(self) -> None:
        self.repo.lesson = LESSON + "\n```html\n<img src=\"./assets/example.png\">\n```\n"
        self.assertClean(self.repo.run())

    def test_external_and_anchor_links_ignored(self) -> None:
        self.repo.lesson = LESSON + "\n[x](https://example.com) [y](#top) [z](mailto:a@b.c)\n"
        self.assertEqual(self.repo.run()["warnings"], [])

    def test_widget_rules(self) -> None:
        self.repo.lesson = LESSON + "\n:::widget ghost-widget\ntitle: G\ndescription: G\n:::\n" \
                                    "\n:::widget demo-widget\nfullscreen: sometimes\n:::\n"
        result = self.repo.run()
        self.assertError(result, "not found at widgets/ghost-widget.html")
        self.assertError(result, "invalid fullscreen")
        self.assertWarning(result, "missing title: prop")

    def test_widget_html_warnings(self) -> None:
        self.repo.extra_files["widgets/demo-widget.html"] = "<div id='app'></div>"
        result = self.repo.run()
        self.assertClean(result)
        self.assertWarning(result, "no widget-ready")
        self.assertWarning(result, "no widget-mode")

    def test_reflection_ids_unique_across_course(self) -> None:
        self.repo.lesson = LESSON + '<div class="reflection" data-id="demo-reflection"></div>\n'
        self.assertError(self.repo.run(), "duplicate reflection data-id")


class AssetPaths(Base):
    """Image and link targets resolve the way LessonRenderer.vue resolveAssetPath does."""

    def lesson_with(self, *refs: str) -> None:
        self.repo.lesson = "# Intro\n\n" + "\n\n".join(refs) + "\n"

    def test_dot_slash_is_lesson_folder(self) -> None:
        self.lesson_with("![a](./assets/pic.png)", '<img src="./assets/pic.png">')
        self.assertEqual(self.repo.run()["warnings"], [])

    def test_dot_slash_in_a_lesson_subfolder(self) -> None:
        self.repo.manifest["lessons"][0]["markdownPath"] = "lessons/01-intro.md"
        self.repo.extra_files["modules/demo-module/lessons/01-intro.md"] = "# Intro\n\n![a](./assets/pic.png)\n"
        # ./ is the lesson file's folder (lessons/), which has no assets/.
        self.assertError(self.repo.run(), "referenced file does not exist: ./assets/pic.png")

    def test_bare_path_resolves_under_the_course_not_the_module(self) -> None:
        self.lesson_with("![a](assets/pic.png)")
        self.assertError(self.repo.run(), "the player resolves it to courses/demo-course/assets/pic.png")
        self.repo.extra_files["courses/demo-course/assets/pic.png"] = "png"
        self.assertClean(self.repo.run())

    def test_dot_dot_assets_resolves_under_the_course(self) -> None:
        self.lesson_with("![a](../assets/pic.png)")
        self.assertError(self.repo.run(), "courses/demo-course/assets/pic.png")
        self.repo.extra_files["courses/demo-course/assets/pic.png"] = "png"
        self.assertClean(self.repo.run())

    def test_leading_dot_dots_are_all_dropped(self) -> None:
        # ../../assets/x is NOT repo-root assets/: the player drops every leading ../ and reads courses/<c>/assets/x.
        self.repo.extra_files["assets/pic.png"] = "png"
        self.lesson_with("![a](../../assets/pic.png)")
        self.assertError(self.repo.run(), "courses/demo-course/assets/pic.png")

    def test_course_relative_path_is_checked_in_every_course(self) -> None:
        self.repo.extra_files["courses/other-course/course.json"] = json.dumps(
            {"id": "other-course", "title": "Other", "description": "d", "modules": ["demo-module"]})
        self.repo.extra_files["courses/demo-course/assets/pic.png"] = "png"
        self.lesson_with("![a](assets/pic.png)")
        errs = messages(self.repo.run(), "error")
        self.assertTrue(any("courses/other-course/assets/pic.png" in e for e in errs), errs)
        self.assertFalse(any("courses/demo-course/assets/pic.png" in e for e in errs), errs)

    def test_module_no_course_lists_is_a_warning(self) -> None:
        self.repo.course["modules"] = []  # course errors, but the module is validated alone
        self.lesson_with("![a](assets/pic.png)")
        self.assertWarning(self.repo.run(), "no course lists this module")

    def test_welcome_dot_slash_is_course_folder(self) -> None:
        self.repo.extra_files["courses/demo-course/welcome.md"] = "# Welcome\n\n![a](./assets/w.png)\n"
        self.assertError(self.repo.run(), "referenced file does not exist: ./assets/w.png")
        self.repo.extra_files["courses/demo-course/assets/w.png"] = "png"
        self.assertClean(self.repo.run())

    def test_image_with_spaces_like_fix_image_url_spaces(self) -> None:
        self.repo.extra_files["modules/demo-module/assets/my pic.png"] = "png"
        self.lesson_with("![a](./assets/my pic.png)", "![b](./assets/my%20pic.png)")
        result = self.repo.run()
        self.assertClean(result)
        self.assertEqual(result["warnings"], [])

    def test_image_with_spaces_and_a_title_breaks_in_the_player(self) -> None:
        # fixImageUrlSpaces turns every space into %20, so the title becomes part of the file name.
        self.lesson_with('![a](./assets/pic.png "A title")')
        self.assertError(self.repo.run(), "referenced file does not exist")

    def test_image_title_after_encoded_space_is_a_title(self) -> None:
        self.repo.extra_files["modules/demo-module/assets/my pic.png"] = "png"
        self.lesson_with('![a](./assets/my%20pic.png "A title")')
        self.assertClean(self.repo.run())

    def test_link_with_title_and_link_with_spaces(self) -> None:
        self.lesson_with('[a](./assets/pic.png "Title")')
        self.assertEqual(self.repo.run()["warnings"], [])
        self.lesson_with("[a](./assets/my pic.png)")
        result = self.repo.run()
        self.assertClean(result)
        self.assertWarning(result, "renders as plain text")

    def test_other_schemes_warn(self) -> None:
        self.lesson_with("[call](tel:+6491234567)", "[x](BLOB:abc) [y](Data:image/png;base64,AA) [z](//cdn.example.com/a.png)")
        result = self.repo.run()
        self.assertClean(result)
        warns = messages(result, "warning")
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("rewrites this one as a course file path", warns[0])

    def test_escape_outside_repo(self) -> None:
        self.lesson_with("![a](./../../../../etc/passwd)")
        self.assertError(self.repo.run(), "escapes the repository")

    def test_reflection_ids_unique_across_modules(self) -> None:
        self.repo.course["modules"].append("second-module")
        self.repo.extra_files["modules/second-module/manifest.json"] = json.dumps({
            "id": "second-module", "title": "Second", "description": "d",
            "lessons": [{"id": "one", "title": "One", "type": "content", "markdownPath": "one.md"}],
        })
        self.repo.extra_files["modules/second-module/one.md"] = \
            '# One\n<div class="reflection" data-id="demo-reflection"></div>\n'
        self.assertError(self.repo.run(), "in the same course")


class ChangedFiles(Base):
    def setUp(self) -> None:
        super().setUp()
        self.repo.extra_files["courses/other-course/course.json"] = json.dumps(
            {"id": "other-course", "title": "Other", "description": "d", "modules": ["lonely-module"]})
        self.repo.extra_files["modules/lonely-module/manifest.json"] = json.dumps(
            {"id": "lonely-module", "title": "Lonely", "description": "d",
             "lessons": [{"id": "x", "title": "X", "type": "section"}]})
        self.root = self.repo.write()

    def test_module_change_validates_courses_using_it(self) -> None:
        courses, modules = vc.resolve_changed(["modules/demo-module/01-intro.md"], self.root)
        self.assertEqual([c.name for c in courses], ["demo-course"])
        self.assertEqual([m.name for m in modules], ["demo-module"])

    def test_widget_change_validates_every_course(self) -> None:
        courses, _ = vc.resolve_changed(["widgets/demo-widget.html"], self.root)
        self.assertEqual([c.name for c in courses], ["demo-course", "other-course"])

    def test_unrelated_and_deleted_paths(self) -> None:
        courses, modules = vc.resolve_changed(["README.md", "modules/deleted-module/manifest.json"], self.root)
        self.assertEqual((courses, modules), ([], []))

    def test_deleted_module_still_listed_fails_its_course(self) -> None:
        import shutil
        shutil.rmtree(self.root / "modules" / "lonely-module")
        listing = self.root / "changed.txt"
        listing.write_text("modules/lonely-module/manifest.json\n", encoding="utf-8")
        result, status = vc.run(vc.parse_args(["--changed-from", str(listing), "--repo-root", str(self.root)]))
        self.assertEqual(status, 1)
        self.assertTrue(any("'lonely-module' not found" in e for e in result["errors"]), result["errors"])

    def test_changed_from_file(self) -> None:
        listing = self.root / "changed.txt"
        listing.write_text("courses/other-course/course.json\n\n", encoding="utf-8")
        result, status = vc.run(vc.parse_args(["--changed-from", str(listing), "--repo-root", str(self.root)]))
        self.assertEqual(status, 0, result["errors"])
        self.assertEqual(result["stats"]["courses"], 1)
        self.assertEqual(result["stats"]["modules"], 1)

    def test_nothing_changed_passes(self) -> None:
        result, status = vc.run(vc.parse_args(["--changed", "--repo-root", str(self.root)]))
        self.assertEqual((status, result["stats"]["courses"]), (0, 0))


class Cli(Base):
    def cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-I", str(SCRIPT), *args], capture_output=True, text=True)

    def test_exit_codes_and_outputs(self) -> None:
        root = self.repo.write()
        ok = self.cli(str(root))
        self.assertEqual(ok.returncode, 0, ok.stdout)
        self.assertTrue(ok.stdout.startswith("PASS: 1 courses"))

        self.repo.quiz["questions"][0]["answers"][0]["isCorrect"] = True
        self.repo.write()
        bad = self.cli(str(root), "--json", "--github")
        self.assertEqual(bad.returncode, 1)
        lines = bad.stdout.splitlines()
        self.assertTrue(lines[0].startswith("::error file=modules/demo-module/quiz.json::"), lines[0])
        payload = json.loads("\n".join(l for l in lines if not l.startswith("::")))
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["version"], vc.VERSION)

    def test_annotation_file_property_is_escaped(self) -> None:
        self.assertEqual(vc.escape_property("a:b,c%d\ne"), "a%3Ab%2Cc%25d%0Ae")
        self.assertEqual(vc.escape_data("50%: a,b\r\n"), "50%25: a,b%0D%0A")

    def test_usage_errors(self) -> None:
        self.assertEqual(self.cli().returncode, 2)
        with tempfile.TemporaryDirectory() as empty:
            self.assertEqual(self.cli(empty).returncode, 2)

    def test_version(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit):
            vc.parse_args(["--version"])
        self.assertIn(vc.VERSION, out.getvalue())


@unittest.skipIf(Draft202012Validator is None, "jsonschema not installed")
class SchemaAgreement(Base):
    """The JSON Schemas and the validator must agree on every structural rule a schema can express."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.schemas = {}
        for name in ("course", "module-manifest", "quiz"):
            schema = json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            cls.schemas[name] = Draft202012Validator(schema)

    def schema_ok(self) -> bool:
        return all(self.schemas[k].is_valid(v) for k, v in (
            ("course", self.repo.course), ("module-manifest", self.repo.manifest), ("quiz", self.repo.quiz)))

    def check(self, mutate, valid: bool) -> None:
        mutate(self.repo)
        result = self.repo.run()
        self.assertEqual(self.schema_ok(), valid, "schema")
        self.assertEqual(result["ok"], valid, result["errors"])

    def test_good(self) -> None:
        self.check(lambda r: None, True)

    def test_passing_score_allowed(self) -> None:
        self.check(lambda r: r.quiz.update(passingScore=80), True)

    def test_true_false_allowed(self) -> None:
        self.check(lambda r: r.quiz["questions"][0].update(type="TRUE_FALSE"), True)

    def test_feedback_optional(self) -> None:
        self.check(lambda r: r.quiz["questions"][0].pop("feedback"), True)

    def test_course_optional_fields(self) -> None:
        self.check(lambda r: [r.course.pop(k) for k in ("description", "estimatedDuration", "welcomePath")], True)

    def test_quiz_type_optional(self) -> None:
        self.check(lambda r: r.quiz.pop("type"), True)

    def test_quiz_type_other_value_allowed(self) -> None:
        self.check(lambda r: r.quiz.update(type="lesson"), True)

    def test_section_lesson_allowed(self) -> None:
        self.check(lambda r: r.manifest["lessons"].append({"id": "s", "title": "S", "type": "section"}), True)

    def test_url_lesson_paths(self) -> None:
        cases = [("lesson", "markdownPath"), ("quiz", "quizPath"), ("course", "welcomePath")]
        for value in ("https://example.com/x.md", "HTTP://example.com/x.md", "//cdn.example.com/x.md",
                      "mailto:a@b.c", "#intro", "tel:123"):
            for where, key in cases:
                with self.subTest(value=value, key=key):
                    self.tearDown()
                    self.setUp()

                    def mutate(r, where=where, key=key, value=value):
                        target = {"lesson": r.manifest["lessons"][0], "quiz": r.manifest["lessons"][1],
                                  "course": r.course}[where]
                        target[key] = value
                    self.check(mutate, False)

    def test_is_correct(self) -> None:
        self.check(lambda r: r.quiz["questions"][0]["answers"][0].update(isCorrect=True), False)

    def test_two_correct_multiple_choice(self) -> None:
        self.check(lambda r: r.quiz["questions"][0]["answers"][1].update(correct=True), False)

    def test_no_correct_multiple_response(self) -> None:
        self.check(lambda r: [a.update(correct=False) for a in r.quiz["questions"][1]["answers"]], False)

    def test_matching_without_match_text(self) -> None:
        self.check(lambda r: r.quiz["questions"][2]["answers"][0].pop("matchText"), False)

    def test_bad_question_type(self) -> None:
        self.check(lambda r: r.quiz["questions"][0].update(type="ESSAY"), False)

    def test_reveal_mode(self) -> None:
        self.check(lambda r: r.course.update(quizRevealMode="sometimes"), False)

    def test_threshold_range(self) -> None:
        self.check(lambda r: r.course.update(quizPassingThreshold=120), False)

    def test_content_lesson_needs_path(self) -> None:
        self.check(lambda r: r.manifest["lessons"][0].pop("markdownPath"), False)

    def test_legacy_lesson_id(self) -> None:
        self.check(lambda r: r.manifest["lessons"][1].update(id="m|||l"), False)

    def test_absolute_path(self) -> None:
        self.check(lambda r: r.manifest["lessons"][0].update(markdownPath="/courses/x/01-intro.md"), False)

    def test_bad_lesson_type(self) -> None:
        self.check(lambda r: r.manifest["lessons"][1].update(type="video"), False)

    def test_empty_modules(self) -> None:
        self.check(lambda r: r.course.update(modules=[]), False)


if __name__ == "__main__":
    unittest.main()
