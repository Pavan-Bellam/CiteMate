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

    python setup.py staging init      - Initialize terraform for staging (runs shared first)
    python setup.py staging apply     - Apply staging infrastructure (runs shared first)
    python setup.py staging destroy   - Destroy staging infrastructure

    python setup.py production init   - Initialize terraform for production (runs shared first)
    python setup.py production apply  - Apply production infrastructure (runs shared first)
    python setup.py production destroy- Destroy production infrastructure
"""

import json
import subprocess
import sys
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).parent
CONFIG_PATH = ROOT_DIR / "config.json"
ENV_PATH = ROOT_DIR / ".env"
BOOTSTRAP_DIR = ROOT_DIR / "terraform" / "bootstrap"
DEV_DIR = ROOT_DIR / "terraform" / "envs" / "development"
SHARED_DIR = ROOT_DIR / "terraform" / "envs" / "shared"
STAGING_DIR = ROOT_DIR / "terraform" / "envs" / "staging"
PRODUCTION_DIR = ROOT_DIR / "terraform" / "envs" / "production"


# =============================================================================
# Utilities
# =============================================================================

def run_command(
    cmd: list[str],
    cwd: Path | None = None,
    capture_output: bool = False,
    extra_env: dict | None = None,
) -> subprocess.CompletedProcess:
    """
    Run a command and handle errors.

    Args:
        cmd: Command and arguments as list
        cwd: Working directory for the command
        capture_output: If True, capture stdout/stderr instead of streaming
        extra_env: Additional environment variables to merge with current env

    Returns:
        CompletedProcess instance

    Raises:
        SystemExit: If command fails
    """
    import os
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            check=True,
            env=env,
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


def load_config(env: str | None = None) -> dict:
    """Load configuration from config.json or config.{env}.json."""
    if env:
        config_path = ROOT_DIR / f"config.{env}.json"
    else:
        config_path = CONFIG_PATH

    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)

    with open(config_path) as f:
        return json.load(f)


def load_env(required_keys: list[str]) -> dict:
    """Load secrets from .env file and validate required keys."""
    if not ENV_PATH.exists():
        print(f"Error: .env file not found: {ENV_PATH}")
        print("Create .env with the following variables:")
        for key in required_keys:
            print(f"  {key}=xxx")
        sys.exit(1)

    env_vars = {}
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip().strip('"').strip("'")

    # Validate required keys
    missing = [key for key in required_keys if key not in env_vars or not env_vars[key]]
    if missing:
        print(f"Error: Missing required environment variables in .env:")
        for key in missing:
            print(f"  {key}")
        sys.exit(1)

    return env_vars


def validate_config(config: dict, required_keys: list[str]) -> None:
    """Validate that required keys exist in config."""
    missing = []
    for key in required_keys:
        # Support nested keys like "bootstrap.bucket_name"
        parts = key.split(".")
        value = config
        try:
            for part in parts:
                value = value[part]
            if not value:
                missing.append(key)
        except (KeyError, TypeError):
            missing.append(key)

    if missing:
        print(f"Error: Missing required config keys:")
        for key in missing:
            print(f"  {key}")
        sys.exit(1)


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
    github_config = config.get("github", {})

    print("\nRunning terraform apply...")
    run_command([
        "terraform", "apply",
        "-auto-approve",
        f"-var=project_name={config['project_name']}",
        f"-var=aws_region={config['aws_region']}",
        f"-var=aws_account_id={config['aws_account_id']}",
        f"-var=bucket_name={config['bootstrap']['bucket_name']}",
        f"-var=github_org={github_config['org']}",
        f"-var=github_repository={github_config['repository']}",
        f"-var=main_branch={github_config.get('main_branch', 'main')}",
        f"-var=prod_branch={github_config.get('prod_branch', 'prod')}",
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
    github_config = config.get("github", {})

    print("\nRunning terraform destroy...")
    run_command([
        "terraform", "destroy",
        "-auto-approve",
        f"-var=project_name={config['project_name']}",
        f"-var=aws_region={config['aws_region']}",
        f"-var=aws_account_id={config['aws_account_id']}",
        f"-var=bucket_name={config['bootstrap']['bucket_name']}",
        f"-var=github_org={github_config['org']}",
        f"-var=github_repository={github_config['repository']}",
        f"-var=main_branch={github_config.get('main_branch', 'main')}",
        f"-var=prod_branch={github_config.get('prod_branch', 'prod')}",
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
# Shared
# =============================================================================

def shared_init(config: dict) -> None:
    """Initialize terraform for shared environment."""
    print("\n=== Shared Init ===\n")

    # Generate backend config
    backend_config = SHARED_DIR / "shared.tfbackend"
    backend_content = f"""bucket = "{config['bootstrap']['bucket_name']}"
