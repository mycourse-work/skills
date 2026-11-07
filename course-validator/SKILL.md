---
name: course-validator
description: Validate module-first course content for the mycourse.work platform with a single stdlib Python script. Checks course.json and module manifests, ids, file paths, lesson markdown (title line, no front matter, links, widgets, reflections) and quiz correctness, using the same rules as the platform. Use when validating courses, checking course quality, debugging a broken course, or before opening a pull request on a tenant content repo.
---

# Course Validator

`scripts/validate_course.py` validates module-first course content (format v1). It needs only Python 3.9+, with no packages. Its rules are in `schema/RULES.md` and match `scripts/validate-course.ts` in the platform repo.

## Usage

Run it from a tenant content repo (the folder with `courses/`, `modules/` and `widgets/`):

```bash
python3 validate_course.py .                              # every course and module
python3 validate_course.py courses/ai-for-business        # one course and its modules
python3 validate_course.py modules/ai-basics              # one module
python3 validate_course.py --changed modules/ai-basics/quiz.json widgets/prompt-builder.html
python3 validate_course.py --changed-from changed.txt --github   # what CI runs
```

| Option | What it does |
|---|---|
| `targets` | Repo root, course folder or `course.json`, module folder or `manifest.json`. |
| `--repo-root DIR` | The repo root, if the script cannot find it from the targets. |
| `--changed FILE...` | Validate what these files affect: a changed module also validates every course that lists it; a changed widget validates every course. Pass deleted files too: a deleted module makes it check every course that still lists it. Unrelated paths are skipped. |
| `--changed-from LIST` | The same, reading the file list (one per line) from a file. |
| `--json` | Print `{ok, version, errors, warnings, issues, stats}`. |
| `--github` | Also print `::error` / `::warning` annotations for GitHub Actions. |
| `--version` | Print the version. |

Exit status: `0` no errors (warnings are allowed), `1` errors, `2` usage problem (for example, no course or module found).

## Errors and warnings

**Errors** break the course or change what the learner gets. Fix every one before you open the pull request. The most common:

- A course or module `id` is not the same as its folder name
- A module listed in `course.json` does not exist
- A lesson path is absolute (`/courses/...`) or points to a missing file
- A lesson starts with front matter (`---`)
- A quiz has no `"type": "quiz"`, an answer uses `isCorrect`, or a `MULTIPLE_CHOICE` question does not have exactly one correct answer
- A `:::widget` names a widget that is not in `widgets/`
- A reflection `data-id` is used twice in one course

**Warnings** are allowed, but have a look. The most common:

- `passingScore` in a quiz: it is ignored. The pass mark is `quizPassingThreshold` in `course.json`
- A question has no question-level `feedback` (answer-level feedback is never shown)
- `TRUE_FALSE` question type: it plays as `MULTIPLE_CHOICE`
- The first line of a lesson is not `# Title`
- A missing course or module `description`, or an unknown field (often a typo)
- A widget with no `title:` / `description:`, or a widget that does not handle the full-screen protocol

The full list, with the platform code each rule comes from, is in [schema/RULES.md](../schema/RULES.md). The folder structure is in [references/course-structure.md](references/course-structure.md).

## In CI

Content repos pin a tagged version. See "Pinning the validator" in the repo README.
