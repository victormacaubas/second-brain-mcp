#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_NAME="second-brain-mcp"

usage() {
  cat <<EOF
Usage: ./install.sh <vault-path> [--project|--global|--desktop]

Register the $SERVER_NAME MCP server with a Claude client.

Arguments:
  vault-path    Absolute path to your Obsidian vault (required)

Options:
  --project     Register in Claude Code for the current project (default)
  --global      Register in Claude Code for all sessions
  --desktop     Register in Claude Desktop

Prerequisites:
  - uv (https://docs.astral.sh/uv/)
  - claude CLI (for --project and --global only)

Examples:
  ./install.sh ~/Documents/my-vault
  ./install.sh ~/Documents/my-vault --global
  ./install.sh ~/Documents/my-vault --desktop
EOF
  exit 1
}

die() { echo "Error: $*" >&2; exit 1; }

get_desktop_config() {
  case "$(uname -s)" in
    Darwin)
      echo "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
      ;;
    Linux)
      echo "${XDG_CONFIG_HOME:-$HOME/.config}/Claude/claude_desktop_config.json"
      ;;
    MINGW*|MSYS*|CYGWIN*)
      if [[ -n "${APPDATA:-}" ]]; then
        echo "$APPDATA/Claude/claude_desktop_config.json"
      else
        die "Cannot determine Claude Desktop config path. Set APPDATA environment variable."
      fi
      ;;
    *)
      die "Unsupported OS: $(uname -s). Supported: macOS, Linux, Windows (Git Bash/WSL)."
      ;;
  esac
}

validate() {
  if [[ -z "$VAULT_PATH" ]]; then
    die "Vault path is required. Run ./install.sh --help for usage."
  fi

  local resolved_vault
  resolved_vault="$(cd "$VAULT_PATH" 2>/dev/null && pwd)" || die "Vault path '$VAULT_PATH' does not exist or is not a directory."
  VAULT_PATH="$resolved_vault"

  if ! command -v uv &>/dev/null; then
    die "uv is not installed. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
  fi

  if [[ "$SCOPE" != "desktop" ]]; then
    if ! command -v claude &>/dev/null; then
      die "claude CLI not found in PATH. Install Claude Code from https://claude.ai/download or use --desktop instead."
    fi
  fi
}

install_claude_code() {
  local scope_flag="$1"
  local uv_path
  uv_path="$(command -v uv)"

  echo "Adding $SERVER_NAME to Claude Code (scope: $scope_flag)..."

  claude mcp add "$SERVER_NAME" \
    --scope "$scope_flag" \
    --transport stdio \
    -e "VAULT_PATH=$VAULT_PATH" \
    -- "$uv_path" run --directory "$SCRIPT_DIR" "$SERVER_NAME"

  echo ""
  echo "Done. Verify with: claude mcp list"
}

install_desktop() {
  local uv_path
  uv_path="$(command -v uv)"
  local config_file
  config_file="$(get_desktop_config)"

  echo "Writing $SERVER_NAME to Claude Desktop config..."
  echo "  Config: $config_file"

  mkdir -p "$(dirname "$config_file")"

  python3 - <<PYTHON
import json, os, sys

config_file = """$config_file"""
vault_path  = """$VAULT_PATH"""
uv_path     = """$uv_path"""
project_dir = """$SCRIPT_DIR"""
server_name = "$SERVER_NAME"

entry = {
    "command": uv_path,
    "args": ["run", "--directory", project_dir, server_name],
    "env": {"VAULT_PATH": vault_path},
}

if os.path.exists(config_file):
    with open(config_file) as f:
        config = json.load(f)
else:
    config = {}

config.setdefault("mcpServers", {})[server_name] = entry

with open(config_file, "w") as f:
    json.dump(config, f, indent=2)
    f.write("\n")
PYTHON

  echo ""
  echo "Done. Quit and reopen Claude Desktop to activate the server."
}

# --- Argument parsing ---

VAULT_PATH=""
SCOPE="project"

if [[ $# -eq 0 ]]; then
  usage
fi

case "$1" in
  -h|--help) usage ;;
  -*) die "First argument must be the vault path. Run ./install.sh --help for usage." ;;
  *) VAULT_PATH="$1" ;;
esac
shift

case "${1:-}" in
  --project) SCOPE="project" ;;
  --global)  SCOPE="global" ;;
  --desktop) SCOPE="desktop" ;;
  "")        ;;
  *) die "Unknown option: $1. Valid options: --project, --global, --desktop" ;;
esac

# --- Main ---

validate

case "$SCOPE" in
  project) install_claude_code "project" ;;
  global)  install_claude_code "user" ;;
  desktop) install_desktop ;;
esac