key    = "shared/terraform/terraform.tfstate"
region = "{config['aws_region']}"
"""
    print(f"Writing backend config: {backend_config}")
    backend_config.write_text(backend_content)

    print("\nRunning terraform init...")
    run_command([
        "terraform", "init",
        "-reconfigure",
        "-backend-config=shared.tfbackend",
    ], cwd=SHARED_DIR)


def shared_apply(config: dict) -> None:
    """Apply shared infrastructure."""
    print("\n=== Shared Apply ===\n")

    print("\nRunning terraform apply...")
    run_command([
        "terraform", "apply",
        "-auto-approve",
        f"-var=project_name={config['project_name']}",
        f"-var=aws_region={config['aws_region']}",
    ], cwd=SHARED_DIR)

    print("\n=== Shared Apply Complete ===")


def shared_destroy(config: dict) -> None:
    """Destroy shared infrastructure."""
    print("\n=== Shared Destroy ===\n")

    print("\nRunning terraform destroy...")
    run_command([
        "terraform", "destroy",
        "-auto-approve",
        f"-var=project_name={config['project_name']}",
        f"-var=aws_region={config['aws_region']}",
    ], cwd=SHARED_DIR)

    print("\n=== Shared Destroy Complete ===")


# =============================================================================
# Staging
# =============================================================================

STAGING_REQUIRED_CONFIG = [
    "project_name",
    "aws_region",
    "aws_account_id",
    "bootstrap.bucket_name",
]

STAGING_REQUIRED_ENV = [
    "UNSTRUCTURED_API_KEY",
    "UPSTASH_EMAIL",
    "UPSTASH_API_KEY",
    "PINECONE_API_KEY",
    "OPENAI_API_KEY",
]


def staging_init() -> None:
    """Initialize terraform for staging environment (runs shared first)."""
    print("\n=== Staging Init ===\n")
    check_terraform()
    check_aws_cli()

    config = load_config("staging")
    validate_config(config, STAGING_REQUIRED_CONFIG)

    # Init shared first
    shared_init(config)

    # Generate backend config for staging
    backend_config = STAGING_DIR / "staging.tfbackend"
    backend_content = f"""bucket = "{config['bootstrap']['bucket_name']}"
