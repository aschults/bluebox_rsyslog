# Utility functions

# Command based generation or filtering for config files
# Usage: expand_conf /dir/to/originals /dir/for/generated/config

handle_failed_file() {
 if [ -n "${FAILED_FILE_CONTENT:-}" ] ; then
    echo "Replacing $2 with '$FAILED_FILE_CONTENT'" >&2
    echo "$FAILED_FILE_CONTENT" >"$2"
 fi
}

debug_msg() {
  if [ -n "${DEBUG_LIB:-}" ] ; then
    echo "DEBUG:" "$@" >&2
  fi
}

error_msg() {
  echo "ERROR:" "$@" >&2
  exit 1
}

expand_conf() {
  (
    set +e
  local confdir="$1"
  local conf_gen="$2"
  local comment_str="${COMMENT_STR:-#}"
  handle_failed_file="${FAILED_FILE_HANDLER:-handle_failed_file}"
  
  if [ -d "$confdir" ] ; then
        ls -1 "$confdir" | while read f ; do
                local fn="$confdir/$f"
                local bang
		read bang < "$fn"
                local fn2="`basename "$fn"`"
                export SRC_FILE="$fn"
                export DST_FILE="$conf_gen/$fn2"
                export FILENAME="$fn2"

                debug_msg bang: "$bang"
		case "$bang" in
		  \#\!*|${comment_str}\!*)
			 local cmd="${bang#${comment_str}\!}"
                         debug_msg about to eval "$cmd '$fn'"
			 eval "$cmd '$fn'" >"$conf_gen/$fn2"
                         rv=$?
                         if [ $rv -gt 0 ] ; then
                           echo "failed to exec <$cmd>: $rv" >&2
                           eval "$handle_failed_file" "$fn" "$conf_gen/$fn2" $rv "$cmd" 
                           rv2=$?
                           if [ $rv2 -gt 0 ] ; then
                             exit $rv2
                           fi
                         fi
			 ;;
		  ${comment_str}\|*)
			 local cmd="${bang#${comment_str}\|}"
                         debug_msg about to eval "cat '$fn' |$cmd"
			 eval "cat '$fn' |$cmd" >"$conf_gen/$fn2"
                         rv=$?
                         if [ $rv -gt 0 ] ; then
                           echo "failed to pipe $fn into exec <$cmd>: $rv" >&2
                           eval "$handle_failed_file" "$fn" "$conf_gen/$fn2" $rv "$cmd" 
                           rv2=$?
                           if [ $rv2 -gt 0 ] ; then
                             exit $rv2
                           fi
                         fi
			 ;;
		  *)
                         debug_msg simply copying "$fn" "$conf_gen/$fn2"
			 cp "$fn" "$conf_gen/$fn2"
                         rv=$?
                         if [ $rv -gt 0 ] ; then
                           echo "failed to copy file $fn to $conf_gen/$fn2: $rv" >&2
                           eval "$handle_failed_file" "$fn" "$conf_gen/$fn2" $rv "cp" 
                           rv2=$?
                           if [ $rv2 -gt 0 ] ; then
                             exit $rv2
                           fi
                         fi
			 ;;
		esac
	done
        rv=$?
        if [ $rv -gt 0 ] ; then
          exit $rv
        fi
        export SRC_FILE=
        export DST_FILE=
        export FILENAME=
  fi
  )
  return $?
}

collect_files() {
  local expr=$1
  shift
  for dir in "$@" ; do
    ls -1 "$dir" | while read f ; do
      local fn="$dir/$f"
      eval "echo -en \"${expr//\"/\\\"}\""
    done
  done
}
