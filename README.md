# mycourse.work Skills

[Claude Code](https://docs.anthropic.com/en/docs/claude-code) skills for the [mycourse.work](https://mycourse.work) course platform.

## Available Skills

### course-creator

Guides creation of complete training courses using the module-first architecture — standalone modules with manifests, course definitions referencing module IDs, lesson markdown with rich content features (callouts, inline HTML diagrams, math, code blocks, video embeds), quiz authoring (multiple choice, multiple response, matching), and deployment to R2/D1 via GitHub or upload scripts.

```json
{
  "skills": ["mycourse-work/skills/course-creator"]
}
```

### course-validator

Validates course content: module manifests, course definitions, markdown quality (heading hierarchy, image references), and quiz correctness.

```bash
pnpm validate-course content/{tenantId}
```

```json
{
  "skills": ["mycourse-work/skills/course-validator"]
}
```

### image-generator

Generates branded training images using the Gemini image generation API. Reads `brand.md` and `branding/logo.png` from a tenant's content repo, supports reference images, configurable style/size/aspect ratio.

```bash
npx tsx .claude/skills/image-generator/scripts/generate-image.ts \
  --repo /tmp/dt-repo \
  --prompt "Infographic showing the WALES mixing order" \
  --style infographic \
  --output assets/wales-mixing.png
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
- `jsdom` — Minimal DOM for validation
