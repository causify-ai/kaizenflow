#!/bin/bash -xe

# Check for leaks.
gitleaks detect --verbose 2>&1 | tee gitleaks.before.txt

\jack "Fingerprint" gitleaks.before.txt | \grep -v ipynb | tee cfile

# Check the output.
# \jack "Fingerprint" log.txt | \grep -v ipynb | perl -p -e 's/^.*Fingerprint: \S{40}:(.*):.*:(.*)/vim $1 +$2/' | tee cfile
# source cfile

find . -name "*.ipynb" | xargs -n 1 -t jupyter nbconvert --to=notebook --inplace --ClearOutputPreprocessor.enabled=True --ClearMetadataPreprocessor.enabled=True 

# Check for leaks.
gitleaks detect --verbose 2>&1 | tee gitleaks.after.txt
