#!/usr/bin/env bash

set -Eeuo pipefail
trap cleanup SIGINT SIGTERM ERR EXIT

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd -P)

usage() {
  cat <<EOF
Usage: $(basename "${BASH_SOURCE[0]}") [-h] [-v] [-f] -p param_value arg1 [arg2...]

Script description here.

Available options:

-h, --help      Print this help and exit
-v, --verbose   Print script debug info
-f, --flag      Some flag description
-p, --param     Some param description
EOF
  exit
}

cleanup() {
  trap - SIGINT SIGTERM ERR EXIT
  # script cleanup here
}

setup_colors() {
  if [[ -t 2 ]] && [[ -z "${NO_COLOR-}" ]] && [[ "${TERM-}" != "dumb" ]]; then
    NOFORMAT='\033[0m' RED='\033[0;31m' GREEN='\033[0;32m' ORANGE='\033[0;33m' BLUE='\033[0;34m' PURPLE='\033[0;35m' CYAN='\033[0;36m' YELLOW='\033[1;33m'
  else
    NOFORMAT='' RED='' GREEN='' ORANGE='' BLUE='' PURPLE='' CYAN='' YELLOW=''
  fi
}

msg() {
  echo >&2 -e "${1-}"
}

die() {
  local msg=$1
  local code=${2-1} # default exit status 1
  msg "$msg"
  exit "$code"
}

parse_params() {
  # default values of variables set from params
  flag=0
  param=''

  while :; do
    case "${1-}" in
    -h | --help) usage ;;
    -v | --verbose) set -x ;;
    --no-color) NO_COLOR=1 ;;
    -f | --flag) flag=1 ;; # example flag
    -p | --param) # example named parameter
      param="${2-}"
      shift
      ;;
    -?*) die "Unknown option: $1" ;;
    *) break ;;
    esac
    shift
  done

  args=("$@")

  # check required params and arguments
  #[[ -z "${param-}" ]] && die "Missing required parameter: param"
  #[[ ${#args[@]} -eq 0 ]] && die "Missing script arguments"

  return 0
}

parse_params "$@"
setup_colors

###################

SYSTEMD_DIR="/lib/systemd/system"
SYSTEMD_CONFIG="systemd/pimqtt.service"

###################

# First, some system checks

if [ "$EUID" -ne 0 ]
then
  die "${RED}Error: Please run as root${NOFORMAT}"
else
  msg "Running as root: ${GREEN}CHECK${NOFORMAT}"
fi

if [ ! -d $SYSTEMD_DIR ] 
then
  die "${RED}Directory $SYSTEMD_DIR DOES NOT exist, is this a systemd-compatible OS?${NOFORMAT}." 
else
  msg "Systemd: ${GREEN}CHECK${NOFORMAT}"
fi

if ! [ -x "$(command -v pip3)" ]; then
  die "Error: pip3 is not installed."
else
  msg "Pip3: ${GREEN}CHECK${NOFORMAT}"
fi


# now do the install

cp $SYSTEMD_CONFIG $SYSTEMD_DIR
msg "Systemd config file copied: ${GREEN}CHECK${NOFORMAT}"

systemctl daemon-reload
msg "Systemd reloaded: ${GREEN}CHECK${NOFORMAT}"

systemctl enable pimqtt.service
msg "Systemd pimqtt enabled: ${GREEN}CHECK${NOFORMAT}"

systemctl restart pimqtt.service
msg "Systemd pimqtt restarted: ${GREEN}CHECK${NOFORMAT}"

# TODO:
# install cron.d
# install config file if not present
# pip3 install whatever is needed, global install (ugly but it works)
#   paho picamera


msg "${GREEN}Install Complete${NOFORMAT}"


#msg "${RED}Read parameters:${NOFORMAT}"
#msg "- flag: ${flag}"
#msg "- param: ${param}"
#msg "- arguments: ${args[*]-}"

