# con_argument_skill

## Metadata
- **name**: con_argument_skill
- **intended_agents**: con
- **trigger**: When presenting an opening argument or advancing a new claim (round 1, or after a rebuttal).

## Input Schema
```json
{
  "type": "object",
  "properties": {
    "topic": {"type": "string"},
    "round": {"type": "integer"}
  },
  "required": ["topic", "round"]
}
```

## Output Schema
```json
{
  "type": "object",
  "properties": {
    "message_type": {"const": "argument"},
    "content": {"type": "string"},
    "evidence": {"type": "array"}
  },
  "required": ["message_type", "content", "evidence"]
}
```
