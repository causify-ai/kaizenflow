#!/bin/bash -e
aws ec2 describe-instance-status \
  --instance-ids $AM_INST_ID \
  --output text
