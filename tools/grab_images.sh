#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<EOF
Usage:
  $0 <pi-user> [pi-host] [remote-project-directory]

Example:
  $0 vicky eyepi.local /home/vicky/projects/eyes
EOF
}

if [[ $# -lt 1 || $# -gt 3 ]]; then
  usage >&2
  exit 2
fi

pi_user=$1
pi_host=${2:-eyepi.local}
remote_dir=${3:-"/home/${pi_user}/projects/eyes"}

# Resolve .local hostnames through Windows because WSL may not resolve them.
if [[ ! $pi_host =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  if [[ ! $pi_host =~ ^[A-Za-z0-9.-]+$ ]]; then
    echo "Invalid hostname: $pi_host" >&2
    exit 1
  fi

  requested_host=$pi_host
  echo "Resolving ${requested_host}..."

  if ! pi_host=$(
    timeout 10s powershell.exe -NoProfile -Command \
      "(Resolve-DnsName -Name '$requested_host' -Type A -ErrorAction Stop |
        Select-Object -First 1 -ExpandProperty IPAddress)" \
      2>/dev/null |
    tr -d '\r\n'
  ); then
    echo "Could not resolve ${requested_host}." >&2
    exit 1
  fi

  if [[ -z $pi_host ]]; then
    echo "Could not resolve ${requested_host}." >&2
    exit 1
  fi

  echo "Resolved ${requested_host} to ${pi_host}"
fi

# This script is in tools/, and images/ is beside tools/.
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
project_dir=$(cd -- "${script_dir}/.." && pwd)
local_images_dir="${project_dir}/images"
remote_images_dir="${remote_dir}/images"

if ! command -v rsync >/dev/null 2>&1; then
  echo "Error: rsync is not installed." >&2
  exit 1
fi

mkdir -p "$local_images_dir"

echo "Pulling images:"
echo "  From: ${pi_user}@${pi_host}:${remote_images_dir}/"
echo "  To:   ${local_images_dir}/"

rsync \
  --recursive \
  --times \
  --verbose \
  --human-readable \
  --progress \
  --itemize-changes \
  "${pi_user}@${pi_host}:${remote_images_dir}/" \
  "${local_images_dir}/"

echo "Image transfer complete."