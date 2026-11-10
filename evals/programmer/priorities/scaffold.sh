#!/usr/bin/env bash
# Copies the case's fixture into the run's workspace, which is the working directory.
set -euo pipefail
cp -R -- "${0%/*}/fixture/." .
