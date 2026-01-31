# mycourse.work Skills

[Claude Code](https://docs.anthropic.com/en/docs/claude-code) skills for the [mycourse.work](https://mycourse.work) course platform.

## Available Skills

### course-validator

Validates course content for the mycourse.work platform. Checks:

- **Manifest structure** — required fields, sequential indices, matching IDs, valid paths
- **Markdown quality** — heading hierarchy, empty headings, image references
- **Mermaid diagrams** — syntax validation via `mermaid.parse()`
- **Quiz correctness** — question types, answer fields, `correct` vs `isCorrect`
- **Directory structure** — naming patterns, orphaned files

#### Usage

Copy `scripts/validate-course.ts` into your platform repo, then:

```bash
pnpm validate-course <path-to-course-folder>
```

#### As a Claude Code Skill

Add this repo as a skill in your Claude Code config:

```json
{
  "skills": ["mycourse-work/skills/course-validator"]
}
```

## Structure

```
course-validator/
├── SKILL.md                          # Skill metadata and instructions
├── scripts/
│   └── validate-course.ts            # Validator script (tsx)
└── references/
    └── course-structure.md           # Course format reference
```

## Dependencies

The validator requires these packages (already installed in the mycourse.work platform):

- `marked` — Markdown lexer for content validation
- `mermaid` — Diagram syntax validation
- `jsdom` — Minimal DOM for mermaid's parser
