# This creates problems with piping.
# Make output white.
#echo -e '\033[0;0m\c'

ACK_OPTS="--smart-case --nogroup --nocolor"

GIT_LOG_OPTS='%Creset%Cgreen%h %C(reset)%C(cyan)%<(8)%aN%Creset %Creset%C(bold white) %<(55)%s %C(bold black)(%>(14)%ar) %C(red)%ad %C(yellow)%<(10)%d%C(reset)'

execute() {
  cmd=$*
  echo "+ $cmd"
  eval $cmd
  return $?
}

execute_with_verbose() {
  cmd=$*
  if [[ $verbose == 1 ]]; then
      echo "+ $cmd"
  fi;
  eval $cmd
  return $?
}

frame() {
  echo "####################################################################"
  echo "$*"
  echo "####################################################################"
}


parse_jack_cmd_opts() {
  # Initialize variables.
  regex=""
  dir="."
  verbose=0

  #echo "Options to parse: '$@'"
  while getopts ":vhr:d:" opt; do
      #echo "Parsing opt='$opt'"
      case "$opt" in
          h)
              echo "Usage:"
              echo "  -r 'regex to look for'"
              echo "  [-d] directory to search in"
              echo "  [-v] verbose"
              exit 0
              ;;
          v)  verbose=1
              echo "verbose=$verbose"
              ;;
          r)  regex=$OPTARG
              ;;
          d)  dir=$OPTARG
              ;;
          \? )
              echo "Error: invalid option '-$OPTARG'"
              exit -1
              ;;
          :)
              echo "Error: option '-$OPTARG' requires an argument"
              exit -1
              ;;
      esac
  done
  #echo "OPTIND='$OPTIND'"
  shift $((OPTIND-1))
  #[ "${1:-}" = "--" ] && shift

  if [[ -z $regex ]]; then
      regex=$1
      shift
  fi;

  #if [[ ! -z $@ ]]; then
  #    echo "Error: too many params '$@'"
  #    exit -1
  #fi;

  if [[ $verbose == 1 ]]; then
      echo "regex='$regex'"
      echo "dir='$dir'"
  fi;
}

# ##############################################################################

get_python_version() {
  python - <<END
import sys
pyv = sys.version_info[:]
pyv_as_str = ".".join(map(str, pyv[:3]))
print("python version='%s'" % pyv_as_str)
is_too_old = pyv_as_str < "3.6"
print("is_too_old=%s" % is_too_old)
sys.exit(is_too_old);
END
  return $?
}


execute_setenv() {
  if [[ -z $1 ]]; then
    echo "ERROR($EXEC_NAME): Need to specify a parameter representing setenv"
    return 1
  fi;
  SETENV=$1
  if [[ -z $2 ]]; then
    echo "ERROR($EXEC_NAME): Need to specify the env to use"
    return 1
  fi;
  ENV_NAME=$2
  # Create the script to execute calling python.
  echo "Creating setenv script ... done"
  DATETIME=$(date "+%Y%m%d-%H%M%S")_$(python -c "import time; print(int(time.time()*1000))")
  #DATETIME=""
  SCRIPT_FILE=/tmp/$SETENV.${DATETIME}.sh
  echo "SCRIPT_FILE=$SCRIPT_FILE"
  cmd="$EXEC_PATH/$SETENV.py --output_file $SCRIPT_FILE -e $ENV_NAME"
  execute $cmd
  rc=$?
  echo "rc=$rc"
  if [[ $rc != 0 ]]; then
    frame "'$cmd' failed returning $rc"
    return $rc
  fi;
  echo "Creating setenv script '$SCRIPT_FILE' ... done"

  # Execute the newly generated script.
  echo "Sourcing '$SCRIPT_FILE' ..."
  source $SCRIPT_FILE
  echo "Sourcing '$SCRIPT_FILE' ... done"

  echo "Running '$EXEC_NAME' ... done"
}
