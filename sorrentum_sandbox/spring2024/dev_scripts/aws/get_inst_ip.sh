#!/bin/bash -e
aws ec2 describe-instances \
  --instance-ids $AM_INST_ID \
  --query "Reservations[*].Instances[*].PublicIpAddress" \
  --output=text
