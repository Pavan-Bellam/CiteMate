#!/usr/bin/env python3
"""
Run script for RAS services.

Usage:
    python run.py producer build        - Build producer image
    python run.py producer up           - Run producer container
    python run.py producer down         - Stop producer container
    python run.py consumer build        - Build consumer image
    python run.py consumer up [mode]    - Run consumer (mode: parse, process, full)
    python run.py consumer down         - Stop consumer container

Consumer modes:
    parse   - Consume from SQS, parse PDFs, save raw elements to S3
    process - Load raw elements from S3, chunk all papers (no SQS needed)
    full    - Parse and process in one pipeline (default)
"""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent
CONFIG_PATH = ROOT_DIR / "config.json"


def load_config() -> dict:
    """Load configuration from config.json."""
    if not CONFIG_PATH.exists():
        print(f"Error: Config file not found: {CONFIG_PATH}")
        sys.exit(1)

    with open(CONFIG_PATH) as f:
        return json.load(f)


def get_env(config: dict) -> dict:
    """Build environment variables for docker-compose."""
    env = os.environ.copy()

    username = config["username"]
    project = config["project_name"]
    region = config["aws_region"]
    account_id = config["aws_account_id"]

    # S3 config
    env["BUCKET_NAME"] = config["bootstrap"]["bucket_name"]
    env["BUCKET_PREFIX"] = f"development/{username}/papers"
    env["AWS_REGION"] = region

    # SQS config
    queue_name = f"{project}-dev-{username}-papers"
    env["QUEUE_URL"] = f"https://sqs.{region}.amazonaws.com/{account_id}/{queue_name}"

    # Producer config
    env["ARXIV_CATEGORY"] = config["producer"]["arxiv_category"]
    env["MAX_RESULTS"] = str(config["producer"]["max_results"])
    env["MAX_PAGES"] = str(config["producer"].get("max_pages", 20))

    # Consumer config
    consumer = config.get("consumer", {})
    env["CHUNK_MAX_CHARACTERS"] = str(consumer.get("chunk_max_characters", 1500))
    env["CHUNK_NEW_AFTER_N_CHARS"] = str(consumer.get("chunk_new_after_n_chars", 1000))
    env["CHUNK_COMBINE_UNDER_N_CHARS"] = str(consumer.get("chunk_combine_under_n_chars", 500))
    env["EMBEDDING_MODEL"] = consumer.get("embedding_model", "text-embedding-3-small")
    env["EMBEDDING_TOKEN_THRESHOLD"] = str(consumer.get("embedding_token_threshold", 8000))
    env["PINECONE_INDEX_NAME"] = consumer.get("pinecone_index_name", "")
    env["EMBEDDING_DIMENSION"] = config.get("pinecone", {}).get("embedding_dimension", "1536")

    return env


def run_compose(args: list[str], env: dict) -> None:
    """Run docker-compose command."""
    cmd = ["docker-compose"] + args
    print(f"Running: {' '.join(cmd)}")

    try:
        subprocess.run(cmd, env=env, check=True, cwd=ROOT_DIR)
    except FileNotFoundError:
        print("Error: docker-compose not found")
        sys.exit(1)
    except subprocess.CalledProcessError:
        sys.exit(1)


def print_usage() -> None:
    """Print usage information."""
    print(__doc__)


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 3:
        print_usage()
        sys.exit(1)

    service = sys.argv[1]
    command = sys.argv[2]

    if service not in ["producer", "consumer"]:
        print(f"Unknown service: {service}")
        print_usage()
        sys.exit(1)

    config = load_config()
    env = get_env(config)

    # Check AWS credentials are set
    if not env.get("AWS_ACCESS_KEY_ID"):
        print("Error: AWS credentials not set")
        print("Run: python assume_role.py | Invoke-Expression")
        sys.exit(1)

    if command == "build":
        run_compose(["build", service], env)
    elif command == "up":
        # Handle consumer mode argument
        if service == "consumer" and len(sys.argv) >= 4:
            mode = sys.argv[3]
            if mode not in ["parse", "process", "full"]:
                print(f"Unknown consumer mode: {mode}")
                print_usage()
                sys.exit(1)
            env["MODE"] = mode
        run_compose(["up", service], env)
    elif command == "down":
        run_compose(["down"], env)
    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
