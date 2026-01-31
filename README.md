# mycourse.work Skills

[Claude Code](https://docs.anthropic.com/en/docs/claude-code) skills for the [mycourse.work](https://mycourse.work) course platform.

## Available Skills

### course-creator

Guides creation of complete training courses — directory structure, manifest configuration, lesson markdown with rich content features (callouts, mermaid diagrams, math, code blocks, video embeds), and quiz authoring (multiple choice, multiple response, matching).

```json
{
  "skills": ["mycourse-work/skills/course-creator"]
}
```

### course-validator

Validates course content: manifest structure, markdown quality (heading hierarchy, image references), mermaid diagram syntax, and quiz correctness.

```bash
pnpm validate-course <path-to-course-folder>
```

```json
{
  "skills": ["mycourse-work/skills/course-validator"]
}
```

## Structure

```
course-creator/
├── SKILL.md
└── references/
    ├── manifest-schema.md
    └── quiz-schema.md

course-validator/
├── SKILL.md
├── scripts/
│   └── validate-course.ts
└── references/
    └── course-structure.md
```

## Dependencies

The validator script requires these packages (already installed in the mycourse.work platform):

- `marked` — Markdown lexer for content validation
- `mermaid` — Diagram syntax validation
- `jsdom` — Minimal DOM for mermaid's parser
