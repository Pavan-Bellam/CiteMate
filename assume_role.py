#!/usr/bin/env python3
"""
Assume the RAS developer role and output environment variables.

Usage:
    # PowerShell - set environment variables
    python assume_role.py | Invoke-Expression

    # Or just print credentials
    python assume_role.py --print
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# Load config
ROOT_DIR = Path(__file__).parent
CONFIG_PATH = ROOT_DIR / "config.json"


def load_config() -> dict:
    """Load configuration from config.json."""
    if not CONFIG_PATH.exists():
        print(f"Error: Config file not found: {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(CONFIG_PATH) as f:
        return json.load(f)


def get_username() -> str:
    """Get the current IAM username."""
    try:
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity"],
            capture_output=True,
            text=True,
            check=True,
        )
        identity = json.loads(result.stdout)
        arn = identity["Arn"]
        # Extract username from ARN like arn:aws:iam::123456789:user/username
        if ":user/" in arn:
            return arn.split(":user/")[-1]
        else:
            print(f"Error: Expected IAM user, got: {arn}", file=sys.stderr)
            sys.exit(1)
    except subprocess.CalledProcessError as e:
        print("Error: Failed to get AWS identity", file=sys.stderr)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        sys.exit(1)


def assume_role(role_arn: str, username: str) -> dict:
    """
    Assume the developer role with source identity.

    Args:
        role_arn: The role ARN to assume
        username: IAM username to use as source identity

    Returns:
        Credentials dictionary
    """
    try:
        result = subprocess.run(
            [
                "aws", "sts", "assume-role",
                "--role-arn", role_arn,
                "--role-session-name", f"{username}-session",
                "--source-identity", username,
                "--output", "json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to assume role {role_arn}", file=sys.stderr)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    config = load_config()
    account_id = config["aws_account_id"]
    project_name = config["project_name"]
    role_arn = f"arn:aws:iam::{account_id}:role/{project_name}-developer-role"

    # Get current username
    username = get_username()

    # Assume role
    response = assume_role(role_arn, username)
    creds = response["Credentials"]

    # Check if user wants to just print
    if len(sys.argv) > 1 and sys.argv[1] == "--print":
        print(f"AWS_ACCESS_KEY_ID={creds['AccessKeyId']}")
        print(f"AWS_SECRET_ACCESS_KEY={creds['SecretAccessKey']}")
        print(f"AWS_SESSION_TOKEN={creds['SessionToken']}")
    else:
        # Output PowerShell commands to set environment variables
        print(f'$env:AWS_ACCESS_KEY_ID = "{creds["AccessKeyId"]}"')
        print(f'$env:AWS_SECRET_ACCESS_KEY = "{creds["SecretAccessKey"]}"')
        print(f'$env:AWS_SESSION_TOKEN = "{creds["SessionToken"]}"')


if __name__ == "__main__":
    main()
