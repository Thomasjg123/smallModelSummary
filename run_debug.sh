#!/bin/bash
# Simple wrapper to run debug_cli.py non-interactively

# Create a temporary copy with wait_for_enter modified
cp debug_cli.py debug_cli_temp.py

# Replace the wait_for_enter function to be non-interactive
sed -i '73,79c\    def wait_for_enter(prompt: str = "Press ENTER to continue (q to quit, s to skip to end): "):\n        return "continue"' debug_cli_temp.py

# Run it
timeout 180 yes '' | python debug_cli_temp.py "$1" "$2" 2>&1

# Clean up
rm debug_cli_temp.py
