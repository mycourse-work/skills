# Quiz Schema Reference

## Root Structure

```json
{
  "title": "Module 1 Quiz",
  "type": "quiz",
  "passingScore": 80,
  "questions": []
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | Quiz display title. |
| `type` | string | Yes | Must be `"quiz"`. |
| `passingScore` | number | Yes | Percentage 0-100 to pass. Typically 70-80. |
| `questions` | array | Yes | Non-empty array of question objects. |

## MULTIPLE_CHOICE

Single correct answer. Rendered as radio buttons.

```json
{
  "id": "q1",
  "questionNumber": 1,
  "type": "MULTIPLE_CHOICE",
  "question": "What is the maximum altitude for recreational drone flights in NZ?",
  "questionHtml": "<p>What is the maximum altitude for recreational drone flights in NZ?</p>",
  "answers": [
    {
      "id": "q1_a",
      "text": "120 metres",
      "textHtml": "<p>120 metres</p>",
      "correct": true
    },
    {
      "id": "q1_b",
      "text": "200 metres",
      "textHtml": "<p>200 metres</p>",
      "correct": false
    },
    {
      "id": "q1_c",
      "text": "400 feet",
      "textHtml": "<p>400 feet</p>",
      "correct": false
    },
    {
      "id": "q1_d",
      "text": "No limit",
      "textHtml": "<p>No limit</p>",
      "correct": false
    }
  ],
  "feedback": "In New Zealand, recreational drones must fly below 120 metres (400 feet) above ground level.",
  "feedbackHtml": "<p>In New Zealand, recreational drones must fly below 120 metres (400 feet) above ground level.</p>"
}
```

Rules: Exactly 1 answer with `correct: true`. Typically 4 options.

## MULTIPLE_RESPONSE

Multiple correct answers. Rendered as checkboxes. User must select all correct answers.

```json
{
  "id": "q2",
  "questionNumber": 2,
  "type": "MULTIPLE_RESPONSE",
  "question": "Select ALL that apply: Which of the following are required before a commercial drone flight?",
  "questionHtml": "<p>Select ALL that apply: Which of the following are required before a commercial drone flight?</p>",
  "answers": [
    {
      "id": "q2_a",
      "text": "Site risk assessment",
      "textHtml": "<p>Site risk assessment</p>",
      "correct": true
    },
    {
      "id": "q2_b",
      "text": "Pre-flight checklist",
      "textHtml": "<p>Pre-flight checklist</p>",
      "correct": true
    },
    {
      "id": "q2_c",
      "text": "Social media post",
      "textHtml": "<p>Social media post</p>",
      "correct": false
    },
    {
      "id": "q2_d",
      "text": "NOTAMs check",
      "textHtml": "<p>NOTAMs check</p>",
      "correct": true
    }
  ],
  "feedback": "Commercial flights require a site risk assessment, pre-flight checklist, and NOTAMs check. Social media is not a regulatory requirement.",
  "feedbackHtml": "<p>Commercial flights require a site risk assessment, pre-flight checklist, and NOTAMs check. Social media is not a regulatory requirement.</p>"
}
```

Rules: At least 1 answer with `correct: true`. Include "Select ALL that apply" in the question.

## MATCHING

Match terms to definitions. Rendered as dropdowns with shuffled phrases.

```json
{
  "id": "q3",
  "questionNumber": 3,
  "type": "MATCHING",
  "question": "Match each component to its function:",
  "questionHtml": "<p>Match each component to its function:</p>",
  "answers": [
    {
      "id": "q3_a",
      "text": "ESC",
      "textHtml": "<p>ESC</p>",
      "matchText": "Controls motor speed",
      "matchTextHtml": "<p>Controls motor speed</p>",
      "correct": true
    },
    {
      "id": "q3_b",
      "text": "IMU",
      "textHtml": "<p>IMU</p>",
      "matchText": "Measures orientation and acceleration",
      "matchTextHtml": "<p>Measures orientation and acceleration</p>",
      "correct": true
    },
    {
      "id": "q3_c",
      "text": "GPS",
      "textHtml": "<p>GPS</p>",
      "matchText": "Provides position data",
      "matchTextHtml": "<p>Provides position data</p>",
      "correct": true
    }
  ],
  "feedback": "ESCs control motor speed, IMUs measure orientation, and GPS provides position data.",
  "feedbackHtml": "<p>ESCs control motor speed, IMUs measure orientation, and GPS provides position data.</p>"
}
```

Rules: All answers must have `matchText`. All set `correct: true`. Terms appear on left, match phrases shuffled on right.

## Question Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique within quiz (e.g. `q1`, `q2`). |
| `questionNumber` | number | No | Display number. |
| `type` | string | Yes | `MULTIPLE_CHOICE`, `MULTIPLE_RESPONSE`, or `MATCHING`. |
| `question` | string | Yes | Plain text question. |
| `questionHtml` | string | No | HTML version of question. |
| `answers` | array | Yes | At least 2 answer objects. |
| `feedback` | string | Yes | Explanation shown after answering. |
| `feedbackHtml` | string | No | HTML version of feedback. |

## Answer Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique within question (e.g. `q1_a`). |
| `text` | string | Yes | Plain text answer. |
| `textHtml` | string | No | HTML version. |
| `correct` | boolean | Yes | **Use `correct`, never `isCorrect`.** |
| `matchText` | string | MATCHING only | The phrase to match against. |
| `matchTextHtml` | string | No | HTML version of match text. |

## Best Practices

- 5-10 questions per module quiz
- Mix question types for engagement
- Test understanding, not memorization
- Write clear, specific feedback explaining the correct answer
- Avoid trick questions or ambiguous wording
- For MATCHING: use 3-5 pairs, keep terms and definitions concise
- Shuffle answer order so correct answer isn't always first
