---
name: course-validator
description: Validate course content for the mycourse.work platform. Checks manifest structure, markdown content quality (heading hierarchy, image references), mermaid diagram syntax, and quiz file correctness. Use when validating courses, checking course quality, debugging broken courses, or before uploading course content to R2.
---

# Course Validator

Validate course content structure, markdown quality, and mermaid diagrams for the mycourse.work course platform.

## Usage

Run from the platform repo root:

```bash
pnpm validate-course <path-to-course-folder>
```

Example:

```bash
pnpm validate-course content/tenants/openclaw/courses/openclaw-security-hardening
```

The script is at `scripts/validate-course.ts` and runs via `npx tsx`. It requires `marked`, `mermaid`, and `jsdom` (all already installed in the platform).

## What It Validates

### Manifest (`manifest.json`)
- Valid JSON with required fields (`id`, `title`, `description`, `modules`)
- `id` matches the course folder name
- Valid hex color
- Sequential module/lesson indices
- No duplicate module or lesson IDs
- Lesson ID format: `{moduleId}|||{lessonFileName}`
- `markdownPath`/`quizPath` files exist on disk

### Markdown Content (`.md` files)
- Parses with `marked.lexer()`
- First heading is H1
- No empty headings
- No skipped heading levels (e.g. H2 directly to H4)
- Image references resolve to files on disk (for `/courses/{id}/...` paths)
- Warns on external image URLs
- Detects orphaned files not referenced in manifest

### Mermaid Diagrams
- Extracts fenced code blocks with `lang: mermaid`
- Validates each with `mermaid.parse()`
- Reports diagram type on success (flowchart, sequence, mindmap, etc.)
- Reports parse errors with location info on failure

### Quiz Files (`.json`)
- Valid JSON with required fields (`title`, `type: "quiz"`, `passingScore`, `questions`)
- Question types: `MULTIPLE_CHOICE`, `MULTIPLE_RESPONSE`, `MATCHING`
- Uses `correct` field (not `isCorrect`)
- `MULTIPLE_CHOICE` has exactly 1 correct answer
- `MATCHING` questions have `matchText` on all answers
- No duplicate question IDs, all answers have IDs and text

### Directory Structure
- `assets/` directory exists
- Module directories follow `##_Name` pattern
- No unexpected file types in module directories

## Output

Results are printed with icons:
- `pass` — pass
- `error` — error (causes non-zero exit)
- `warning` — warning (advisory)

Exit code is `1` if any errors found, `0` otherwise.

## Fixing Common Errors

| Error | Fix |
|-------|-----|
| `uses "isCorrect" instead of "correct"` | Rename `isCorrect` to `correct` in quiz JSON |
| `markdownPath file not found` | Check path in manifest matches actual file location |
| `mermaid diagram has syntax error` | Fix the mermaid syntax in the markdown file |
| `skips heading level` | Add intermediate heading (e.g. add H3 between H2 and H4) |
| `references missing image` | Add the image file or fix the path |

## scripts/

Contains the full validator source at [scripts/validate-course.ts](scripts/validate-course.ts). Copy to `scripts/validate-course.ts` in the platform repo if not already present.

## references/

See [references/course-structure.md](references/course-structure.md) for the expected course directory layout, manifest schema, lesson markdown format, and quiz JSON schema.
