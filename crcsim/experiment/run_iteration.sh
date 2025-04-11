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

aws s3 cp "s3://exp-relative-overall-survival-comparison/scenarios/$scenario/params.json" "./params.json" 

crc-simulate \
    --npeople=$npeople \
    --seed=$seed \
    --params-file=./params.json \
    --cohort-file=./cohort.csv &&

crc-analyze \
    --params-file=./params.json &&

# Create the S3 directory structure if you need to upload results
aws s3 cp ./results.csv "s3://exp-relative-overall-survival-comparison/scenarios/$scenario/results_$iteration.csv"
