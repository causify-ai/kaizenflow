perl -e 'print join(":", grep { not $seen{$_}++ } split(/:/, scalar <>))'
