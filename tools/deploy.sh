#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<EOF
Usage:
  $0 [--dry-run] <pi-user> [pi-host] /home/<pi_user>/projects/eyes
  $0 <pi-user> [pi-host] /home/<pi_user>/projects/eyes

Options:
  -n, --dry-run   Preview changes without transferring anything
  -h, --help      Show this help
EOF
}

# Parse optional parameters. Options can appear before or after the positional
# parameters.
dry_run_args=()
positional_args=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -n|--dry-run)
      dry_run_args+=(--dry-run)
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      positional_args+=("$@")
      break
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      positional_args+=("$1")
      ;;
  esac
  shift
done

set -- "${positional_args[@]}"

if [[ $# -lt 1 || $# -gt 3 ]]; then
  usage >&2
  exit 2
fi

pi_user=$1
pi_host=${2:-eyepi.local}
remote_dir=${3:-"/home/${pi_user}/projects/eyes"}

# WSL sometimes cannot resolve .local hostnames even though Windows can.
# Ask Windows PowerShell to resolve the hostname.
if [[ ! $pi_host =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  if [[ ! $pi_host =~ ^[A-Za-z0-9.-]+$ ]]; then
    echo "Invalid hostname: $pi_host" >&2
    exit 1
  fi

  requested_host=$pi_host

  pi_host=$(
    powershell.exe -NoProfile -Command \
      "(Resolve-DnsName -Name '$requested_host' -Type A -ErrorAction Stop |
        Select-Object -First 1 -ExpandProperty IPAddress)" \
      2>/dev/null |
    tr -d '\r\n'
  )

  if [[ -z $pi_host ]]; then
    echo "Could not resolve hostname: $requested_host" >&2
    exit 1
  fi

  echo "Resolved ${requested_host} to ${pi_host}"
fi

# deploy.sh is located in tools/, so its parent is the project directory.
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
project_dir=$(cd -- "${script_dir}/.." && pwd)

if ! command -v rsync >/dev/null 2>&1; then
  echo "Error: rsync is not installed or is not on PATH." >&2
  exit 1
fi

if [[ ${#dry_run_args[@]} -gt 0 ]]; then
  echo "DRY RUN: no files will be changed."
fi

echo "Deploying ${project_dir}/"
echo "        to ${pi_user}@${pi_host}:${remote_dir}/"

# Common rsync options.
rsync_args=(
  --archive
  --verbose
  --human-readable
  --progress
  --itemize-changes
  "${dry_run_args[@]}"
)

echo
echo "Pulling requirements.txt from Pi..."

rsync \
  "${rsync_args[@]}" \
  "${pi_user}@${pi_host}:${remote_dir}/requirements.txt" \
  "${project_dir}/requirements.txt"

echo
echo "Sending project to Pi..."

rsync \
  "${rsync_args[@]}" \
  --no-perms \
  --no-owner \
  --no-group \
  --omit-dir-times \
  --exclude='.git/' \
  --exclude='.gitignore' \
  --exclude='.venv/' \
  --exclude='venv/' \
  --exclude='__pycache__/' \
  --exclude='*.py[cod]' \
  --exclude='.env' \
  --exclude='.vscode/' \
  --exclude='/tools/deploy.sh' \
  --exclude='/tools/deploy_old.sh' \
  --rsync-path="mkdir -p '${remote_dir}' && rsync" \
  "${project_dir}/" \
  "${pi_user}@${pi_host}:${remote_dir}/"

echo
if [[ ${#dry_run_args[@]} -gt 0 ]]; then
  echo "Dry run complete. No files were changed."
else
  echo "Deployment complete."
fi