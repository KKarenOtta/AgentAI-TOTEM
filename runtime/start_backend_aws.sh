#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

set -a
source runtime/env_templates/backend.aws.env
set +a

bash runtime/start_all.sh