key    = "staging/terraform/terraform.tfstate"
region = "{config['aws_region']}"
"""
    print(f"\nWriting backend config: {backend_config}")
    backend_config.write_text(backend_content)

    print("\nRunning terraform init for staging...")
    run_command([
        "terraform", "init",
        "-reconfigure",
        "-backend-config=staging.tfbackend",
    ], cwd=STAGING_DIR)

    print("\n=== Staging Init Complete ===")
    print("\nNext: python setup.py staging apply")


def staging_apply() -> None:
    """Apply staging infrastructure (runs shared first)."""
    print("\n=== Staging Apply ===\n")
    check_terraform()
    check_aws_cli()

    config = load_config("staging")
    validate_config(config, STAGING_REQUIRED_CONFIG)
    env_vars = load_env(STAGING_REQUIRED_ENV)

    # Apply shared first
    shared_apply(config)

    # Get ECR URLs from shared output
    print("\nGetting ECR repository URLs from shared...")
    result = run_command([
        "terraform", "output", "-json"
    ], cwd=SHARED_DIR, capture_output=True)
    shared_outputs = json.loads(result.stdout)
    producer_image = shared_outputs["producer_repository_url"]["value"] + ":latest"
    consumer_image = shared_outputs["consumer_repository_url"]["value"] + ":latest"

    print(f"  Producer image: {producer_image}")
    print(f"  Consumer image: {consumer_image}")

    # Apply staging
    print("\nRunning terraform apply for staging...")
    redis_config = config.get("redis", {})
    producer_config = config.get("producer", {})
    consumer_config = config.get("consumer", {})
    pinecone_config = config.get("pinecone", {})

    # Upstash provider needs these as environment variables
    upstash_env = {
        "UPSTASH_EMAIL": env_vars["UPSTASH_EMAIL"],
        "UPSTASH_API_KEY": env_vars["UPSTASH_API_KEY"],
    }

    run_command([
        "terraform", "apply",
        "-auto-approve",
        f"-var=project_name={config['project_name']}",
        f"-var=aws_region={config['aws_region']}",
        f"-var=bucket_name={config['bootstrap']['bucket_name']}",
        f"-var=redis_primary_region={redis_config.get('redis_primary_region', 'us-east-1')}",
        f"-var=redis_tls={str(redis_config.get('redis_tls', True)).lower()}",
        f"-var=producer_image={producer_image}",
        f"-var=consumer_image={consumer_image}",
        f"-var=unstructured_api_key={env_vars['UNSTRUCTURED_API_KEY']}",
        f"-var=upstash_email={env_vars['UPSTASH_EMAIL']}",
        f"-var=upstash_api_key={env_vars['UPSTASH_API_KEY']}",
        f"-var=pinecone_api_key={env_vars['PINECONE_API_KEY']}",
        f"-var=openai_api_key={env_vars['OPENAI_API_KEY']}",
        # Producer env vars
        f"-var=producer_arxiv_category={producer_config.get('arxiv_category', 'cs.AI,cs.LG,cs.CL')}",
        f"-var=producer_max_results={producer_config.get('max_results', 10)}",
        f"-var=producer_max_pages={producer_config.get('max_pages', 20)}",
        # Consumer env vars
        f"-var=consumer_mode={consumer_config.get('mode', 'full')}",
        f"-var=consumer_chunk_max_characters={consumer_config.get('chunk_max_characters', 1500)}",
        f"-var=consumer_chunk_new_after_n_chars={consumer_config.get('chunk_new_after_n_chars', 1000)}",
        f"-var=consumer_chunk_combine_under_n_chars={consumer_config.get('chunk_combine_under_n_chars', 500)}",
        f"-var=consumer_embedding_model={consumer_config.get('embedding_model', 'text-embedding-3-large')}",
        f"-var=consumer_embedding_token_threshold={consumer_config.get('embedding_token_threshold', 6000)}",
        f"-var=consumer_pinecone_index_name={consumer_config.get('pinecone_index_name', 'ras-papers')}",
        f"-var=consumer_embedding_dimension={pinecone_config.get('embedding_dimension', '3072')}",
    ], cwd=STAGING_DIR, extra_env=upstash_env)

    print("\n=== Staging Apply Complete ===")


def staging_destroy() -> None:
    """Destroy staging infrastructure."""
    print("\n=== Staging Destroy ===\n")
    check_terraform()
    check_aws_cli()

    config = load_config("staging")
    validate_config(config, STAGING_REQUIRED_CONFIG)
    env_vars = load_env(STAGING_REQUIRED_ENV)

    # Get ECR URLs from shared output
    print("\nGetting ECR repository URLs from shared...")
    result = run_command([
        "terraform", "output", "-json"
    ], cwd=SHARED_DIR, capture_output=True)
    shared_outputs = json.loads(result.stdout)
    producer_image = shared_outputs["producer_repository_url"]["value"] + ":latest"
    consumer_image = shared_outputs["consumer_repository_url"]["value"] + ":latest"

    print("\nRunning terraform destroy for staging...")
    redis_config = config.get("redis", {})
    producer_config = config.get("producer", {})
    consumer_config = config.get("consumer", {})
    pinecone_config = config.get("pinecone", {})

    # Upstash provider needs these as environment variables
    upstash_env = {
        "UPSTASH_EMAIL": env_vars["UPSTASH_EMAIL"],
        "UPSTASH_API_KEY": env_vars["UPSTASH_API_KEY"],
    }

    run_command([
        "terraform", "destroy",
        "-auto-approve",
        f"-var=project_name={config['project_name']}",
        f"-var=aws_region={config['aws_region']}",
        f"-var=bucket_name={config['bootstrap']['bucket_name']}",
        f"-var=redis_primary_region={redis_config.get('redis_primary_region', 'us-east-1')}",
        f"-var=redis_tls={str(redis_config.get('redis_tls', True)).lower()}",
        f"-var=producer_image={producer_image}",
        f"-var=consumer_image={consumer_image}",
        f"-var=unstructured_api_key={env_vars['UNSTRUCTURED_API_KEY']}",
        f"-var=upstash_email={env_vars['UPSTASH_EMAIL']}",
        f"-var=upstash_api_key={env_vars['UPSTASH_API_KEY']}",
        f"-var=pinecone_api_key={env_vars['PINECONE_API_KEY']}",
        f"-var=openai_api_key={env_vars['OPENAI_API_KEY']}",
        # Producer env vars
        f"-var=producer_arxiv_category={producer_config.get('arxiv_category', 'cs.AI,cs.LG,cs.CL')}",
        f"-var=producer_max_results={producer_config.get('max_results', 10)}",
        f"-var=producer_max_pages={producer_config.get('max_pages', 20)}",
        # Consumer env vars
        f"-var=consumer_mode={consumer_config.get('mode', 'full')}",
        f"-var=consumer_chunk_max_characters={consumer_config.get('chunk_max_characters', 1500)}",
        f"-var=consumer_chunk_new_after_n_chars={consumer_config.get('chunk_new_after_n_chars', 1000)}",
        f"-var=consumer_chunk_combine_under_n_chars={consumer_config.get('chunk_combine_under_n_chars', 500)}",
        f"-var=consumer_embedding_model={consumer_config.get('embedding_model', 'text-embedding-3-large')}",
        f"-var=consumer_embedding_token_threshold={consumer_config.get('embedding_token_threshold', 6000)}",
        f"-var=consumer_pinecone_index_name={consumer_config.get('pinecone_index_name', 'ras-papers')}",
        f"-var=consumer_embedding_dimension={pinecone_config.get('embedding_dimension', '3072')}",
    ], cwd=STAGING_DIR, extra_env=upstash_env)

    print("\n=== Staging Destroy Complete ===")
    print("\nNote: Shared infrastructure (ECR) was not destroyed.")
    print("To destroy shared: manually run terraform destroy in terraform/envs/shared/")


# =============================================================================
# Production
# =============================================================================

PRODUCTION_REQUIRED_CONFIG = [
    "project_name",
    "aws_region",
    "aws_account_id",
    "bootstrap.bucket_name",
]

PRODUCTION_REQUIRED_ENV = [
    "UNSTRUCTURED_API_KEY",
    "UPSTASH_EMAIL",
    "UPSTASH_API_KEY",
    "PINECONE_API_KEY",
    "OPENAI_API_KEY",
]


def production_init() -> None:
    """Initialize terraform for production environment (runs shared first)."""
    print("\n=== Production Init ===\n")
    check_terraform()
    check_aws_cli()

    config = load_config("production")
    validate_config(config, PRODUCTION_REQUIRED_CONFIG)

    # Init shared first
    shared_init(config)

    # Generate backend config for production
    backend_config = PRODUCTION_DIR / "production.tfbackend"
    backend_content = f"""bucket = "{config['bootstrap']['bucket_name']}"
