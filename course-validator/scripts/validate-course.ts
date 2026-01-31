import { readFileSync, existsSync, readdirSync, statSync } from 'fs'
import { join, basename, extname } from 'path'
import { JSDOM } from 'jsdom'

// ─── DOM Setup (required before mermaid import) ─────────────────────────────

const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>')
// @ts-expect-error — minimal DOM globals for mermaid.parse()
global.window = dom.window
global.document = dom.window.document
Object.defineProperty(global, 'navigator', { value: dom.window.navigator, writable: true })

// ─── Imports that depend on DOM globals ─────────────────────────────────────

const { lexer } = await import('marked')
const mermaid = (await import('mermaid')).default
mermaid.initialize({ startOnLoad: false })

// ─── Types ───────────────────────────────────────────────────────────────────

interface Manifest {
  id: string
  title: string
  description: string
  color: string
  coverImage?: string
  modules: ManifestModule[]
}

interface ManifestModule {
  id: string
  title: string
  index: number
  description?: string
  lessons: ManifestLesson[]
}

interface ManifestLesson {
  id: string
  moduleId: string
  title: string
  type: 'content' | 'quiz' | 'section'
  index: number
  markdownPath?: string
  quizPath?: string
}

interface QuizFile {
  title: string
  type: string
  passingScore?: number
  questions: QuizQuestion[]
}

interface QuizQuestion {
  id: string
  type: string
  question: string
  answers: QuizAnswer[]
  feedback?: string
}

interface QuizAnswer {
  id: string
  text: string
  correct?: boolean
  isCorrect?: boolean
  matchText?: string
}

// ─── Result Tracking ─────────────────────────────────────────────────────────

type Severity = 'pass' | 'error' | 'warning'

interface Result {
  severity: Severity
  message: string
}

const results: Result[] = []

function pass(msg: string) {
  results.push({ severity: 'pass', message: msg })
}

function error(msg: string) {
  results.push({ severity: 'error', message: msg })
}

function warn(msg: string) {
  results.push({ severity: 'warning', message: msg })
}

function printResults() {
  for (const r of results) {
    const icon = r.severity === 'pass' ? '✓' : r.severity === 'error' ? '✗' : '⚠'
    console.log(`  ${icon} ${r.message}`)
  }

  const passes = results.filter(r => r.severity === 'pass').length
  const errors = results.filter(r => r.severity === 'error').length
  const warnings = results.filter(r => r.severity === 'warning').length

  console.log()
  console.log(`Results: ${passes} passed, ${errors} error${errors !== 1 ? 's' : ''}, ${warnings} warning${warnings !== 1 ? 's' : ''}`)

  return errors
}

// ─── Validators ──────────────────────────────────────────────────────────────

function validateManifest(coursePath: string): Manifest | null {
  const manifestPath = join(coursePath, 'manifest.json')

  if (!existsSync(manifestPath)) {
    error('manifest.json not found')
    return null
  }

  let manifest: Manifest
  try {
    const raw = readFileSync(manifestPath, 'utf-8')
    manifest = JSON.parse(raw)
    pass('manifest.json exists and is valid JSON')
  } catch (e) {
    error(`manifest.json is not valid JSON: ${(e as Error).message}`)
    return null
  }

  // Required fields
  const requiredFields = ['id', 'title', 'description', 'modules'] as const
  const missingFields = requiredFields.filter(f => !(f in manifest))
  if (missingFields.length > 0) {
    error(`Missing required manifest fields: ${missingFields.join(', ')}`)
  } else {
    pass('Required manifest fields present')
  }

  // ID matches folder name
  const folderName = basename(coursePath)
  if (manifest.id && manifest.id !== folderName) {
    error(`manifest.id "${manifest.id}" does not match folder name "${folderName}"`)
  } else if (manifest.id) {
    pass(`manifest.id matches folder name "${folderName}"`)
  }

  // Color validation
  if (manifest.color) {
    if (/^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(manifest.color)) {
      pass(`Color "${manifest.color}" is a valid hex color`)
    } else {
      error(`Color "${manifest.color}" is not a valid hex color`)
    }
  }

  // Modules
  if (!Array.isArray(manifest.modules) || manifest.modules.length === 0) {
    error('modules must be a non-empty array')
    return manifest
  }
  pass(`${manifest.modules.length} modules found`)

  return manifest
}

