#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../device"
test_dir="$(mktemp -d /tmp/muse-app-tests.XXXXXX)"
trap 'rm -rf -- "$test_dir"' EXIT
python3 tests/test_muse_chat_link.py
"${CC:-cc}" -std=c11 -Wall -Wextra -Werror -Icomponents/passport_muse/sdk -Icomponents/passport_muse/include tests/test_muse_voice.c components/passport_muse/voice_helpers.c -o "$test_dir/voice"
"$test_dir/voice"
echo 'Muse application-only host tests: PASS'