key    = "production/terraform/terraform.tfstate"
region = "{config['aws_region']}"
"""
    print(f"\nWriting backend config: {backend_config}")
    backend_config.write_text(backend_content)

    print("\nRunning terraform init for production...")
    run_command([
        "terraform", "init",
        "-reconfigure",
        "-backend-config=production.tfbackend",
    ], cwd=PRODUCTION_DIR)

    print("\n=== Production Init Complete ===")
    print("\nNext: python setup.py production apply")


def production_apply() -> None:
    """Apply production infrastructure (runs shared first)."""
    print("\n=== Production Apply ===\n")
    check_terraform()
    check_aws_cli()

    config = load_config("production")
    validate_config(config, PRODUCTION_REQUIRED_CONFIG)
    env_vars = load_env(PRODUCTION_REQUIRED_ENV)

    # Apply shared first
    shared_apply(config)

    # Get ECR URLs from shared output
    print("\nGetting ECR repository URLs from shared...")
    result = run_command([
        "terraform", "output", "-json"
    ], cwd=SHARED_DIR, capture_output=True)
    shared_outputs = json.loads(result.stdout)
    producer_image = shared_outputs["producer_repository_url"]["value"] + ":latest"
    consumer_image = shared_outputs["consumer_repository_url"]["value"] + ":latest"

    print(f"  Producer image: {producer_image}")
    print(f"  Consumer image: {consumer_image}")

    # Apply production
    print("\nRunning terraform apply for production...")
    redis_config = config.get("redis", {})
    producer_config = config.get("producer", {})
    consumer_config = config.get("consumer", {})
    pinecone_config = config.get("pinecone", {})

    # Upstash provider needs these as environment variables
    upstash_env = {
        "UPSTASH_EMAIL": env_vars["UPSTASH_EMAIL"],
        "UPSTASH_API_KEY": env_vars["UPSTASH_API_KEY"],
    }

    run_command([
        "terraform", "apply",
        "-auto-approve",
        f"-var=project_name={config['project_name']}",
        f"-var=aws_region={config['aws_region']}",
        f"-var=bucket_name={config['bootstrap']['bucket_name']}",
        f"-var=redis_primary_region={redis_config.get('redis_primary_region', 'us-east-1')}",
        f"-var=redis_tls={str(redis_config.get('redis_tls', True)).lower()}",
        f"-var=producer_image={producer_image}",
        f"-var=consumer_image={consumer_image}",
        f"-var=unstructured_api_key={env_vars['UNSTRUCTURED_API_KEY']}",
        f"-var=upstash_email={env_vars['UPSTASH_EMAIL']}",
        f"-var=upstash_api_key={env_vars['UPSTASH_API_KEY']}",
        f"-var=pinecone_api_key={env_vars['PINECONE_API_KEY']}",
        f"-var=openai_api_key={env_vars['OPENAI_API_KEY']}",
        # Producer env vars
        f"-var=producer_arxiv_category={producer_config.get('arxiv_category', 'cs.AI,cs.LG,cs.CL')}",
        f"-var=producer_max_results={producer_config.get('max_results', 10)}",
        f"-var=producer_max_pages={producer_config.get('max_pages', 20)}",
        # Consumer env vars
        f"-var=consumer_mode={consumer_config.get('mode', 'full')}",
        f"-var=consumer_chunk_max_characters={consumer_config.get('chunk_max_characters', 1500)}",
        f"-var=consumer_chunk_new_after_n_chars={consumer_config.get('chunk_new_after_n_chars', 1000)}",
        f"-var=consumer_chunk_combine_under_n_chars={consumer_config.get('chunk_combine_under_n_chars', 500)}",
        f"-var=consumer_embedding_model={consumer_config.get('embedding_model', 'text-embedding-3-large')}",
        f"-var=consumer_embedding_token_threshold={consumer_config.get('embedding_token_threshold', 6000)}",
        f"-var=consumer_pinecone_index_name={consumer_config.get('pinecone_index_name', 'ras-papers')}",
        f"-var=consumer_embedding_dimension={pinecone_config.get('embedding_dimension', '3072')}",
    ], cwd=PRODUCTION_DIR, extra_env=upstash_env)

    print("\n=== Production Apply Complete ===")


def production_destroy() -> None:
    """Destroy production infrastructure."""
    print("\n=== Production Destroy ===\n")
    check_terraform()
    check_aws_cli()

    config = load_config("production")
    validate_config(config, PRODUCTION_REQUIRED_CONFIG)
    env_vars = load_env(PRODUCTION_REQUIRED_ENV)

    # Get ECR URLs from shared output
    print("\nGetting ECR repository URLs from shared...")
    result = run_command([
        "terraform", "output", "-json"
    ], cwd=SHARED_DIR, capture_output=True)
    shared_outputs = json.loads(result.stdout)
    producer_image = shared_outputs["producer_repository_url"]["value"] + ":latest"
    consumer_image = shared_outputs["consumer_repository_url"]["value"] + ":latest"

    print("\nRunning terraform destroy for production...")
    redis_config = config.get("redis", {})
    producer_config = config.get("producer", {})
    consumer_config = config.get("consumer", {})
    pinecone_config = config.get("pinecone", {})

    # Upstash provider needs these as environment variables
    upstash_env = {
        "UPSTASH_EMAIL": env_vars["UPSTASH_EMAIL"],
        "UPSTASH_API_KEY": env_vars["UPSTASH_API_KEY"],
    }

    run_command([
        "terraform", "destroy",
        "-auto-approve",
        f"-var=project_name={config['project_name']}",
        f"-var=aws_region={config['aws_region']}",
        f"-var=bucket_name={config['bootstrap']['bucket_name']}",
        f"-var=redis_primary_region={redis_config.get('redis_primary_region', 'us-east-1')}",
        f"-var=redis_tls={str(redis_config.get('redis_tls', True)).lower()}",
        f"-var=producer_image={producer_image}",
        f"-var=consumer_image={consumer_image}",
        f"-var=unstructured_api_key={env_vars['UNSTRUCTURED_API_KEY']}",
        f"-var=upstash_email={env_vars['UPSTASH_EMAIL']}",
        f"-var=upstash_api_key={env_vars['UPSTASH_API_KEY']}",
        f"-var=pinecone_api_key={env_vars['PINECONE_API_KEY']}",
        f"-var=openai_api_key={env_vars['OPENAI_API_KEY']}",
        # Producer env vars
        f"-var=producer_arxiv_category={producer_config.get('arxiv_category', 'cs.AI,cs.LG,cs.CL')}",
        f"-var=producer_max_results={producer_config.get('max_results', 10)}",
        f"-var=producer_max_pages={producer_config.get('max_pages', 20)}",
        # Consumer env vars
        f"-var=consumer_mode={consumer_config.get('mode', 'full')}",
        f"-var=consumer_chunk_max_characters={consumer_config.get('chunk_max_characters', 1500)}",
        f"-var=consumer_chunk_new_after_n_chars={consumer_config.get('chunk_new_after_n_chars', 1000)}",
        f"-var=consumer_chunk_combine_under_n_chars={consumer_config.get('chunk_combine_under_n_chars', 500)}",
        f"-var=consumer_embedding_model={consumer_config.get('embedding_model', 'text-embedding-3-large')}",
        f"-var=consumer_embedding_token_threshold={consumer_config.get('embedding_token_threshold', 6000)}",
        f"-var=consumer_pinecone_index_name={consumer_config.get('pinecone_index_name', 'ras-papers')}",
        f"-var=consumer_embedding_dimension={pinecone_config.get('embedding_dimension', '3072')}",
    ], cwd=PRODUCTION_DIR, extra_env=upstash_env)

    print("\n=== Production Destroy Complete ===")
    print("\nNote: Shared infrastructure (ECR) was not destroyed.")
    print("To destroy shared: manually run terraform destroy in terraform/envs/shared/")


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

    elif command == "staging":
        if len(sys.argv) < 3:
            print("Usage: python setup.py staging <init|apply|destroy>")
            sys.exit(1)

        subcommand = sys.argv[2]
        if subcommand == "init":
            staging_init()
        elif subcommand == "apply":
            staging_apply()
        elif subcommand == "destroy":
            staging_destroy()
        else:
            print(f"Unknown staging subcommand: {subcommand}")
            sys.exit(1)

    elif command == "production":
        if len(sys.argv) < 3:
            print("Usage: python setup.py production <init|apply|destroy>")
            sys.exit(1)

        subcommand = sys.argv[2]
        if subcommand == "init":
            production_init()
        elif subcommand == "apply":
            production_apply()
        elif subcommand == "destroy":
            production_destroy()
        else:
            print(f"Unknown production subcommand: {subcommand}")
            sys.exit(1)

    elif command in ["-h", "--help", "help"]:
        print_usage()

    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
