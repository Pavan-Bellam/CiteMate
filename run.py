#!/usr/bin/env python3
"""
Run script for RAS services.

Usage:
    python run.py producer build  - Build producer image
    python run.py producer up     - Run producer container
    python run.py producer down   - Stop producer container
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

    if service not in ["producer"]:
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
        run_compose(["up", service], env)
    elif command == "down":
        run_compose(["down"], env)
    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
