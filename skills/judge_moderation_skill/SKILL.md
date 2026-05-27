# judge_moderation_skill

## Metadata
- **name**: judge_moderation_skill
- **intended_agents**: judge
- **trigger**: Before each round begins and when summarising after a round ends.

## Input Schema
```json
{
  "type": "object",
  "properties": {
    "round": {"type": "integer"},
    "topic": {"type": "string"},
    "previous_summary": {"type": "string"}
  },
  "required": ["round", "topic"]
}
```

## Output Schema
```json
{
  "type": "object",
  "properties": {
    "message_type": {"const": "moderation"},
    "content": {"type": "string"},
    "addressed_to": {"type": "string", "enum": ["pro", "con", "both"]}
  },
  "required": ["message_type", "content"]
}
```
