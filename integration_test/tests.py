from container_test_base import Container
import docker
import unittest
import httplib
import time
import socket
import json
import tempfile
import atexit
import shutil
from logging.handlers import SysLogHandler
import logging
import os.path
import glob

# See: http://csl.sublevel3.org/post/python-syslog-client/
class Facility:
  "Syslog facilities"
  KERN, USER, MAIL, DAEMON, AUTH, SYSLOG, \
  LPR, NEWS, UUCP, CRON, AUTHPRIV, FTP = range(12)

  LOCAL0, LOCAL1, LOCAL2, LOCAL3, \
  LOCAL4, LOCAL5, LOCAL6, LOCAL7 = range(16, 24)


class Level:
  "Syslog levels"
  EMERG, ALERT, CRIT, ERR, \
  WARNING, NOTICE, INFO, DEBUG = range(8)


def send_log(host,facility,level,msg,sock=None):
    if not sock:
        sock=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s="<{l}>{msg}".format(l=level + facility*8, msg=msg)
    sock.sendto(s,(host,514))

class TestBase(unittest.TestCase):
    _dirs=None

    @classmethod
    def _cleanup(cls):
        for d in cls._dirs:
            shutil.rmtree(d,ignore_errors=True)
        cls._dirs=[]

    def __init__(self,methodName='runTest', **container_args):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if TestBase._dirs is None:
            TestBase._dirs=[]
            #atexit.register(TestBase._cleanup)
        self.log_dir=tempfile.mkdtemp(prefix="unittest_rsyslog_logs")
        TestBase._dirs.append(self.log_dir)
        super(TestBase,self).__init__(methodName=methodName)
        self.rsyslog = Container(path='..')
        self.rsyslog.set_container_args(environment={'rsyslogd_options':'-d','rsyslog_debug':'1','immediate':'1'},
                                        volumes={self.log_dir:{'bind': '/var/lib/rsyslog/logs', 'mode': 'rw'} },
                                        **container_args)

class StandardConfigTest(TestBase):

    def __init__(self,methodName='runTest'):
        super(StandardConfigTest,self).__init__(methodName=methodName) 
        
                                               
    def testSimpleMsg(self):
        send_log(self.rsyslog.ip_address,Facility.USER,Level.INFO,"thehost theapp[111]:the message is ::HERE::",
            sock=self.socket)
        time.sleep(2)
        print str(glob.glob(self.log_dir+"/by_host/*"))
        print str(glob.glob(self.log_dir+"/by_host/*/*"))
        #print self.rsyslog.container.logs(stdout=True,stderr=True)
        self.assertTrue(os.path.exists(self.log_dir+ "/by_host/localhost/syslog-rsyslogd.log"))
        logfile=self.log_dir+ "/by_host/thehost/user-theapp.log"
        self.assertTrue("::HERE::" in file(logfile).read())

if __name__ == '__main__':
    unittest.main()
