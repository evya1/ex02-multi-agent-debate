# verdict_skill

## Metadata
- **name**: verdict_skill
- **intended_agents**: judge
- **trigger**: After all debate rounds are complete.

## Input Schema
```json
{
  "type": "object",
  "properties": {
    "topic": {"type": "string"},
    "full_transcript": {"type": "array"},
    "total_rounds": {"type": "integer"}
  },
  "required": ["topic", "full_transcript", "total_rounds"]
}
```

## Output Schema
```json
{
  "type": "object",
  "properties": {
    "message_type": {"const": "verdict"},
    "winner": {"type": "string", "enum": ["pro", "con"]},
    "total_pro_score": {"type": "number"},
    "total_con_score": {"type": "number"},
    "round_scores": {"type": "array"},
    "reasoning": {"type": "string"},
    "key_turning_point": {"type": "string"}
  },
  "required": ["message_type", "winner", "total_pro_score", "total_con_score", "reasoning", "key_turning_point"]
}
```
