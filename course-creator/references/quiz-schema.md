# Quiz format (format v1)

The machine-readable version is `schema/quiz.schema.json`. `schema/RULES.md` lists every rule and its severity.

A quiz is a JSON file in the module folder, listed in the module manifest as a `quiz` lesson with `quizPath`.

## Root

```json
{
  "title": "Rules Quiz",
  "type": "quiz",
  "questions": []
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | yes | |
| `type` | `"quiz"` | yes | Missing or different → error. |
| `questions` | array | yes | Not empty. Question ids are unique. |
| `passingScore` | — | **don't author** | Ignored by the player and the grader. The validator warns. |

**The pass mark is set per course**, in `course.json`: `"quizPassingThreshold": 80` (default 80). When answers are revealed is also per course: `quizRevealMode`.

## Question fields

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Unique in the quiz, e.g. `q1`. |
| `type` | yes | `MULTIPLE_CHOICE`, `MULTIPLE_RESPONSE` or `MATCHING`. |
| `question` | yes | Plain text. `questionHtml` is optional. |
| `answers` | yes | At least 2. |
| `feedback` | recommended | The explanation. **This is the only feedback learners see.** `feedbackHtml` is optional. |
| `questionNumber` | no | Integer ≥ 1. The player numbers questions by position. |
| `image`, `imageAlt` | no | `image` is a file name in the **course** folder's `assets/` (`courses/<course>/assets/<image>`), not the module's. |

Answer fields: `id` (required, unique in the question), `text` (required), `correct` (boolean), `matchText` (for `MATCHING`), and optional `textHtml` / `matchTextHtml`.

- Use `correct`. **Never `isCorrect`**: the grader does not read it, so the question can never be passed. This is an error.
- Answer-level `feedback` is never shown to learners. Put the explanation in the question's `feedback`.
- Answer ids: `<questionId>_<letter>`, e.g. `q1_a`.

## MULTIPLE_CHOICE

Exactly one answer has `correct: true`.

```json
{
  "id": "q1",
  "type": "MULTIPLE_CHOICE",
  "question": "What is the maximum height for a Part 101 flight without a shielded operation?",
  "answers": [
    { "id": "q1_a", "text": "60 m", "correct": false },
    { "id": "q1_b", "text": "120 m", "correct": true },
    { "id": "q1_c", "text": "400 m", "correct": false }
  ],
  "feedback": "Part 101 limits flights to 120 m above ground level unless the operation is shielded."
}
```

## MULTIPLE_RESPONSE

At least one answer has `correct: true`. Say "Select all that apply" in the question.

```json
{
  "id": "q2",
  "type": "MULTIPLE_RESPONSE",
  "question": "Which of these must you check before flight? Select all that apply.",
  "answers": [
    { "id": "q2_a", "text": "Battery charge", "correct": true },
    { "id": "q2_b", "text": "Airspace", "correct": true },
    { "id": "q2_c", "text": "Your social media", "correct": false }
  ],
  "feedback": "Battery and airspace checks are part of every pre-flight."
}
```

## MATCHING

Every answer has `text` (left) and `matchText` (right). The grader checks each pair. `correct` is not needed.

```json
{
  "id": "q3",
  "type": "MATCHING",
  "question": "Match each colour to its airspace.",
  "answers": [
    { "id": "q3_a", "text": "Red", "matchText": "Restricted area" },
    { "id": "q3_b", "text": "Blue", "matchText": "Controlled airspace" }
  ],
  "feedback": "Restricted areas need permission from the administering authority; controlled airspace needs an ATC clearance."
}
```

## TRUE_FALSE (legacy)

`TRUE_FALSE` is not a platform type. The player plays it as `MULTIPLE_CHOICE`, so it works, but the validator warns. For new content, use `MULTIPLE_CHOICE` with the two answers "True" and "False".

## Good practice

- 5-10 questions per module quiz. Mix the types.
- Test the lesson's learning outcomes. Use scenarios rather than recall where you can.
- No trick wording, and no implausible distractors.
