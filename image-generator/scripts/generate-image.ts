#!/usr/bin/env npx tsx
/**
 * Generate branded training images using Gemini image generation API.
 *
 * Reads brand.md + logo from a tenant content repo and produces
 * on-brand images with configurable style, size, and reference images.
 *
 * Usage:
 *   npx tsx .claude/skills/image-generator/scripts/generate-image.ts \
 *     --repo /tmp/dt-repo \
 *     --prompt "Infographic showing the 4 exposure pathways" \
 *     --style infographic \
 *     --output /tmp/dt-repo/modules/chem-human-safety/assets/exposure-pathways.png
 */

import 'dotenv/config'
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { basename, dirname, extname, join } from 'node:path'
import { parseArgs } from 'node:util'

// ── Args ──

const { values } = parseArgs({
  options: {
    repo: { type: 'string' },
    prompt: { type: 'string', short: 'p' },
    output: { type: 'string', short: 'o' },
    style: { type: 'string', short: 's' },
    'aspect-ratio': { type: 'string', default: '16:9' },
    size: { type: 'string', default: '1K' },
    model: { type: 'string', default: 'gemini-3.1-flash-image-preview' },
    ref: { type: 'string', multiple: true },
    'ref-label': { type: 'string', multiple: true },
    'no-logo': { type: 'boolean', default: false },
    'no-brand': { type: 'boolean', default: false },
    thinking: { type: 'string', default: 'minimal' },
    'dry-run': { type: 'boolean', default: false }
  },
  strict: false
})

const GEMINI_API_KEY = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY
if (!GEMINI_API_KEY && !values['dry-run']) {
  console.error('Error: GEMINI_API_KEY or GOOGLE_API_KEY environment variable required')
  process.exit(1)
}

if (!values.repo || !values.prompt) {
  console.error('Usage: generate-image.ts --repo <path> --prompt "..." [--output <path>] [--style <type>]')
  console.error('')
  console.error('Required:')
  console.error('  --repo      Path to tenant content repo (must contain brand.md + branding/logo.png)')
  console.error('  --prompt    What to generate')
  console.error('')
  console.error('Optional:')
  console.error('  --output         Output file path (default: ./generated-{timestamp}.png)')
  console.error('  --style          infographic|process|comparison|safety|technical|illustration|photo')
  console.error('  --aspect-ratio   1:1|4:3|16:9|21:9 (default: 16:9)')
  console.error('  --size           512|1K|2K|4K (default: 1K)')
  console.error('  --model          Gemini model (default: gemini-3.1-flash-image-preview)')
  console.error('  --ref            Reference image path (repeatable, max 14)')
  console.error('  --ref-label      Label for corresponding --ref (same order)')
  console.error('  --no-logo        Skip logo reference image')
  console.error('  --no-brand       Skip brand.md guidelines')
  console.error('  --thinking       minimal|High (default: minimal)')
  console.error('  --dry-run        Print prompt without calling API')
  process.exit(1)
}

// ── Style instructions ──

const STYLE_INSTRUCTIONS: Record<string, string> = {
  infographic: [
    'Create a clean educational infographic with strong visual hierarchy.',
    'Use organized layout with clear sections, readable labels, and simple icons.',
    'Flat design style with arrows/lines showing relationships.',
    'Include clear text labels, annotations, and headings where needed.'
  ].join(' '),

  process: [
    'Create a clean process diagram or flowchart.',
    'Use numbered steps with directional arrows and simple icons for each step.',
    'Left-to-right or top-to-bottom flow with consistent spacing.',
    'Include step numbers and brief text labels.'
  ].join(' '),

  comparison: [
    'Create a clean comparison chart.',
    'Use side-by-side or grid layout with clear column/row headers.',
    'Balanced visual weight with consistent icons.',
    'Include category labels and key differentiators as text.',
    'Max 4-6 items for clarity.'
  ].join(' '),

  safety: [
    'Create a safety information graphic with high contrast.',
    'Use internationally recognized hazard symbols where applicable.',
    'Include safety labels and brief instructional text.',
    'Use red/salmon only for warnings and danger emphasis.'
  ].join(' '),

  technical: [
    'Create a technical equipment diagram.',
    'Use clean line drawings or simplified illustrations with labeled parts.',
    'Include component labels with leader lines.',
    'Accurate proportions, organized label placement, professional technical illustration style.'
  ].join(' '),

  illustration: [
    'Create a professional educational illustration.',
    'Clean, modern style supporting the lesson content.',
    'No text needed unless it improves instructional value.',
    'Avoid cartoonish or photorealistic styles.'
  ].join(' '),

  photo: [
    'Create a realistic, professional photograph.',
    'Show drone pilots or operators in field operations, not airline imagery.',
    'High-visibility safety clothing, practical outdoor gear, controllers.',
    'Aspirational yet real — avoid stock photo aesthetics.'
  ].join(' ')
}

