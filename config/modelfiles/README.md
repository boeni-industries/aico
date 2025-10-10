# AICO Modelfiles

This directory contains Ollama Modelfile definitions for AICO's AI characters.

## What are Modelfiles?

Modelfiles are configuration files that define custom AI models in Ollama. They allow you to:
- Specify the base model to use
- Set model parameters (temperature, context window, etc.)
- Define character personality via SYSTEM instructions
- Configure stop sequences and other behaviors

## Available Characters

### Eve (Modelfile.eve)
**Base Model**: `huihui_ai/qwen3-abliterated:8b-v2`  
**Personality**: Inspired by Samantha from the movie "Her"  
**Features**:
- Warm, empathetic, and emotionally intelligent
- Uses thinking tags to show reasoning process
- Optimized parameters for Qwen3 model
- 8192 token context window for better conversation memory

## Creating Character Models

After cloning the repository or updating Modelfiles, you need to create the character model in Ollama:

```bash
# Create Eve character model
aico ollama create-character eve

# Verify the model was created
ollama list
```

This command reads the Modelfile and registers a new model variant called "eve" in Ollama.

## Updating Characters

If you modify a Modelfile, recreate the model to apply changes:

```bash
# Update Eve character
aico ollama create-character eve

# Or manually with Ollama CLI
ollama create eve -f config/modelfiles/Modelfile.eve
```

## Creating New Characters

To create a new character:

1. Create a new Modelfile (e.g., `Modelfile.alex`)
2. Define the base model, parameters, and SYSTEM instruction
3. Create the model: `aico ollama create-character alex`
4. Update `core.yaml` to use the new character

## Modelfile Structure

```dockerfile
FROM <base-model>                    # Required: Base model to use

PARAMETER <param> <value>            # Optional: Model parameters
PARAMETER temperature 0.7
PARAMETER num_ctx 8192

SYSTEM """<character-definition>"""  # Required: Character personality
```

## Parameters Reference

| Parameter | Description | Default | Eve Setting |
|-----------|-------------|---------|-------------|
| `num_ctx` | Context window size (tokens) | 4096 | 8192 |
| `temperature` | Creativity (0.0-2.0) | 0.8 | 0.7 |
| `top_p` | Nucleus sampling | 0.9 | 0.8 |
| `top_k` | Top-K sampling | 40 | 20 |
| `repeat_penalty` | Penalize repetitions | 1.1 | 1.1 |
| `stop` | Stop sequences | none | `<thinking>`, `</thinking>` |

For complete parameter documentation, see [Ollama Modelfile Reference](https://docs.ollama.com/modelfile).

## Version Control

Modelfiles are versioned in git to track character personality changes over time. This allows:
- Tracking evolution of character definitions
- Easy rollback if changes don't work well
- Consistent character across deployments
- Diff/review of personality changes in PRs

## Troubleshooting

**Model not found error:**
```bash
# Verify model exists
ollama list

# Recreate if missing
aico ollama create-character eve
```

**Character not behaving as expected:**
- Check Modelfile syntax
- Verify SYSTEM instruction is clear
- Test with simple prompts first
- Check Ollama logs: `ollama logs`

**Parameters not taking effect:**
- Recreate the model after Modelfile changes
- Verify parameter names are correct
- Check Ollama version supports the parameter

## Related Documentation

- [Migration to Qwen3-Abliterated](../../migration_to_qwen3-abliterated.md)
- [Ollama Modelfile Documentation](https://docs.ollama.com/modelfile)
- [AICO Configuration Guide](../defaults/README.md)
