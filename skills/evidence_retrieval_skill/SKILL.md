# evidence_retrieval_skill

## Metadata
- **name**: evidence_retrieval_skill
- **intended_agents**: pro, con
- **trigger**: Whenever an argument or rebuttal needs factual backing. Always retrieve at least one piece of evidence per message.

## Input Schema
```json
{
  "type": "object",
  "properties": {
    "query": {"type": "string"}
  },
  "required": ["query"]
}
```

## Output Schema
```json
{
  "type": "object",
  "properties": {
    "source": {"type": "string"},
    "quote": {"type": "string"},
    "url": {"type": "string"}
  },
  "required": ["source", "quote"]
}
```