// ── Helpers ──

function detectMimeType(filePath: string): string {
  const ext = extname(filePath).toLowerCase()
  const map: Record<string, string> = {
    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
    '.png': 'image/png', '.webp': 'image/webp',
    '.gif': 'image/gif', '.svg': 'image/svg+xml',
    '.avif': 'image/avif'
  }
  return map[ext] || 'image/png'
}

function readImageAsBase64(filePath: string): { base64: string; mimeType: string } {
  const buffer = readFileSync(filePath)
  return {
    base64: buffer.toString('base64'),
    mimeType: detectMimeType(filePath)
  }
}

// ── Build prompt ──

function buildPrompt(
  userPrompt: string,
  brandContent: string | null,
  style: string | undefined
): string {
  const parts: string[] = []

  parts.push(`Create an image: ${userPrompt}`)

  if (style && STYLE_INSTRUCTIONS[style]) {
    parts.push(`\nImage style — ${style}:\n${STYLE_INSTRUCTIONS[style]}`)
  }

  if (brandContent) {
    parts.push(`\nBrand guidelines:\n${brandContent}`)
  }

  // Universal quality instructions
  parts.push([
    '',
    'Composition: Use a standard 16:9 landscape layout. Do not create panoramic or ultra-wide.',
    'Text quality: All visible text must be spelled correctly in clear professional English. If clean text cannot be rendered reliably, use fewer words.',
    'Do not add course titles, module titles, footer metadata, or captions unless specifically requested.',
    'Do not duplicate icons, labels, or visual elements unnecessarily.',
    'Keep typography and icon style consistent throughout.'
  ].join('\n'))

  return parts.join('\n')
}

// ── Build API request parts ──

interface ContentPart {
  text?: string
  inline_data?: { mime_type: string; data: string }
}

function buildRequestParts(
  prompt: string,
  refImages: Array<{ base64: string; mimeType: string; label?: string }>,
  logoImage: { base64: string; mimeType: string } | null
): ContentPart[] {
  const parts: ContentPart[] = []

  // Add reference images first (Gemini expects images before text)
  for (const ref of refImages) {
    if (ref.label) {
      parts.push({ text: ref.label })
    }
    parts.push({
      inline_data: { mime_type: ref.mimeType, data: ref.base64 }
    })
  }

  // Add logo as final reference image
  if (logoImage) {
    parts.push({ text: 'Tenant logo — place in top-right corner on a dark green (#253C29) badge. Keep small with clean padding.' })
    parts.push({
      inline_data: { mime_type: logoImage.mimeType, data: logoImage.base64 }
    })
  }

  // Add the text prompt last
  parts.push({ text: prompt })

  return parts
}

// ── Call Gemini API ──

