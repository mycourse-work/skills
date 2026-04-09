---
name: image-generator
description: Generate branded training images using Gemini image generation. Reads brand.md and logo from a tenant's content repo, supports reference images, configurable style/size/aspect ratio. Use when creating infographics, diagrams, illustrations, or any visual asset for course content.
---

# Image Generator

Generate branded training images for mycourse.work courses using the Gemini image generation API.

## Prerequisites

- `GEMINI_API_KEY` or `GOOGLE_API_KEY` environment variable set
- A cloned tenant content repo (e.g. `/tmp/dt-repo` for dronetrust) containing:
  - `brand.md` — brand guidelines (colors, style, logo placement rules)
  - `branding/logo.png` — tenant logo file

## Usage

```bash
npx tsx .claude/skills/image-generator/scripts/generate-image.ts \
  --repo /tmp/dt-repo \
  --prompt "Infographic showing the 4 exposure pathways for chemical operators" \
  --output /tmp/dt-repo/modules/chem-human-safety/assets/exposure-pathways.png \
  --style infographic
```

### Required Arguments

| Arg | Description |
|-----|-------------|
| `--repo` | Path to the tenant content repo (must contain `brand.md` and `branding/logo.png`) |
| `--prompt` | What to generate — be specific about content, layout, and purpose |

### Optional Arguments

| Arg | Default | Description |
|-----|---------|-------------|
| `--output` | `./generated-{timestamp}.png` | Output file path |
| `--style` | (auto from brand.md) | Image classification: `infographic`, `process`, `comparison`, `safety`, `technical`, `illustration`, `photo` |
| `--aspect-ratio` | `16:9` | Aspect ratio: `1:1`, `4:3`, `16:9`, `21:9` |
| `--size` | `1K` | Image size: `512`, `1K`, `2K`, `4K` |
| `--model` | `gemini-3.1-flash-image-preview` | Gemini model to use |
| `--ref` | (none) | Reference image path(s) — can be specified multiple times (max 14) |
| `--ref-label` | (none) | Label for the corresponding `--ref` image (same order) |
| `--no-logo` | false | Skip adding the logo as a reference image |
| `--no-brand` | false | Skip reading brand.md guidelines |
| `--thinking` | `minimal` | Thinking level: `minimal`, `High` |
| `--dry-run` | false | Print the prompt without calling the API |

### Examples

```bash
# Simple infographic
npx tsx .claude/skills/image-generator/scripts/generate-image.ts \
  --repo /tmp/dt-repo \
  --prompt "Infographic showing the WALES chemical mixing order: Wetter, Agitator, Liquid, Emulsion, Suspension" \
  --style infographic \
  --output /tmp/dt-repo/modules/chem-agricultural-chemicals/assets/wales-mixing-order.png

# Recreate an existing image with improvements
npx tsx .claude/skills/image-generator/scripts/generate-image.ts \
  --repo /tmp/dt-repo \
  --prompt "Improve this safety graphic — cleaner layout, better hierarchy" \
  --ref /tmp/dt-repo/modules/chem-human-safety/assets/ppe-requirements.png \
  --ref-label "Source image to recreate with improved branding" \
  --style safety \
  --output /tmp/dt-repo/modules/chem-human-safety/assets/ppe-requirements-v2.png

# Technical diagram with multiple references
npx tsx .claude/skills/image-generator/scripts/generate-image.ts \
  --repo /tmp/dt-repo \
  --prompt "Labeled diagram of DJI Agras T40 spray system components" \
  --ref photo1.jpg --ref-label "Component photo for reference" \
  --ref photo2.jpg --ref-label "Nozzle detail" \
  --style technical \
  --size 2K \
  --output assets/spray-system-diagram.png

# Dry run to preview prompt
npx tsx .claude/skills/image-generator/scripts/generate-image.ts \
  --repo /tmp/dt-repo \
  --prompt "Fire triangle infographic relating ignition sources to chemical operations" \
  --style safety \
  --dry-run
```

## How It Works

1. Reads `brand.md` from the tenant repo for color palette, style rules, and tone
2. Reads `branding/logo.png` and includes it as a reference image with placement instructions
3. Builds a structured prompt combining: user prompt + brand guidelines + style-specific instructions + reference images
4. Calls the Gemini image generation API (`generateContent` with `responseModalities: ["IMAGE"]`)
5. Saves the output image to the specified path

## Style-Specific Behavior

Each `--style` adds targeted instructions to the prompt:

- **infographic**: Educational layout, strong hierarchy, readable labels, flat design
- **process**: Numbered steps, directional arrows, clear flow
- **comparison**: Side-by-side grid, clear headers, balanced visual weight
- **safety**: High contrast, hazard symbols, warning emphasis with salmon red
- **technical**: Line drawings, labeled parts, leader lines, accurate proportions
- **illustration**: Clean, modern, educational — no text unless needed
- **photo**: Realistic, professional — drone operators in field gear

## Batch Usage

For generating multiple images, call the script in a loop or use Claude Code agents in parallel:

```bash
# Generate multiple images from a list
while IFS=$'\t' read -r prompt style output; do
  npx tsx .claude/skills/image-generator/scripts/generate-image.ts \
    --repo /tmp/dt-repo \
    --prompt "$prompt" \
    --style "$style" \
    --output "$output"
done < image-list.tsv
```

## Notes

- All generated images include a SynthID watermark (Gemini requirement)
- The logo is always sent as the last reference image unless `--no-logo` is set
- brand.md is read fresh each invocation — edit it to adjust branding without changing the script
- Output directories are created automatically if they don't exist
