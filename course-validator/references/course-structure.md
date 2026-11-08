# Course structure the validator expects (format v1)

```text
<tenant repo>/
├── courses/<course-id>/course.json        # id == folder name
├── courses/<course-id>/welcome.md         # optional (welcomePath)
├── modules/<module-id>/manifest.json      # id == folder name
├── modules/<module-id>/*.md               # lessons (markdownPath, relative)
├── modules/<module-id>/quiz.json          # quizzes (quizPath, relative)
├── modules/<module-id>/assets/            # images and files linked as ./assets/...
└── widgets/<name>.html                    # used by :::widget <name>
```

What the validator does for each target:

1. **Course** (`courses/<id>/course.json`): checks the fields, the optional settings (`quizPassingThreshold`, `quizRevealMode`, ...), the welcome page, and that each listed module exists. Then it validates each module, and checks that reflection ids are unique across the course.
2. **Module** (`modules/<id>/manifest.json`): checks the fields and each lesson. A `content` lesson's markdown and a `quiz` lesson's JSON are validated. A `section` lesson is a warning: the learner player shows it as an empty lesson. Image and link targets are resolved like the player's `resolveAssetPath`: only `./` is lesson-relative; other relative paths resolve under `courses/<course>/` for every course using the module.
3. **Lesson markdown**: the first line is `# Title`, no front matter, local links and images exist, widgets exist and have their props, reflection ids are unique.
4. **Quiz**: `"type": "quiz"`, unique ids, valid question types, correct-answer counts, `matchText` for matching, no `isCorrect`, and question-level feedback.

A module that no course lists is still validated when you validate the repo root.

The field-by-field format is in `course-creator/references/manifest-schema.md` and `course-creator/references/quiz-schema.md`. The JSON Schemas are in `schema/`.