async function generateImage(
  model: string,
  parts: ContentPart[],
  config: { aspectRatio: string; imageSize: string; thinking: string }
): Promise<{ imageData: Buffer; mimeType: string; text?: string }> {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`

  const body: Record<string, unknown> = {
    contents: [{ parts }],
    generationConfig: {
      responseModalities: ['TEXT', 'IMAGE'],
      imageConfig: {
        aspectRatio: config.aspectRatio,
        imageSize: config.imageSize
      }
    }
  }

  if (config.thinking) {
    (body as any).generationConfig.thinkingConfig = {
      thinkingLevel: config.thinking
    }
  }

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'x-goog-api-key': GEMINI_API_KEY!,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(body)
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`Gemini API error ${response.status}: ${errorText}`)
  }

  const data = await response.json() as any

  // Extract image and optional text from response
  let imageData: Buffer | null = null
  let imageMimeType = 'image/png'
  let responseText: string | undefined

  for (const candidate of data.candidates || []) {
    for (const part of candidate.content?.parts || []) {
      if (part.inlineData?.data) {
        imageData = Buffer.from(part.inlineData.data, 'base64')
        imageMimeType = part.inlineData.mimeType || 'image/png'
      } else if (part.text && !part.thoughtSignature) {
        responseText = part.text
      }
    }
  }

  if (!imageData) {
    // Log full response for debugging
    console.error('Full API response:', JSON.stringify(data, null, 2).slice(0, 2000))
    throw new Error('No image data in Gemini response')
  }

  return { imageData, mimeType: imageMimeType, text: responseText }
}

// ── Main ──

async function main() {
  const repoPath = values.repo!
  const userPrompt = values.prompt!
  const style = values.style
  const aspectRatio = values['aspect-ratio']!
  const imageSize = values.size!
  const model = values.model!
  const refPaths = (values.ref as string[] | undefined) || []
  const refLabels = (values['ref-label'] as string[] | undefined) || []
  const noLogo = values['no-logo']
  const noBrand = values['no-brand']
  const thinking = values.thinking!
  const dryRun = values['dry-run']

  // Default output path
  const outputPath = values.output || `./generated-${Date.now()}.png`

  // Read brand.md
  let brandContent: string | null = null
  if (!noBrand) {
    const brandPath = join(repoPath, 'brand.md')
    if (existsSync(brandPath)) {
      brandContent = readFileSync(brandPath, 'utf-8')
      console.log(`Brand: loaded from ${brandPath}`)
    } else {
      console.warn(`Warning: brand.md not found at ${brandPath}`)
    }
  }

  // Read logo
  let logoImage: { base64: string; mimeType: string } | null = null
  if (!noLogo) {
    const logoPath = join(repoPath, 'branding', 'logo.png')
    if (existsSync(logoPath)) {
      logoImage = readImageAsBase64(logoPath)
      console.log(`Logo: loaded from ${logoPath}`)
    } else {
      console.warn(`Warning: logo not found at ${logoPath}`)
    }
  }

  // Read reference images
  const refImages: Array<{ base64: string; mimeType: string; label?: string }> = []
  for (let i = 0; i < refPaths.length; i++) {
    const refPath = refPaths[i]
    if (!existsSync(refPath)) {
      console.error(`Reference image not found: ${refPath}`)
      process.exit(1)
    }
    const img = readImageAsBase64(refPath)
    refImages.push({
      ...img,
      label: refLabels[i] || `Reference image ${i + 1}`
    })
    console.log(`Ref ${i + 1}: loaded ${refPath} (${img.mimeType})`)
  }

  if (refImages.length + (logoImage ? 1 : 0) > 14) {
    console.error(`Error: Too many reference images (${refImages.length} + logo). Gemini supports max 14.`)
    process.exit(1)
  }

  // Build prompt
  const prompt = buildPrompt(userPrompt, brandContent, style)

  console.log(`\nModel: ${model}`)
  console.log(`Style: ${style || '(auto)'}`)
  console.log(`Aspect ratio: ${aspectRatio}`)
  console.log(`Image size: ${imageSize}`)
  console.log(`Thinking: ${thinking}`)
  console.log(`Reference images: ${refImages.length}${logoImage ? ' + logo' : ''}`)
  console.log(`Output: ${outputPath}`)
  console.log(`\n${'─'.repeat(60)}`)
  console.log('PROMPT:')
  console.log(`${'─'.repeat(60)}`)
  console.log(prompt)
  console.log(`${'─'.repeat(60)}\n`)

  if (dryRun) {
    console.log('[dry-run] Would call Gemini API with the above prompt.')
    return
  }

  // Build request parts
  const parts = buildRequestParts(prompt, refImages, logoImage)

  // Call API
  console.log('Generating image...')
  const startTime = Date.now()

  const result = await generateImage(model, parts, {
    aspectRatio,
    imageSize,
    thinking
  })

  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1)
  console.log(`Generated in ${elapsed}s (${result.mimeType})`)

  if (result.text) {
    console.log(`\nModel notes: ${result.text}`)
  }

  // Ensure output directory exists
  const outDir = dirname(outputPath)
  if (outDir && outDir !== '.') {
    mkdirSync(outDir, { recursive: true })
  }

  // Write image
  writeFileSync(outputPath, result.imageData)
  console.log(`\nSaved to: ${outputPath}`)

  // Write metadata sidecar
  const metaPath = outputPath.replace(/\.[^.]+$/, '.meta.json')
  writeFileSync(metaPath, JSON.stringify({
    prompt: userPrompt,
    fullPrompt: prompt,
    style,
    model,
    aspectRatio,
    imageSize,
    thinking,
    mimeType: result.mimeType,
    refImages: refPaths,
    brandFile: brandContent ? join(repoPath, 'brand.md') : null,
    logoIncluded: !!logoImage,
    generatedAt: new Date().toISOString(),
    elapsedSeconds: parseFloat(elapsed),
    modelNotes: result.text || null
  }, null, 2) + '\n')
  console.log(`Metadata: ${metaPath}`)
}

main().catch((err) => {
  console.error('Error:', err.message || err)
  process.exit(1)
})
