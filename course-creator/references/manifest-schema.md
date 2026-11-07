# Course and module manifests (format v1, module-first)

The machine-readable versions are `schema/course.schema.json` and `schema/module-manifest.schema.json` in this repo. `schema/RULES.md` lists every rule, its severity, and the platform code it comes from.

> The old layout (one `manifest.json` per course, `01_Module/` folders, `module|||lesson` ids, `/courses/...` absolute paths) is the **legacy** format. The admin zip import still reads it for old courses. Don't author new content in it.

## Repository layout

A tenant content repo (`mycourse-work/<tenant>`) has three top-level folders:

```text
repo/
├── courses/
│   └── <course-id>/
│       ├── course.json
│       ├── welcome.md              # optional, see welcomePath
│       └── assets/                 # course-level images, if needed
├── modules/
│   └── <module-id>/
│       ├── manifest.json
│       ├── 01-first-lesson.md
│       ├── quiz.json
│       ├── assets/                 # module images
│       └── downloads/              # optional job aids
└── widgets/
    └── <widget-name>.html          # shared, self-contained widgets
```

- A course lists module ids. A module can be in more than one course.
- **The folder name must equal the `id`.** The sync workflow copies files by folder name, but it registers the course or module by `id`. If they differ, the course points to files that are not there.
- Use kebab-case ids. Don't change an id after you publish it: learner progress is stored against it.

## course.json

```json
{
  "id": "drone-basics-nz",
  "title": "Drone Basics (NZ)",
  "description": "What you need to know before your first flight in New Zealand.",
  "estimatedDuration": "2-3 hours",
  "welcomePath": "welcome.md",
  "coverImage": "assets/cover.webp",
  "quizPassingThreshold": 80,
  "quizRevealMode": "end-of-quiz",
  "modules": ["drone-basics-rules", "drone-basics-airspace"]
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Equals the folder name. |
| `title` | string | yes | Learner-facing. |
| `description` | string | recommended | Shown on the course card. Missing → warning. |
| `modules` | string[] | yes | Module ids in learner order. Each one must exist. No duplicates. |
| `estimatedDuration` | string | no | Human-readable, e.g. `"2-3 hours"`. |
| `welcomePath` | string | no | Markdown file, relative to the course folder. Shown before module 1. |
| `coverImage` | string | no | Image path or URL for the course card. |
| `quizPassingThreshold` | number 0-100 | no | **The pass mark for every quiz in the course.** Default 80. |
| `quizMaxAttempts` | integer ≥ 1 | no | Limit on quiz attempts. Default: no limit. |
| `quizRevealMode` | `immediate` \| `end-of-quiz` \| `never` | no | When learners see the correct answers. Default `end-of-quiz`. |
| `sequentialProgression` | boolean | no | Learners must finish lessons in order. |
| `contentUnitLabel`, `contentUnitLabelPlural` | string | no | Rename "Module" / "Modules" in the UI. |
| `completionRecord` | object | no | Completion record page: `enabled` (boolean), `title`, `heading`, `nameLabel`, `referenceLabel`, `requireName`, `requireCaaId`. |
| `completionEvidence` | `off` \| `warn` \| `enforce` | no | Reading-time evidence for completion. |
| `evidenceWordsPerMinute` | number > 0 | no | Reading speed for `completionEvidence`. |

Unknown fields are ignored by the platform. The validator warns about them, because they are usually typos.

## modules/&lt;id&gt;/manifest.json

```json
{
  "id": "drone-basics-rules",
  "title": "The Rules",
  "description": "The Part 101 rules every pilot must follow.",
  "estimatedDuration": "45 minutes",
  "tags": ["part101", "rules"],
  "lessons": [
    { "id": "why-rules", "title": "Why the Rules Exist", "type": "content", "markdownPath": "01-why-rules.md" },
    { "id": "in-the-field", "title": "In the Field", "type": "section" },
    { "id": "pre-flight", "title": "Pre-flight Checks", "type": "content", "markdownPath": "02-pre-flight.md" },
    { "id": "quiz", "title": "Rules Quiz", "type": "quiz", "quizPath": "quiz.json" }
  ]
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Equals the folder name. |
| `title` | string | yes | |
| `description` | string | recommended | Missing → warning. |
| `estimatedDuration` | string | no | |
| `tags` | string[] | no | |
| `lessons` | array | yes | In learner order. Not empty. |

Lesson fields:

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Unique in the module. No `\|\|\|`: the platform adds `<module>\|\|\|` itself. |
| `title` | yes | |
| `type` | yes | `content`, `quiz` or `section`. |
| `markdownPath` | for `content` | Relative to the module folder, e.g. `01-why-rules.md`. Never `/courses/...`. |
| `quizPath` | for `quiz` | Relative to the module folder, e.g. `quiz.json`. |

A `section` lesson is a heading in the lesson list. It has no file.

## Lesson Markdown

- The first line is `# Lesson title`.
- **No front matter.** The player renders the whole file, so a `---` block shows up as text. This is an error.
- Reference images relatively: `![Alt text](./assets/diagram.webp)`.
- Every local file you link or embed must exist.
- Widgets: `:::widget <name>` needs `widgets/<name>.html`, plus `title:` and `description:` props (the phone activity card).
- Reflection `data-id`s must be unique across the whole course.

See the course-creator `SKILL.md` for content features (callouts, code, Mermaid, maths, video, widgets, reflections).
