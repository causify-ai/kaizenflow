# Set up the env vars in both clients.
export AMP_DIR=/Users/saggese/src/amp1
echo "# $AMP_DIR"
ls $AMP_DIR

export CMAMP_DIR=/Users/saggese/src/cmamp1
echo "# $CMAMP_DIR"
ls $CMAMP_DIR

# Create branches
DATE=20211210
export BRANCH_NAME=AmpTask1786_Integrate_${DATE}
i git_branch_create -b $BRANCH_NAME
