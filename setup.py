#!/usr/bin/env python3
"""
Setup script for RAS project infrastructure.

Usage:
    python setup.py bootstrap init    - Initialize terraform for bootstrap
    python setup.py bootstrap apply   - Apply bootstrap infrastructure
    python setup.py bootstrap destroy - Destroy bootstrap infrastructure

    python setup.py dev init          - Initialize terraform for dev environment
    python setup.py dev apply         - Apply dev infrastructure
    python setup.py dev destroy       - Destroy dev infrastructure
"""

import json
import subprocess
import sys
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).parent
CONFIG_PATH = ROOT_DIR / "config.json"
BOOTSTRAP_DIR = ROOT_DIR / "terraform" / "bootstrap"
DEV_DIR = ROOT_DIR / "terraform" / "envs" / "development"


# =============================================================================
# Utilities
# =============================================================================

def run_command(
    cmd: list[str],
    cwd: Path | None = None,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    """
    Run a command and handle errors.

    Args:
        cmd: Command and arguments as list
        cwd: Working directory for the command
        capture_output: If True, capture stdout/stderr instead of streaming

    Returns:
        CompletedProcess instance

    Raises:
        SystemExit: If command fails
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            check=True,
        )
        return result
    except FileNotFoundError:
        print(f"Error: Command not found: {cmd[0]}")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error: Command failed: {' '.join(cmd)}")
        if e.stderr:
            print(e.stderr)
        sys.exit(1)


def load_config() -> dict:
    """Load configuration from config.json."""
    if not CONFIG_PATH.exists():
        print(f"Error: Config file not found: {CONFIG_PATH}")
        sys.exit(1)

    with open(CONFIG_PATH) as f:
        return json.load(f)


def check_terraform() -> None:
    """Check if terraform is installed."""
    print("Checking terraform...")
    try:
        subprocess.run(["terraform", "--version"], capture_output=True, check=True)
        print("  OK")
    except FileNotFoundError:
        print("Error: terraform not installed")
        print("  Install: https://developer.hashicorp.com/terraform/downloads")
        sys.exit(1)


def check_aws_cli() -> None:
    """Check if AWS CLI is installed and configured."""
    print("Checking AWS CLI...")
    try:
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity"],
            capture_output=True,
            text=True,
            check=True,
        )
        identity = json.loads(result.stdout)
        print(f"  OK - {identity['Arn']}")
    except FileNotFoundError:
        print("Error: AWS CLI not installed")
        print("  Install: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print("Error: AWS credentials not configured")
        if e.stderr:
            print(f"  {e.stderr.strip()}")
        sys.exit(1)


# =============================================================================
# Bootstrap
# =============================================================================

def bootstrap_init() -> None:
    """Initialize terraform for bootstrap."""
    print("\n=== Bootstrap Init ===\n")
    check_terraform()

    print("\nRunning terraform init...")
    run_command(["terraform", "init", "--reconfigure"], cwd=BOOTSTRAP_DIR)

    print("\n=== Init Complete ===")
    print("\nNext: python setup.py bootstrap apply")


def bootstrap_apply() -> None:
    """Apply bootstrap infrastructure."""
    print("\n=== Bootstrap Apply ===\n")
    check_terraform()
    check_aws_cli()

    config = load_config()

    print("\nRunning terraform apply...")
    run_command([
        "terraform", "apply",
        "-auto-approve",
        f"-var=project_name={config['project_name']}",
        f"-var=aws_region={config['aws_region']}",
        f"-var=aws_account_id={config['aws_account_id']}",
        f"-var=bucket_name={config['bootstrap']['bucket_name']}",
    ], cwd=BOOTSTRAP_DIR)

    print("\n=== Bootstrap Complete ===")
    print("\nNext steps:")
    print("  1. Add your IAM user to the 'ras-developers' group")
    print("  2. Run: python assume_role.py | Invoke-Expression")


def bootstrap_destroy() -> None:
    """Destroy bootstrap infrastructure."""
    print("\n=== Bootstrap Destroy ===\n")
    check_terraform()
    check_aws_cli()

    config = load_config()

    print("\nRunning terraform destroy...")
    run_command([
        "terraform", "destroy",
        "-auto-approve",
        f"-var=project_name={config['project_name']}",
        f"-var=aws_region={config['aws_region']}",
        f"-var=aws_account_id={config['aws_account_id']}",
        f"-var=bucket_name={config['bootstrap']['bucket_name']}",
    ], cwd=BOOTSTRAP_DIR)

    print("\n=== Destroy Complete ===")


# =============================================================================
# Dev
# =============================================================================

def dev_init() -> None:
    """Initialize terraform for dev environment."""
    print("\n=== Dev Init ===\n")
    check_terraform()
    check_aws_cli()

    config = load_config()

    # Generate backend config
    backend_config = DEV_DIR / "dev.tfbackend"
    backend_content = f"""bucket = "{config['bootstrap']['bucket_name']}"
key    = "development/{config['username']}/terraform/terraform.tfstate"
region = "{config['aws_region']}"
"""
    print(f"Writing backend config: {backend_config}")
    backend_config.write_text(backend_content)

    print("\nRunning terraform init...")
    run_command([
        "terraform", "init",
        "-reconfigure",
        "-backend-config=dev.tfbackend",
    ], cwd=DEV_DIR)

    print("\n=== Init Complete ===")
    print("\nNext: python setup.py dev apply")


def dev_apply() -> None:
    """Apply dev infrastructure."""
    print("\n=== Dev Apply ===\n")
    check_terraform()
    check_aws_cli()

    config = load_config()

    print("\nRunning terraform apply...")
    redis_config = config.get("redis", {})
    run_command([
        "terraform", "apply",
        "-auto-approve",
        f"-var=project_name={config['project_name']}",
        f"-var=aws_region={config['aws_region']}",
        f"-var=bucket_name={config['bootstrap']['bucket_name']}",
        f"-var=developer={config['username']}",
        f"-var=redis_db_name={redis_config.get('redis_db_name', f'{config["project_name"]}-dev-{config["username"]}')}",
        f"-var=redis_primary_region={redis_config.get('redis_primary_region', 'us-east-1')}",
        f"-var=redis_tls={str(redis_config.get('redis_tls', True)).lower()}",
    ], cwd=DEV_DIR)

    print("\n=== Apply Complete ===")


def dev_destroy() -> None:
    """Destroy dev infrastructure."""
    print("\n=== Dev Destroy ===\n")
    check_terraform()
    check_aws_cli()

    config = load_config()

    print("\nRunning terraform destroy...")
    run_command([
        "terraform", "destroy",
        "-auto-approve",
        f"-var=project_name={config['project_name']}",
        f"-var=aws_region={config['aws_region']}",
        f"-var=bucket_name={config['bootstrap']['bucket_name']}",
        f"-var=developer={config['username']}",
    ], cwd=DEV_DIR)

    print("\n=== Destroy Complete ===")


# =============================================================================
# Main
# =============================================================================

def print_usage() -> None:
    """Print usage information."""
    print(__doc__)


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1]

    if command == "bootstrap":
        if len(sys.argv) < 3:
            print("Usage: python setup.py bootstrap <init|apply|destroy>")
            sys.exit(1)

        subcommand = sys.argv[2]
        if subcommand == "init":
            bootstrap_init()
        elif subcommand == "apply":
            bootstrap_apply()
        elif subcommand == "destroy":
            bootstrap_destroy()
        else:
            print(f"Unknown bootstrap subcommand: {subcommand}")
            sys.exit(1)

    elif command == "dev":
        if len(sys.argv) < 3:
            print("Usage: python setup.py dev <init|apply|destroy>")
            sys.exit(1)

        subcommand = sys.argv[2]
        if subcommand == "init":
            dev_init()
        elif subcommand == "apply":
            dev_apply()
        elif subcommand == "destroy":
            dev_destroy()
        else:
            print(f"Unknown dev subcommand: {subcommand}")
            sys.exit(1)

    elif command in ["-h", "--help", "help"]:
        print_usage()

    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
