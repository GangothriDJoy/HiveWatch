#!/usr/bin/env python3

import json
import random
import sys
from pathlib import Path

# Find the main HiveWatch project folder.
PROJECT_DIR = Path(__file__).resolve().parent.parent

# Paths to the two JSON files.
HOSTNAME_FILE = PROJECT_DIR / "config" / "hostname_pool.json"
BANNER_FILE = PROJECT_DIR / "config" / "banner_pool.json"

# The output file will be created in the project folder.
ENV_FILE = PROJECT_DIR / ".env"


def load_pool(file_path):
    """Read and validate a JSON list of strings."""
    try:
        with file_path.open("r", encoding="utf-8") as file:
            values = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read {file_path}: {error}") from error

    if not isinstance(values, list) or len(values) < 5:
        raise ValueError(f"{file_path} must contain at least 5 items.")

    if not all(
        isinstance(value, str)
        and value.strip()
        and "\n" not in value
        and "\r" not in value
        for value in values
    ):
        raise ValueError(f"{file_path} must contain non-empty strings.")

    return values


def main():
    try:
        hostnames = load_pool(HOSTNAME_FILE)
        banners = load_pool(BANNER_FILE)

        # Select one random value from each list.
        hostname = random.choice(hostnames)
        banner = random.choice(banners)

        # Write the two required variables to .env.
        ENV_FILE.write_text(
            f"HP_HOSTNAME={hostname}\n"
            f"HP_BANNER={banner}\n",
            encoding="utf-8",
        )

        # Print one summary line.
        print(f"HP_HOSTNAME={hostname} HP_BANNER={banner}")

    except (ValueError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
