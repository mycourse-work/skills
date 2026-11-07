# mycourse course format v1: the rules

This is the one rulebook for module-first course content. The JSON Schemas in this folder, `course-validator/scripts/validate_course.py`, and `scripts/validate-course.ts` in `mycourse-work/course.platform` all follow it.

**How the severity is chosen**
- **Error**: the platform breaks, silently drops content, or gives the learner something different from what the author wrote.
- **Warning**: the platform tolerates it, but it is probably a mistake, or the platform ignores it.

The platform code is the source of truth. If this file and the platform disagree, the platform wins and this file has a bug.

## Where the rules come from

| Platform code (course.platform) | What it reads |
|---|---|
| `workers/edge-router/src/index.ts`: `normalizeCourseJsonToBlueprint`, `resolveBlueprint` | `course.json` and `modules/<id>/manifest.json`. It prefixes lesson paths with `/courses/<course>/@modules/<module>/`, so the paths must be relative. Lesson ids become `<module>\|\|\|<lesson>`. |
| `mycourse-work/.github` → `sync-to-r2.yml` | It copies files by **folder name**, but it registers the course and module by their **`id`**. So the `id` must equal the folder name. It stores `title`, `description` and `coverImage`. |
| `packages/core/components/course/LessonRenderer.vue` (`marked.parse` on the raw file, ~l.917) | The whole lesson file is rendered as-is. Front matter shows up as text. |
| `packages/core/components/course/QuizPlayer.vue` | The player handles `MULTIPLE_RESPONSE` and `MATCHING` specially. Every other type is played as single choice. It shows only question-level `feedback` / `feedbackHtml`. |
| `packages/core/utils/quiz.ts` | The grader counts `correct === true` and uses `matchText` for `MATCHING`. The pass mark comes from course `quizPassingThreshold` (clamped 0-100, default 80). |
| `packages/core/types/course.ts` | Question types are `MULTIPLE_CHOICE`, `MULTIPLE_RESPONSE` and `MATCHING`. |

## course.json (`courses/<id>/course.json`)

| Rule | Severity | Schema |
|---|---|---|
| Valid JSON object | error | yes |
| `id` is present and equals the folder name | error | presence only |
| `id` is kebab-case | warning | no |
| `title` is a non-empty string | error | yes |
| `description` is missing | warning | no (optional) |
| `modules` is a non-empty array of strings, with no duplicates | error | yes |
| Every listed module exists at `modules/<id>/manifest.json` | error | no |
| `welcomePath` (optional) is relative and the file exists | error | relative only |
| `quizPassingThreshold` is a number from 0 to 100 | error | yes |
| `quizMaxAttempts` is an integer ≥ 1 | error | yes |
| `quizRevealMode` is `immediate`, `end-of-quiz` or `never` | error | yes |
| `completionEvidence` is `off`, `warn` or `enforce` | error | yes |
| `evidenceWordsPerMinute` > 0, `sequentialProgression` is a boolean, `completionRecord.enabled` is a boolean | error | yes |
| A reflection `data-id` is used twice in one course (across all of its modules) | error | no |
| Unknown key (often a typo, such as `quizPasingThreshold`) | warning | no (extra keys are allowed) |

## manifest.json (`modules/<id>/manifest.json`)

| Rule | Severity | Schema |
|---|---|---|
| `id` is present and equals the folder name | error | presence only |
| `title` is a non-empty string | error | yes |
| `description` is missing | warning | no (optional) |
| `lessons` is a non-empty array | error | yes |
| Lesson `id` is unique in the module | error | no |
| Lesson `id` contains `\|\|\|` (the old format) | error | yes |
| Lesson `type` is `content`, `quiz` or `section` | error | yes |
| A `content` lesson has `markdownPath`; a `quiz` lesson has `quizPath` | error | yes |
| A `section` lesson needs no path (it is a heading in the lesson list) | ok | yes |
| The path is relative, stays inside the module folder, and the file exists | error | relative only |

## Lesson Markdown

| Rule | Severity |
|---|---|
| The file is empty | error |
| The file starts with front matter (`---`); the player would show it as text | error |
| The first line is not `# Title` | warning |
| A local image, link or `src=` points to a file that does not exist | error |
| A link starts with `/` (root-relative; it does not resolve on the CDN) | warning |
| `:::widget <name>` has a bad name, or there is no `widgets/<name>.html` | error |
| `fullscreen:` is not `phone`, `always` or `off` | error |
| `:::widget` has no `title:` or no `description:` prop | warning |
| The widget HTML has no `widget-ready`, `widget-mode` or `widget-focus-exit` (unless it posts `widget-focus-optout`) | warning |

Links inside fenced code blocks are not checked.

## quiz.json

| Rule | Severity | Schema |
|---|---|---|
| `title` is a non-empty string | error | yes |
| Top-level `type` is `"quiz"` | error | yes |
| `passingScore` is present; it is **ignored**, and the pass mark is course `quizPassingThreshold` | warning | allowed, marked deprecated |
| `questions` is a non-empty array, and question ids are unique | error | non-empty only |
| `question` text is a non-empty string | error | yes |
| `questionNumber` (optional) is an integer ≥ 1 | error | yes |
| Question `type` is `MULTIPLE_CHOICE`, `MULTIPLE_RESPONSE` or `MATCHING` | error | yes |
| Question `type` is `TRUE_FALSE`; it is not a platform type, and it plays as `MULTIPLE_CHOICE` | warning | allowed, marked deprecated |
| The question has no `feedback` / `feedbackHtml` (learners see no explanation) | warning | no (optional) |
| Only answer-level `feedback` is set (the player never shows it) | warning | no |
| At least 2 answers; answer ids are unique within the question | error | count only |
| An answer has `isCorrect` (the grader reads only `correct`) | error | yes |
| `correct` is not a boolean | error | yes |
| `MULTIPLE_CHOICE` / `TRUE_FALSE`: exactly one answer has `correct: true` | error | yes |
| `MULTIPLE_RESPONSE`: at least one answer has `correct: true` | error | yes |
| `MATCHING`: every answer has `matchText` | error | yes |
| An answer has no `correct` (not `MATCHING`) | warning | no |

"Schema: no" means a JSON Schema cannot express the rule (file existence, folder names, uniqueness of a field across objects). Only the validators check those rules.

## Versioning

- Patch (1.0.x): bug fixes that make a check match these rules.
- Minor (1.x.0): new warnings, or new optional fields.
- Major: a new error, or a changed error, that may fail content which passed before.

Content repos pin a tag (see the README), so a new error never breaks them without a PR.
