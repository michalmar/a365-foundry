---
name: azure-foundry-image-generation
description: Generate images with GPT Image models through the Azure AI Foundry OpenAI-compatible endpoint. Use when presentation, documentation, or UI work needs architecture image variants generated from prompts.
license: MIT
metadata:
  author: local
  version: "1.0.0"
---

# Azure Foundry Image Generation

Use this skill to generate image variants with an Azure AI Foundry GPT Image deployment using Microsoft Entra ID authentication.

## Configuration

The generator reads configuration from this skill's local `.env` file first, then from process environment variables.

Required variables:

```env
AZURE_FOUNDRY_IMAGE_ENDPOINT=https://<resource>.services.ai.azure.com/openai/v1
AZURE_FOUNDRY_IMAGE_DEPLOYMENT=gpt-image-2
```

Optional variable:

```env
AZURE_FOUNDRY_IMAGE_TOKEN_SCOPE=https://ai.azure.com/.default
```

Do not put API keys or secrets in the skill `.env`. The script uses `DefaultAzureCredential`, so authenticate locally with `az login` or run in Azure with managed identity.

## Usage

Generate four architecture image variants from a prompt file:

```bash
python .agents/skills/azure-foundry-image-generation/scripts/generate_images.py \
  --prompt-file prompt.txt \
  --output-dir output/architecture-images \
  --prefix architecture_variant \
  --n 4 \
  --size 1792x1008 \
  --quality high
```

Generate from inline prompt text:

```bash
python .agents/skills/azure-foundry-image-generation/scripts/generate_images.py \
  --prompt "A polished Azure hub-and-spoke multi-agent architecture diagram" \
  --output-dir output/architecture-images
```

## Runtime Notes

Image generation is a synchronous API call and can take several minutes. The script prints authentication and generation progress to stderr; use `--quiet` if you only want generated file paths on stdout.

If a request is taking too long, use a lower quality setting or smaller image size, or cap the request with `--timeout`:

```bash
python .agents/skills/azure-foundry-image-generation/scripts/generate_images.py \
  --prompt "A polished Azure hub-and-spoke multi-agent architecture diagram" \
  --quality low \
  --timeout 180
```

On macOS system Python, urllib3 may warn that Python is compiled with LibreSSL instead of OpenSSL. The script suppresses that known warning by default because it is not the cause of slow generation; pass `--show-ssl-warning` to display it.

## Recommended Prompt Pattern

For architecture diagrams, specify:

- Diagram structure, e.g. layered, hub-and-spoke, identity/data flow
- Required labels and platform services
- Visual style and brand constraints
- Slide-safe aspect ratio and margin needs
- Negative constraints such as no people, no code snippets, no fictional logos