function validateModules(manifest: Manifest, coursePath: string) {
  const moduleIds = new Set<string>()
  const lessonIds = new Set<string>()
  const referencedFiles = new Set<string>()

  // Check module indices are sequential (if present)
  const hasModuleIndices = manifest.modules.every(m => m.index !== undefined)
  if (hasModuleIndices) {
    const moduleIndices = manifest.modules.map(m => m.index)
    const expectedIndices = manifest.modules.map((_, i) => i + 1)
    if (JSON.stringify(moduleIndices) === JSON.stringify(expectedIndices)) {
      pass('Module indices are sequential (1-based)')
    } else {
      error(`Module indices are not sequential. Expected [${expectedIndices}], got [${moduleIndices}]`)
    }
  } else {
    warn('Module indices not present — will be inferred from array position')
  }

  for (const mod of manifest.modules) {
    // Required module fields
    if (!mod.id || !mod.title) {
      error(`Module missing required fields (id, title): ${JSON.stringify({ id: mod.id, title: mod.title })}`)
      continue
    }

    // Duplicate module ID
    if (moduleIds.has(mod.id)) {
      error(`Duplicate module ID: "${mod.id}"`)
    }
    moduleIds.add(mod.id)

    // Module directory exists
    const moduleDirPath = join(coursePath, mod.id)
    if (!existsSync(moduleDirPath)) {
      error(`Module directory not found: ${mod.id}/`)
    }

    // Check module dir name pattern
    if (!/^\d{2}_/.test(mod.id)) {
      warn(`Module ID "${mod.id}" does not follow ##_Name pattern`)
    }

    // Validate lessons
    if (!Array.isArray(mod.lessons) || mod.lessons.length === 0) {
      warn(`Module "${mod.id}" has no lessons`)
      continue
    }

    // Check lesson indices are sequential (if present)
    const hasLessonIndices = mod.lessons.every(l => l.index !== undefined)
    if (hasLessonIndices) {
      const lessonIndices = mod.lessons.map(l => l.index)
      const expectedLessonIndices = mod.lessons.map((_, i) => i + 1)
      if (JSON.stringify(lessonIndices) !== JSON.stringify(expectedLessonIndices)) {
        error(`Lesson indices in module "${mod.id}" are not sequential. Expected [${expectedLessonIndices}], got [${lessonIndices}]`)
      }
    }

    for (const lesson of mod.lessons) {
      // Required lesson fields
      if (!lesson.id || !lesson.title || !lesson.type) {
        error(`Lesson missing required fields (id, title, type): ${JSON.stringify({ id: lesson.id, title: lesson.title, type: lesson.type })}`)
        continue
      }

      // Duplicate lesson ID
      if (lessonIds.has(lesson.id)) {
        error(`Duplicate lesson ID: "${lesson.id}"`)
      }
      lessonIds.add(lesson.id)

      // moduleId matches parent (if present)
      if (lesson.moduleId && lesson.moduleId !== mod.id) {
        error(`Lesson "${lesson.id}" has moduleId "${lesson.moduleId}" but is in module "${mod.id}"`)
      }

      // Lesson ID format: {moduleId}|||{lessonFileName}
      if (!lesson.id.includes('|||')) {
        error(`Lesson ID "${lesson.id}" does not use {moduleId}|||{fileName} format`)
      } else {
        const [idModulePart] = lesson.id.split('|||')
        if (idModulePart !== mod.id) {
          error(`Lesson ID "${lesson.id}" — module part does not match parent module "${mod.id}"`)
        }
      }

      // Type validation
      const validTypes = ['content', 'quiz', 'section']
      if (!validTypes.includes(lesson.type)) {
        error(`Lesson "${lesson.id}" has invalid type "${lesson.type}". Expected: ${validTypes.join(', ')}`)
      }

      // Content lessons need markdownPath
      if (lesson.type === 'content') {
        if (!lesson.markdownPath) {
          error(`Content lesson "${lesson.id}" missing markdownPath`)
        } else {
          // Check path pattern
          if (!lesson.markdownPath.startsWith(`/courses/${manifest.id}/`)) {
            error(`Lesson "${lesson.id}" markdownPath does not follow /courses/{courseId}/... pattern`)
          }
          // Check file exists on disk
          const mdRelative = lesson.markdownPath.replace(`/courses/${manifest.id}/`, '')
          const mdFullPath = join(coursePath, mdRelative)
          if (!existsSync(mdFullPath)) {
            error(`Lesson "${lesson.id}" — markdownPath file not found: ${mdRelative}`)
          }
          referencedFiles.add(mdRelative)
        }
      }

      // Quiz lessons need quizPath
      if (lesson.type === 'quiz') {
        if (!lesson.quizPath) {
          error(`Quiz lesson "${lesson.id}" missing quizPath`)
        } else {
          if (!lesson.quizPath.startsWith(`/courses/${manifest.id}/`)) {
            error(`Lesson "${lesson.id}" quizPath does not follow /courses/{courseId}/... pattern`)
          }
          const qzRelative = lesson.quizPath.replace(`/courses/${manifest.id}/`, '')
          const qzFullPath = join(coursePath, qzRelative)
          if (!existsSync(qzFullPath)) {
            error(`Lesson "${lesson.id}" — quizPath file not found: ${qzRelative}`)
          } else {
            validateQuizFile(qzFullPath, lesson.id)
          }
          referencedFiles.add(qzRelative)
        }
      }
    }
  }

  pass(`All ${lessonIds.size} lesson IDs are unique`)

  return referencedFiles
}

