# Course Structure Reference

## Directory Layout

```
{course-id}/
├── manifest.json
├── assets/
│   ├── cover.png
│   └── ...
├── 01_Module_Name/
│   ├── 01_Lesson.md
│   ├── 02_Another_Lesson.md
│   └── 03_Quiz.json
└── 02_Module_Name/
    └── ...
```

- Course ID: lowercase, hyphenated slug (e.g. `ai-for-business`)
- Module folders: `{##}_{Module_Name}` with underscores, zero-padded
- Lesson files: `{##}_{Lesson_Title}.md`
- Quiz files: `{##}_Quiz.json` or `{##}_{Quiz_Name}.json`

## manifest.json Schema

```json
{
  "id": "course-id",
  "title": "Course Title",
  "description": "<p>HTML description</p>",
  "color": "#3b82f6",
  "coverImage": "cover.png",
  "modules": [
    {
      "id": "01_Module_Name",
      "title": "Module 1: Title",
      "index": 1,
      "description": "Optional module description",
      "lessons": [
        {
          "id": "01_Module_Name|||01_Lesson",
          "moduleId": "01_Module_Name",
          "title": "Lesson Title",
          "type": "content",
          "index": 1,
          "markdownPath": "/courses/course-id/01_Module_Name/01_Lesson.md"
        },
        {
          "id": "01_Module_Name|||02_Quiz",
          "moduleId": "01_Module_Name",
          "title": "Module Quiz",
          "type": "quiz",
          "index": 2,
          "quizPath": "/courses/course-id/01_Module_Name/02_Quiz.json"
        }
      ]
    }
  ]
}
```

Key rules:
- `id` must match folder name
- Lesson IDs: `{moduleId}|||{lessonFileName}` (no extension)
- Paths are absolute from `/courses/`
- Indices are 1-based and sequential
- `type`: `"content"`, `"quiz"`, or `"section"`

## Lesson Markdown Format

```markdown
# Lesson Title

Introduction paragraph.

## Learning Objectives
- Objective 1
- Objective 2

## Main Content

> **Tip:** Tips use blockquotes with bold keyword.

> **Warning:** Warnings for important info.

## Key Takeaways
- Takeaway 1
```

Requirements:
- Must start with H1
- No skipped heading levels (H2 to H4 without H3)
- Image paths: `![alt](/courses/{course-id}/assets/image.png)`
- Mermaid diagrams use fenced code blocks with `mermaid` language

## Quiz JSON Schema

```json
{
  "title": "Quiz Title",
  "type": "quiz",
  "passingScore": 80,
  "questions": [
    {
      "id": "q1",
      "type": "MULTIPLE_CHOICE",
      "question": "Question text?",
      "answers": [
        { "id": "q1_a", "text": "Answer", "correct": true },
        { "id": "q1_b", "text": "Wrong", "correct": false }
      ],
      "feedback": "Explanation"
    }
  ]
}
```

Question types:
- `MULTIPLE_CHOICE` — exactly 1 correct answer
- `MULTIPLE_RESPONSE` — 1+ correct answers
- `MATCHING` — all answers need `matchText` field

Use `correct` (not `isCorrect`) for answer correctness.
