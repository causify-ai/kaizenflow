# #############################################################################
# Configure environment
# #############################################################################

echo "# Configure env"
echo "which gh="$(which gh)

# AWS profiles which are propagated to Docker.
export AM_AWS_PROFILE="am"
export CK_AWS_PROFILE="ck"

# These variables are propagated to Docker.
export AM_ECR_BASE_PATH="665840871993.dkr.ecr.us-east-1.amazonaws.com"
export AM_AWS_S3_BUCKET="alphamatic-data"
# TODO(Grisha): Difference between `amp`, `cmamp` and `kaizenflow`.
# Note: Do not modify during integration. Necessary for users with no access to
# AWS ECR, pulling images from DockerHub.
# TODO(Samarth): Rename sorrentum to kaizenflow once the dockerhub repo
# is changed.
export CK_ECR_BASE_PATH="sorrentum"
export CK_AWS_S3_BUCKET="cryptokaizen-data"

export DEV1="172.30.2.136"
export DEV2="172.30.2.128"

# Print the AM env vars.
printenv | egrep "AM_|AWS_" | sort

# Set up custom path to the alembic.ini file.
# See https://alembic.sqlalchemy.org/en/latest/tutorial.html#editing-the-ini-file
export ALEMBIC_CONFIG="alembic/alembic.ini"

# TODO(gp): Factor out the common code in `amp/dev_scripts/configure_env_amp.sh`
# and execute it from here. For now keep the code in sync manually.
alias i="invoke"
alias it="invoke traceback"
alias itpb="pbpaste | traceback_to_cfile.py -i - -o cfile"
alias ih="invoke --help"
alias il="invoke --list"

# Print the aliases.
alias

# Add autocomplete for `invoke`.
source $AMP/dev_scripts/invoke_completion.sh
