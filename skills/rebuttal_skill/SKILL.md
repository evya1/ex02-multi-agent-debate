# rebuttal_skill

## Metadata
- **name**: rebuttal_skill
- **intended_agents**: pro, con
- **trigger**: In rounds 2+, when the agent must respond to the opponent's previous message.

## Input Schema
```json
{
  "type": "object",
  "properties": {
    "opponent_argument": {"type": "string"},
    "round": {"type": "integer"}
  },
  "required": ["opponent_argument", "round"]
}
```

## Output Schema
```json
{
  "type": "object",
  "properties": {
    "message_type": {"const": "rebuttal"},
    "content": {"type": "string"},
    "evidence": {"type": "array"}
  },
  "required": ["message_type", "content"]
}
```
