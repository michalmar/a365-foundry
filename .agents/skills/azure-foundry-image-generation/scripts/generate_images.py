#!/usr/bin/env python3
"""Generate images with Azure AI Foundry GPT Image deployments."""

from __future__ import annotations

import argparse
import base64
import os
import sys
import time
import warnings
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = SKILL_DIR / ".env"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def read_prompt(args: argparse.Namespace) -> str:
    if args.prompt and args.prompt_file:
        raise ValueError("Use either --prompt or --prompt-file, not both.")
    if args.prompt:
        return args.prompt
    if args.prompt_file:
        return Path(args.prompt_file).read_text(encoding="utf-8")
    raise ValueError("A prompt is required. Pass --prompt or --prompt-file.")


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def configure_warnings(show_ssl_warning: bool) -> None:
    if show_ssl_warning:
        return

    warnings.filterwarnings(
        "ignore",
        message=r"urllib3 v2 only supports OpenSSL 1\.1\.1\+.*",
        category=Warning,
        module=r"urllib3",
    )


def status(message: str, quiet: bool) -> None:
    if not quiet:
        print(message, file=sys.stderr, flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate images with an Azure AI Foundry GPT Image deployment."
    )
    prompt_group = parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompt", help="Inline prompt text.")
    prompt_group.add_argument("--prompt-file", help="Path to a UTF-8 prompt file.")
    parser.add_argument("--output-dir", default="generated-images", help="Directory for PNG outputs.")
    parser.add_argument("--prefix", default="generated_image", help="Output filename prefix.")
    parser.add_argument("--n", type=int, default=1, help="Number of images to generate.")
    parser.add_argument("--size", default="1024x1024", help="Image size, e.g. 1024x1024 or 1792x1008.")
    parser.add_argument("--quality", default=None, choices=["low", "medium", "high"], help="Optional image quality.")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_PATH), help="Path to an env file.")
    parser.add_argument("--timeout", type=float, default=600.0, help="API request timeout in seconds.")
    parser.add_argument("--max-retries", type=int, default=2, help="Maximum OpenAI client retries.")
    parser.add_argument("--quiet", action="store_true", help="Only print generated output paths.")
    parser.add_argument(
        "--show-ssl-warning",
        action="store_true",
        help="Show urllib3 LibreSSL warnings from macOS system Python.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate config and prompt without calling the API.")
    args = parser.parse_args()
    validate_args(parser, args)
    return args


def validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.n < 1:
        parser.error("--n must be at least 1.")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0.")
    if args.max_retries < 0:
        parser.error("--max-retries must be 0 or greater.")


def main() -> None:
    args = parse_args()
    load_env_file(Path(args.env_file))

    endpoint = require_env("AZURE_FOUNDRY_IMAGE_ENDPOINT")
    deployment = require_env("AZURE_FOUNDRY_IMAGE_DEPLOYMENT")
    scope = os.getenv("AZURE_FOUNDRY_IMAGE_TOKEN_SCOPE", "https://ai.azure.com/.default")
    prompt = read_prompt(args)

    if args.dry_run:
        print(f"endpoint={endpoint}")
        print(f"deployment={deployment}")
        print(f"scope={scope}")
        print(f"images={args.n}")
        print(f"size={args.size}")
        print(f"timeout={args.timeout}")
        print(f"max_retries={args.max_retries}")
        print(f"prompt_chars={len(prompt)}")
        return

    configure_warnings(args.show_ssl_warning)

    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    from openai import OpenAI

    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(exclude_interactive_browser_credential=False),
        scope,
    )

    status("Authenticating with Azure...", args.quiet)
    auth_start = time.perf_counter()
    token_provider()
    status(f"Authenticated in {time.perf_counter() - auth_start:.1f}s.", args.quiet)

    client = OpenAI(
        base_url=endpoint,
        api_key=token_provider,
        timeout=args.timeout,
        max_retries=args.max_retries,
    )

    request = {
        "model": deployment,
        "prompt": prompt,
        "n": args.n,
        "size": args.size,
    }
    if args.quality:
        request["quality"] = args.quality

    status(
        f"Submitting image generation request (n={args.n}, size={args.size}, quality={args.quality or 'default'}). "
        "This can take several minutes...",
        args.quiet,
    )
    generation_start = time.perf_counter()
    result = client.images.generate(**request)
    status(f"Image generation completed in {time.perf_counter() - generation_start:.1f}s.", args.quiet)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for index, item in enumerate(result.data, start=1):
        output_path = output_dir / f"{args.prefix}_{index}.png"
        output_path.write_bytes(base64.b64decode(item.b64_json))
        print(output_path)


if __name__ == "__main__":
    main()
