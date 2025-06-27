#!/usr/bin/env bash

npeople="$1"
iteration="$2"
seed=$3
scenario="$4"

output_dir="./output"

if [ ! -d "$output_dir" ]; then
  echo "Creating output directory"
  mkdir $output_dir
fi

aws s3 cp "s3://crcsim-exp-demog-specific-survival/scenarios/$scenario/params.json" "./params.json" 
aws s3 cp "s3://crcsim-exp-demog-specific-survival/scenarios/$scenario/cohort.csv" "./scenario_cohort.csv" 


crc-simulate \
    --npeople=$npeople \
    --seed=$seed \
    --params-file=./params.json \
    --cohort-file=./scenario_cohort.csv &&

crc-analyze \
    --params-file=./params.json &&

aws s3 cp ./results.csv "s3://crcsim-exp-demog-specific-survival/scenarios/$scenario/results_$iteration.csv"
aws s3 cp ./output.csv "s3://crcsim-exp-demog-specific-survival/scenarios/$scenario/output_$iteration.csv"