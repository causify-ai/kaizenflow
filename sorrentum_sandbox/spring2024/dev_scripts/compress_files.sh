#!/bin/bash -xe

for i in *; do
  tar -czf $i.gz $i
done
