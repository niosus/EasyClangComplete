os="$(uname -s | tr "[:upper:]" "[:lower:]")"
readonly os

# Use bazelisk to catch migration problems.
# Value of BAZELISK_GITHUB_TOKEN is set as a secret on Travis.
readonly url="https://github.com/bazelbuild/bazelisk/releases/download/v1.0/bazelisk-${os}-amd64"
readonly bin_dir="${TMPDIR:-/tmp}/bin"
readonly bazel="${bin_dir}/bazel"

mkdir -p "${bin_dir}"
export PATH="${bin_dir}:${PATH}"
curl -L -sSf -o "${bazel}" "${url}"
chmod a+x "${bazel}"