function validateQuizFile(quizPath: string, lessonId: string) {
  const fileName = basename(quizPath)
  let quiz: QuizFile
  try {
    const raw = readFileSync(quizPath, 'utf-8')
    quiz = JSON.parse(raw)
  } catch (e) {
    error(`Quiz "${fileName}" is not valid JSON: ${(e as Error).message}`)
    return
  }

  // Required fields
  if (!quiz.title) {
    error(`Quiz "${fileName}" missing title`)
  }
  if (quiz.type !== 'quiz') {
    error(`Quiz "${fileName}" type must be "quiz", got "${quiz.type}"`)
  }

  // passingScore
  if (quiz.passingScore === undefined) {
    warn(`Quiz "${fileName}" missing passingScore`)
  } else if (typeof quiz.passingScore !== 'number' || quiz.passingScore < 0 || quiz.passingScore > 100) {
    error(`Quiz "${fileName}" passingScore must be 0-100, got ${quiz.passingScore}`)
  }

  // Questions
  if (!Array.isArray(quiz.questions) || quiz.questions.length === 0) {
    error(`Quiz "${fileName}" must have at least one question`)
    return
  }

  const questionIds = new Set<string>()

  for (const q of quiz.questions) {
    if (!q.id) {
      error(`Quiz "${fileName}" has a question without an ID`)
      continue
    }

    if (questionIds.has(q.id)) {
      error(`Quiz "${fileName}" has duplicate question ID "${q.id}"`)
    }
    questionIds.add(q.id)

    const validTypes = ['MULTIPLE_CHOICE', 'MULTIPLE_RESPONSE', 'MATCHING']
    if (!validTypes.includes(q.type)) {
      error(`Quiz "${fileName}" question "${q.id}" has invalid type "${q.type}"`)
    }

    if (!q.question) {
      error(`Quiz "${fileName}" question "${q.id}" missing question text`)
    }

    if (!Array.isArray(q.answers) || q.answers.length < 2) {
      error(`Quiz "${fileName}" question "${q.id}" must have at least 2 answers`)
      continue
    }

    // Check for isCorrect bug
    const usesIsCorrect = q.answers.some((a: QuizAnswer) => 'isCorrect' in a)
    if (usesIsCorrect) {
      warn(`Quiz "${fileName}" question "${q.id}" uses "isCorrect" instead of "correct"`)
    }

    // Check correct field exists
    const usesCorrect = q.answers.some((a: QuizAnswer) => 'correct' in a)
    if (!usesCorrect && !usesIsCorrect) {
      error(`Quiz "${fileName}" question "${q.id}" answers missing "correct" field`)
    }

    // Type-specific checks
    if (q.type === 'MULTIPLE_CHOICE') {
      const correctCount = q.answers.filter((a: QuizAnswer) => a.correct === true).length
      if (correctCount !== 1) {
        error(`Quiz "${fileName}" MULTIPLE_CHOICE question "${q.id}" should have exactly 1 correct answer, found ${correctCount}`)
      }
    }

    if (q.type === 'MULTIPLE_RESPONSE') {
      const correctCount = q.answers.filter((a: QuizAnswer) => a.correct === true).length
      if (correctCount < 1) {
        error(`Quiz "${fileName}" MULTIPLE_RESPONSE question "${q.id}" should have at least 1 correct answer`)
      }
    }

    if (q.type === 'MATCHING') {
      const missingMatch = q.answers.filter((a: QuizAnswer) => !a.matchText)
      if (missingMatch.length > 0) {
        error(`Quiz "${fileName}" MATCHING question "${q.id}" has ${missingMatch.length} answer(s) missing matchText`)
      }
    }

    // Answer IDs
    for (const a of q.answers) {
      if (!a.id) {
        error(`Quiz "${fileName}" question "${q.id}" has an answer without an ID`)
      }
      if (!a.text) {
        error(`Quiz "${fileName}" question "${q.id}" answer "${a.id}" missing text`)
      }
    }
  }

  pass(`Quiz "${fileName}" structure is valid (${quiz.questions.length} questions)`)
}

