#!/bin/bash
set -e

# Default build command
cmd="colcon build --build-base cache/build --install-base cache/install --log-base cache/log --symlink-install"

# Pass any additional arguments to colcon
if [ $# -gt 0 ]; then
    cmd="$cmd $@"
fi

echo "Running: $cmd"
eval $cmd
