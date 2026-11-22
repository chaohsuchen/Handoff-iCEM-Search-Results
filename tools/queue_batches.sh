#!/usr/bin/env bash
# Queue CARLA batches on the idle GPU nodes, two shards in parallel (one per node), each node's jobs chained so they never overlap.
# usage (from robotproject/):  tools/queue_batches.sh NODE0 NODE1 FIRST_DEP0 FIRST_DEP1 case:batch [case:batch ...]
# FIRST_DEP* = a job id to wait for on that node (or "none").
set -euo pipefail
n0=$1; n1=$2; d0=$3; d1=$4; shift 4
for cb in "$@"; do
  case=${cb%%:*}; batch=${cb##*:}
  for s in 0 1; do
    node=$n0; dep=$d0; [ $s = 1 ] && { node=$n1; dep=$d1; }
    opt=(); [ "$dep" != none ] && opt=(--dependency=afterany:$dep)
    id=$(CASE=$case BATCH=$batch SHARD=$s NSHARDS=2 sbatch --parsable --nodelist=$node "${opt[@]}" --export=ALL --job-name=v_${case}_${batch}_$s slurm/verify_idle.sbatch)
    echo "$case/$batch shard $s -> job $id on $node"
    if [ $s = 0 ]; then d0=$id; else d1=$id; fi
  done
done
