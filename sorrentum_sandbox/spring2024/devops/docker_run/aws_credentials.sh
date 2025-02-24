#!/usr/bin/env bash
#
# If ~/.aws exists loads the AWS credentials into the corresponding environment
# variables.
#

# TODO(gp): This file seems useless. If so, delete.

set -e

FILE_NAME="devops/docker_build/entrypoint/aws_credentials.sh"
echo "##> $FILE_NAME"

echo "HOME=$HOME"
AWS_VOLUME="${HOME}/.aws"
if [[ ! -d $AWS_VOLUME ]]; then
    echo "Can't find $AWS_VOLUME: exiting"
else
    INI_FILE=$AWS_VOLUME/credentials
    while IFS=' = ' read key value
    do
        if [[ $key == \[*] ]]; then
            section=$key
        elif [[ $value ]] && [[ $section == '[default]' ]]; then
            if [[ $key == 'aws_access_key_id' ]]; then
                echo "Assigning AM_AWS_ACCESS_KEY_ID='$value'"
                export AM_AWS_ACCESS_KEY_ID=$value
            elif [[ $key == 'aws_secret_access_key' ]]; then
                echo "Assigning AM_AWS_SECRET_ACCESS_KEY='***'"
                export AM_AWS_SECRET_ACCESS_KEY=$value
            fi
        fi
    done < $INI_FILE
    # Update the password file.
    # TODO(gp): Change default00 -> alphamatic-data.
    #echo $AM_AWS_ACCESS_KEY_ID:$AM_AWS_SECRET_ACCESS_KEY > /etc/passwd-s3fs-default00-bucket
    #chmod 600 /etc/passwd-s3fs-default00-bucket
fi;

# TODO(gp): Load also the AM_AWS_DEFAULT_REGION from ~/.aws/config.
export AM_AWS_DEFAULT_REGION="us-east-1"
echo "Assigning AM_AWS_DEFAULT_REGION='$AM_AWS_DEFAULT_REGION'"
