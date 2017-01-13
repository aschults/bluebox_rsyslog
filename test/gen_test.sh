. ../lib.sh


expandOne() {
  f=$1
  shift

  o="$(forward_to=$f sh ../conf/forward.fwd | grep action))"
  for i in "$@" ; do
    if ! echo "$o" | grep "$i" >/dev/null ; then
      fail "expected config to contain '$i'. Got '$o'"
    fi
  done 
}

testForwardExpand() {
  expandOne "" "could not"
  expandOne thehost udp thehost 514

  expandOne tcp:thehost tcp thehost 10514
  expandOne tcp:thehost:999 tcp thehost 999
  expandOne udp:thehost udp thehost 514
  expandOne udp:thehost:999 udp thehost 999 
}


. ${SHUNIT_DIR:-../../shunit2-2.0.3}/src/shell/shunit2
