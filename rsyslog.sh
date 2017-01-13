set -e
. lib.sh

vardir=$rootdir/var/lib/rsyslog
confdir=$rootdir/etc/rsyslog.d
conf_gen=$vardir/conf_generated
export vardir confdir etcdir

for f in `ls $rootdir/etc/rsyslog_start.d`  ; do
  fn=$rootdir/etc/rsyslog_start.d/$f
  if [ -x $fn ] ; then
     eval $fn
  else
     sh $fn
  fi 
done

if ! [ -d $conf_gen ] ; then
  rm -rf $conf_gen
fi
mkdir -p $conf_gen

expand_conf $confdir $conf_gen

conf=/etc/rsyslog.conf
if [ -n "$forward_to" ] ; then
  conf=/etc/rsyslog_fwd.conf
fi

rsyslogd -n -f $conf

