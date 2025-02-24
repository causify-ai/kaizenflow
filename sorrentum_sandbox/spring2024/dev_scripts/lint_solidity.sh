#!/usr/bin/env bash
# Solidity formatter and linter using prettier and EthLint.
#
# Usage: 
# ./lint_solidity.sh file1.sol file2.sol ....

set -eux

# Create a temporary file to build the Docker container.
TMP_FILENAME="/tmp/tmp.lint_solidity.Dockerfile"
cat >$TMP_FILENAME <<EOF
FROM ubuntu:latest

RUN apt-get update && \
    apt-get -y upgrade

RUN apt-get install -y curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Node.js.
RUN curl -sL https://deb.nodesource.com/setup_18.x | bash -
RUN apt-get update && apt-get install -y nodejs
RUN node -v
RUN npm -v

# Install Prettier and Ethlint/Solium.
RUN npm install -g prettier && \
    npm install -g prettier-plugin-solidity && \
    npm install -g solium

RUN npx prettier -v && \
    solium -V

EOF

docker build -f $TMP_FILENAME -t ubuntulint .

USER="$(id -u $(logname)):$(id -g $(logname))"
WORKDIR="$(realpath .)"
MOUNT="type=bind,source=${WORKDIR},target=${WORKDIR}"

# Since Ethlint doesn't support multiple file inputs but only directories,
# we copy all the files supplied to the command line to a temporary directory and
# use it as input to Ethlint.
TMP_DIR_NAME="./tmp.lint_solidity"
mkdir $TMP_DIR_NAME
# Loop through each file name passed as an argument.
for file in "$@"; do
    # Check if the file exists.
    if [ -e "$file" ]; then
        # Copy the file to the new directory.
        cp "$file" "$TMP_DIR_NAME"
    else
        # If the file doesn't exist, print an error message.
        echo "Error: $file does not exist"
    fi
done

# Append code to initialize the linters.
cat >./run_linter.sh <<EOF

solium --init

npx prettier --write $@
solium -d $TMP_DIR_NAME/

rm .soliumrc.json .soliumignore

EOF

# Execute the custom script using Docker.
chmod +x ./run_linter.sh


CMD="bash -c ./run_linter.sh $@"

docker run --rm -it --workdir "${WORKDIR}" --mount "${MOUNT}" ubuntulint:latest $CMD

# Clean up temporary files.
rm run_linter.sh
rm -r $TMP_DIR_NAME
rm $TMP_FILENAME
