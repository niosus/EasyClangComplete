#!/bin/bash

set -exuo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

source "bazel.sh"

"${bazel}" --migrate build :compdb
