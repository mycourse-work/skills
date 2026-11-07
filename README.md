# mycourse.work Skills

[Claude Code](https://docs.anthropic.com/en/docs/claude-code) skills for the [mycourse.work](https://mycourse.work) course platform.

## Available Skills

### course-creator

Guides creation of complete training courses using the module-first architecture (format v1) — standalone modules with manifests, course definitions referencing module IDs, lesson markdown with rich content features (callouts, inline HTML diagrams, math, code blocks, video embeds), quiz authoring (multiple choice, multiple response, matching), and deployment to R2/D1 via GitHub or upload scripts.

```json
{
  "skills": ["mycourse-work/skills/course-creator"]
}
```

### course-validator

Validates module-first course content: `course.json`, module manifests, ids, file paths, lesson markdown and quizzes. One stdlib Python file (Python 3.9+, no packages), with the same rules as the platform.

```bash
python3 course-validator/scripts/validate_course.py path/to/tenant-repo
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

## Course format v1 (JSON Schemas)

The course format is defined in `schema/`:

| File | Describes |
|---|---|
| [`schema/course.schema.json`](schema/course.schema.json) | `courses/<id>/course.json` |
| [`schema/module-manifest.schema.json`](schema/module-manifest.schema.json) | `modules/<id>/manifest.json` |
| [`schema/quiz.schema.json`](schema/quiz.schema.json) | quiz JSON files |
| [`schema/RULES.md`](schema/RULES.md) | every rule, its severity (error or warning), and the platform code it comes from |

The schemas are JSON Schema draft 2020-12. Their `$id`s point at the `v1.0.0` tag, so an editor can use them, for example:

```json
{ "$schema": "https://raw.githubusercontent.com/mycourse-work/skills/v1.0.0/schema/course.schema.json", "id": "...", "title": "...", "modules": [] }
```

A schema cannot check everything (folder names, that files exist, unique ids across objects). `validate_course.py` checks all of it, so use the validator as the gate and the schemas for editors and tools.

## Pinning the validator

Content repos must run a **tagged** version, so a change here never breaks their pull requests without warning. Download the file at a tag:

```bash
VALIDATOR_REF=v1.0.0
curl -fsSL -o /tmp/validate_course.py \
  "https://raw.githubusercontent.com/mycourse-work/skills/${VALIDATOR_REF}/course-validator/scripts/validate_course.py"
python3 /tmp/validate_course.py --version     # validate_course.py 1.0.0
python3 /tmp/validate_course.py .
```

For a stronger pin, use the commit SHA of the tag instead of the tag name, or check the file's SHA-256 after the download:

```bash
echo "<sha256>  /tmp/validate_course.py" | sha256sum -c -
```

In GitHub Actions, the content repos use a `validate.yml` workflow that runs only on pull requests that change `courses/`, `modules/` or `widgets/`, and validates only what changed:

```yaml
- run: git diff --name-only "$BASE_SHA" HEAD > "$RUNNER_TEMP/changed.txt"   # include deleted files
- run: python3 -I "$RUNNER_TEMP/validate_course.py" --repo-root . --changed-from "$RUNNER_TEMP/changed.txt" --github
```

Keep deleted files in the list: a deleted module still makes the validator check every course that lists it.

**To upgrade**, change `VALIDATOR_REF` in the content repo's `validate.yml` in a pull request, and fix any new errors in the same pull request.

Versions follow `schema/RULES.md`: a patch fixes a check, a minor adds warnings or optional fields, a major adds or changes an error. `VERSION` in `validate_course.py` equals the tag.

## Development

```bash
python3 -m unittest discover -s course-validator/tests -v
pip install jsonschema   # optional: also runs the tests that check the schemas agree with the validator
```

CI (`.github/workflows/validator-tests.yml`) runs the tests on Python 3.9 and 3.12 and checks that each schema is valid draft 2020-12.

## Structure

```
schema/
├── RULES.md
├── course.schema.json
├── module-manifest.schema.json
└── quiz.schema.json

course-creator/
├── SKILL.md
└── references/
    ├── manifest-schema.md
    └── quiz-schema.md

course-validator/
├── SKILL.md
├── scripts/
│   └── validate_course.py
├── tests/
│   └── test_validate_course.py
└── references/
    └── course-structure.md

image-generator/
├── SKILL.md
└── scripts/
    └── generate-image.ts
```
