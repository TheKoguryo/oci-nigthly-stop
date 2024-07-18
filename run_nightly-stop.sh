#!/bin/bash

export APPDIR=$HOME/oci-nigthly-stop

cd $APPDIR

###########################################################
# Main
###########################################################
echo "Start running at `date`..."
echo
start_time=$(date +%s)

python3 $APPDIR/nightly-stop.py

echo
echo "Completed at `date`.."
end_time=$(date +%s)

elapsed_seconds=$((end_time - start_time))

hours=$((elapsed_seconds / 3600))
minutes=$(( (elapsed_seconds % 3600) / 60 ))
seconds=$((elapsed_seconds % 60))

echo "Elapsed time: $hours hours, $minutes minutes, $seconds seconds"
