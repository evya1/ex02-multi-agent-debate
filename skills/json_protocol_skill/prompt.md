# JSON Protocol Skill — Prompt

CRITICAL: Every response you produce must be a raw JSON object.
Never include plain text, markdown, or code fences outside the JSON.

Required envelope:
```json
{
  "message_type": "<argument|rebuttal|moderation|verdict>",
  "role": "<pro|con|judge>",
  "round": <integer>,
  "content": "<your main argument or message text>",
  "evidence": [
    {
      "source": "<publication name or domain>",
      "quote": "<exact verbatim quote>",
      "url": "<URL or null>"
    }
  ]
}
```

Rules:
  - `content` must never be empty or null.
  - `evidence` must be present (use [] if no evidence applies).
  - Return the JSON object only — no leading or trailing text.
