#!/usr/bin/env bash

LOGFILE="wf_run.log"

################################################################################
# COMMAND LINE OPTIONS

while [[ $# -gt 0 ]]; do
  case $1 in
    -e|--endpoint)
      ENDPOINT="$2"
      shift # past argument
      shift # past value
      ;;
    -k|--api-key)
      APIKEY="$2"
      shift # past argument
      shift # past value
      ;;
    -i|--input)
      INPUT="$2"
      shift # past argument
      shift # past value
      ;;
    -w|--wf-path)
      WORKFLOW="$2"
      shift # past argument
      shift # past value
      ;;
    --ssh-user)
      SSH_USER="$2"
      shift # past argument
      shift # past value
      ;;
    --ssh-key)
      SSH_KEY="$2"
      shift # past argument
      shift # past value
      ;;
    -d|--device)
      DEVICE="$2"
      shift # past argument
      shift # past value
      ;;
    -o|--output-dir)
      OUTPUT="$2"
      shift # past argument
      shift # past value
      ;;
    --iterations)
      ITERATIONS="$2"
      shift # past argument
      shift # past value
      ;;
    -*|--*)
      echo "Unknown option $1"
      exit 1
      ;;
  esac
done



################################################################################
# MAIN FUNCTION

CURRENT_PATH=$(realpath $BASH_SOURCE)
SCRIPT_PATH="${CURRENT_PATH%/*/*}"

for i in $(seq 1 $ITERATIONS)
do
    echo "Iteration $i: running wf...";
    $SCRIPT_PATH/run_workflow.py --endpoint $ENDPOINT \
    --api-key $APIKEY \
    --history-name "run$i" \
    --clean-histories \
    -i $INPUT \
    --wf-path $WORKFLOW \
    --disk-metrics \
    --ssh-user $SSH_USER \
    --ssh-key $SSH_KEY \
    --dstat-output-dir "/home/$SSH_USER/dstat_out$i" \
    --dstat-device $DEVICE \
    --metrics-output-dir $OUTPUT/metrics$i > $LOGFILE;
    echo "Iteration $i terminated";
done