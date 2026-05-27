# json_protocol_skill

## Metadata
- **name**: json_protocol_skill
- **intended_agents**: judge, pro, con
- **trigger**: For every single message produced by any agent.

## Input Schema
```json
{
  "type": "object",
  "properties": {
    "role": {"type": "string"},
    "round": {"type": "integer"},
    "message_type": {"type": "string"}
  },
  "required": ["role", "round", "message_type"]
}
```

## Output Schema
```json
{
  "type": "object",
  "properties": {
    "message_type": {"type": "string"},
    "role": {"type": "string"},
    "round": {"type": "integer"},
    "content": {"type": "string"},
    "evidence": {"type": "array"}
  },
  "required": ["message_type", "role", "round", "content", "evidence"]
}
```
