# AICO Modelfiles

## Overview

Modelfiles define AI character personalities and model parameters for AICO. They use Ollama's native Modelfile format.

## Available Characters

### Eve (`Modelfile.eve`)
- **Base Model**: `huihui_ai/qwen3-abliterated:8b-v2`
- **Personality**: Inspired by Samantha from "Her" - warm, curious, emotionally intelligent
- **Parameters**: Optimized for Qwen3 (temp=0.7, top_p=0.8, top_k=20, num_ctx=8192)
- **Thinking Tags**: Uses `<think>` tags for inner monologue

## Usage

### Generate Character Model
```bash
aico ollama generate eve
```

This command:
1. Reads the Modelfile
2. Creates the character model in Ollama
3. Makes it available for conversations

### Verify Character
```bash
ollama list          # Check if model exists
ollama run eve       # Test interactively
```

### Update Character
To update after modifying a Modelfile:
```bash
aico ollama generate eve --force
```

## Modelfile Structure

```dockerfile
FROM <base-model>                    # Base model to use
PARAMETER <name> <value>             # Model parameters
SYSTEM """<character-definition>"""  # Character personality
```

## Creating New Characters

1. Create `Modelfile.<name>` in this directory
2. Define FROM, PARAMETER, and SYSTEM sections
3. Generate with `aico ollama generate <name>`
4. Update `core.yaml` to use the new character

## Parameters Reference

| Parameter | Description | Eve Default |
|-----------|-------------|-------------|
| `num_ctx` | Context window size | 8192 |
| `temperature` | Creativity (0.0-2.0) | 0.7 |
| `top_p` | Nucleus sampling | 0.8 |
| `top_k` | Top-K sampling | 20 |
| `repeat_penalty` | Penalize repetitions | 1.1 |

## Notes

- Modelfiles are versioned in git
- Character models are created locally via Ollama
- One deployment can have multiple character models
- Backend configuration selects which character to use
