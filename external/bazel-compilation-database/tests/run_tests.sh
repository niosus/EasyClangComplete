#!/bin/bash

set -exuo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

source "bazel.sh"

"${bazel}" build :compdb

diff expected_file.json bazel-bin/compile_commands.json

diff \
  <(sed -e "s@EXECROOT@$(bazel info execution_root)@" -e "s@PWD@${PWD}@" expected_ycm_output.json) \
  <(python ../.ycm_extra_conf.py a.cc)
