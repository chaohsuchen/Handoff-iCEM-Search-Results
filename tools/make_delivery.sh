#!/usr/bin/env bash
# Pack the hand-off for Fred (when a tar is wanted instead of the GitHub repo): results_search/ without videos and .pkl files, plus docs/, the tools and both engines (rcx/, carla_rc/).
# usage (from robotproject/):  tools/make_delivery.sh [OUT.tar.gz]
set -euo pipefail
out=${1:-/w/20261/$USER/robotproject_delivery_$(date +%Y%m%d).tar.gz}
python3 tools/delivery_status.py > /dev/null
python3 tools/index_runs.py > /dev/null
tar --exclude='*.mp4' --exclude='*.pkl' --exclude='*/__pycache__' --exclude='results_search/logs' \
    -czf "$out" results_search docs tools rcx carla_rc search rc01 slurm/verify_idle.sbatch slurm/kent_run.sbatch slurm/carla_server.sh README.md docs/report.md docs/scenes/20RCs.md
echo "$out  $(du -h "$out" | cut -f1)"
tar -tzf "$out" | wc -l
