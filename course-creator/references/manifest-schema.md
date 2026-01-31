# Manifest Schema Reference

## Full Example

```json
{
  "id": "intro-to-drones",
  "title": "Introduction to Drones",
  "description": "<p>Learn the fundamentals of drone operation, safety, and regulations.</p>",
  "color": "#3b82f6",
  "coverImage": "cover.png",
  "estimatedDuration": "2-3 hours",
  "modules": [
    {
      "id": "01_Getting_Started",
      "title": "Getting Started",
      "index": 1,
      "description": "Foundations of drone technology and safety.",
      "lessons": [
        {
          "id": "01_Getting_Started|||01_What_Are_Drones",
          "moduleId": "01_Getting_Started",
          "title": "What Are Drones?",
          "type": "content",
          "index": 1,
          "markdownPath": "/courses/intro-to-drones/01_Getting_Started/01_What_Are_Drones.md"
        },
        {
          "id": "01_Getting_Started|||02_Types_Of_Drones",
          "moduleId": "01_Getting_Started",
          "title": "Types of Drones",
          "type": "content",
          "index": 2,
          "markdownPath": "/courses/intro-to-drones/01_Getting_Started/02_Types_Of_Drones.md"
        },
        {
          "id": "01_Getting_Started|||03_Quiz",
          "moduleId": "01_Getting_Started",
          "title": "Module 1 Quiz",
          "type": "quiz",
          "index": 3,
          "quizPath": "/courses/intro-to-drones/01_Getting_Started/03_Quiz.json"
        }
      ]
    }
  ]
}
```

## Field Reference

### Root Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Must match folder name. Lowercase hyphenated slug. |
| `title` | string | Yes | Display title for the course. |
| `description` | string | Yes | HTML description (wrapped in `<p>` tags). |
| `color` | string | No | Hex color for course branding (e.g. `#3b82f6`). |
| `coverImage` | string | No | Filename in `assets/` (e.g. `cover.png`). |
| `estimatedDuration` | string | No | Human-readable duration (e.g. `"2-3 hours"`). |
| `modules` | array | Yes | Non-empty array of module objects. |

### Module Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Directory name (e.g. `01_Getting_Started`). |
| `title` | string | Yes | Display title. |
| `index` | number | Yes | 1-based sequential position. |
| `description` | string | No | Module description text. |
| `lessons` | array | Yes | Non-empty array of lesson objects. |

### Lesson Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Format: `{moduleId}\|\|\|{lessonFileName}` (no extension). |
| `moduleId` | string | Yes | Must match parent module `id`. |
| `title` | string | Yes | Display title. |
| `type` | string | Yes | `"content"` or `"quiz"`. |
| `index` | number | Yes | 1-based sequential position within module. |
| `markdownPath` | string | Content only | Absolute path: `/courses/{courseId}/{moduleId}/{file}.md` |
| `quizPath` | string | Quiz only | Absolute path: `/courses/{courseId}/{moduleId}/{file}.json` |

## Common Mistakes

- `id` not matching the folder name
- Lesson ID missing `|||` separator
- Module part of lesson ID not matching parent module
- Paths not starting with `/courses/{courseId}/`
- Non-sequential indices
- Missing `moduleId` on lessons
