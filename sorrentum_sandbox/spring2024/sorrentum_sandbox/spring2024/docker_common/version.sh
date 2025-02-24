#!/bin/bash
echo "# Python3"
python3 --version
echo "# pip3"
pip3 --version
echo "# jupyter"
jupyter --version
echo "# Python packages"
pip3 list
echo "# mongo"
mongod --version || true