// ─── Markdown & Mermaid Validation ──────────────────────────────────────────

function extractImages(tokens: any[]): { href: string; text: string }[] {
  const images: { href: string; text: string }[] = []
  for (const token of tokens) {
    if (token.type === 'image') {
      images.push({ href: token.href, text: token.text })
    }
    if (token.tokens) {
      images.push(...extractImages(token.tokens))
    }
    if (token.items) {
      for (const item of token.items) {
        if (item.tokens) {
          images.push(...extractImages(item.tokens))
        }
      }
    }
  }
  return images
}

async function validateMarkdownContent(filePath: string, relativePath: string, coursePath: string) {
  const content = readFileSync(filePath, 'utf-8')
  const tokens = lexer(content)

  // ── Heading hierarchy ──
  const headings = tokens.filter((t: any) => t.type === 'heading') as { depth: number; text: string }[]

  if (headings.length > 0) {
    // First heading should be H1
    if (headings[0].depth !== 1) {
      warn(`"${relativePath}" first heading is H${headings[0].depth}, expected H1`)
    }

    // Check for empty headings
    for (const h of headings) {
      if (!h.text || h.text.trim() === '') {
        error(`"${relativePath}" contains an empty H${h.depth} heading`)
      }
    }

    // Check for skipped heading levels
    for (let i = 1; i < headings.length; i++) {
      const prev = headings[i - 1].depth
      const curr = headings[i].depth
      if (curr > prev + 1) {
        warn(`"${relativePath}" skips heading level: H${prev} → H${curr}`)
      }
    }
  }

  // ── Image references ──
  const images = extractImages(tokens)
  for (const img of images) {
    if (/^https?:\/\//.test(img.href)) {
      warn(`"${relativePath}" references external image: ${img.href}`)
    } else if (img.href.startsWith('/courses/')) {
      // Resolve relative to course path: strip /courses/{courseId}/ prefix
      const courseId = basename(coursePath)
      const assetRelative = img.href.replace(`/courses/${courseId}/`, '')
      const assetFullPath = join(coursePath, assetRelative)
      if (!existsSync(assetFullPath)) {
        error(`"${relativePath}" references missing image: ${img.href} (expected at ${assetRelative})`)
      }
    }
  }

  // ── Mermaid diagrams ──
  const mermaidBlocks = tokens.filter((t: any) => t.type === 'code' && t.lang === 'mermaid')
  for (let i = 0; i < mermaidBlocks.length; i++) {
    const block = mermaidBlocks[i] as { text: string }
    try {
      await mermaid.parse(block.text, { suppressErrors: false })
      // Extract diagram type from first line
      const firstLine = block.text.trim().split('\n')[0].trim()
      const diagramType = firstLine.split(/[\s{]/)[0]
      pass(`"${relativePath}" mermaid diagram ${i + 1} is valid (${diagramType})`)
    } catch (e: any) {
      const msg = e.message || String(e)
      // Truncate long parse errors to first line
      const shortMsg = msg.split('\n')[0]
      error(`"${relativePath}" mermaid diagram ${i + 1} has syntax error: ${shortMsg}`)
    }
  }
}

async function validateMarkdownFiles(coursePath: string, referencedFiles: Set<string>) {
  // Walk module directories for .md files and check they have headings
  const modules = readdirSync(coursePath).filter(f => {
    const fullPath = join(coursePath, f)
    return statSync(fullPath).isDirectory() && /^\d{2}_/.test(f)
  })

  for (const modDir of modules) {
    const modPath = join(coursePath, modDir)
    const files = readdirSync(modPath)

    for (const file of files) {
      const ext = extname(file)
      const relativePath = `${modDir}/${file}`

      // Check for unexpected file types
      if (!['.md', '.json'].includes(ext)) {
        warn(`Unexpected file type in ${modDir}/: ${file}`)
        continue
      }

      if (ext === '.md') {
        const fullPath = join(modPath, file)
        const content = readFileSync(fullPath, 'utf-8').trim()

        if (content.length === 0) {
          error(`Markdown file "${relativePath}" is empty`)
        } else if (!content.startsWith('# ')) {
          warn(`Markdown file "${relativePath}" does not start with a # heading`)
        }

        // Markdown content validation (headings, images, mermaid)
        if (content.length > 0) {
          await validateMarkdownContent(fullPath, relativePath, coursePath)
        }

        // Check for orphans
        if (!referencedFiles.has(relativePath)) {
          warn(`Orphaned file: "${relativePath}" is not referenced in manifest`)
        }
      }

      if (ext === '.json') {
        if (!referencedFiles.has(relativePath)) {
          warn(`Orphaned file: "${relativePath}" is not referenced in manifest`)
        }
      }

      // Check naming pattern
      if (!/^\d{2}_/.test(file)) {
        warn(`File "${relativePath}" does not follow ##_Name pattern`)
      }
    }
  }
}

function validateDirectoryStructure(coursePath: string) {
  // Check assets directory
  const assetsPath = join(coursePath, 'assets')
  if (!existsSync(assetsPath)) {
    warn('No assets/ directory found')
  } else {
    pass('assets/ directory exists')
  }

  // Check module directories follow pattern
  const entries = readdirSync(coursePath).filter(f => {
    const fullPath = join(coursePath, f)
    return statSync(fullPath).isDirectory() && f !== 'assets' && !f.startsWith('.')
  })

  for (const dir of entries) {
    if (!/^\d{2}_/.test(dir)) {
      warn(`Directory "${dir}" does not follow ##_Name pattern`)
    }
  }
}

// ─── Main ────────────────────────────────────────────────────────────────────

async function main() {
  const coursePath = process.argv[2]

  if (!coursePath) {
    console.error('Usage: pnpm validate-course <path-to-course-folder>')
    console.error('  e.g. pnpm validate-course content/tenants/openclaw/courses/openclaw-security-hardening')
    process.exit(1)
  }

  // Resolve relative to cwd
  const resolvedPath = join(process.cwd(), coursePath)

  if (!existsSync(resolvedPath)) {
    console.error(`Error: Course folder not found: ${resolvedPath}`)
    process.exit(1)
  }

  if (!statSync(resolvedPath).isDirectory()) {
    console.error(`Error: Path is not a directory: ${resolvedPath}`)
    process.exit(1)
  }

  const courseId = basename(resolvedPath)
  console.log(`Validating course: ${courseId}`)
  console.log()

  // 1. Validate manifest
  const manifest = validateManifest(resolvedPath)
  if (!manifest) {
    const errorCount = printResults()
    process.exit(errorCount > 0 ? 1 : 0)
  }

  // 2. Validate modules and lessons
  const referencedFiles = validateModules(manifest, resolvedPath)

  // 3. Validate markdown files (content + orphan check + markdown/mermaid validation)
  await validateMarkdownFiles(resolvedPath, referencedFiles)

  // 4. Validate directory structure
  validateDirectoryStructure(resolvedPath)

  // Print results
  console.log()
  const errorCount = printResults()
  process.exit(errorCount > 0 ? 1 : 0)
}

main()
