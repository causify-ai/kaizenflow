#perl -e 'print join("\n", grep { not $seen{$_}++ } split(/:/, scalar <>))' | sort | uniq
# We want to print the paths in the order to show which one will be picked first.
perl -e 'print join("\n", split(/:/, scalar <>))' | sort
