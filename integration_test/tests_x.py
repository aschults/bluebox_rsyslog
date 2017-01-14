import docker
import unittest
import httplib
import time
import socket
import json
import ssl
import atexit

class Container(object):
    id_counter=0
    _teardownList=[]
    _docker = None

    @classmethod
    def cleanUp(cls):
        for c in reversed(cls._teardownList):
            try:
                c.dispose_container()
            except Exception:
                print "Failure to dispose container"
            try:
                c.dispose_image()
            except Exception:
                print "Failure to dispose image"
        cls._teardownList=[]
                

    @classmethod
    def generate_id(cls):
        s="unittest_{}".format(cls.id_counter)
        cls.id_counter += 1
        return s

    @classmethod
    def set_docker(cls,d):
        cls._docker = d
        
    @classmethod
    def get_docker(cls):
        if not cls._docker:
            atexit.register(Container.cleanUp)
            cls._docker = docker.DockerClient(version='auto')
        return cls._docker 

    def __init__(self,**kwargs):
        """Init by image and container"""

        self._docker = Container.get_docker()
        self._build_args=kwargs
        self._image = None
        self._container = None
        self._container_args={}
        Container._teardownList.append(self)

    @property
    def image(self):
        if not self._image:
            imgid = Container.generate_id()
            self._build_args["stream"]=True
            self._build_args["quiet"]=False
            self._build_args["encoding"]="utf-8"
            if "tag" not in self._build_args:
                self._build_args["tag"]=imgid
            
            print "creating image {imgid} from path {pth}".format(imgid=self._build_args["tag"], pth=self._build_args['path'])
            print str(self._build_args)
            stream = self._docker.api.build(**self._build_args)
            for l in stream:
                #print json.loads(l)["stream"]
                pass

            self._image = self._docker.images.get(self._build_args["tag"])
        return self._image

    @property
    def container_args(self):
        return self._container_args

    def set_container_args(self,**kwargs):
        if kwargs == self._container_args:
            return
        self._container_args=kwargs
        self.dispose_container()

    def dispose_container(self):
        if not self._container:
            return
        print "stopping and removing container {cid}".format(cid=self._container.name)
        self._container.stop()
        self._container.remove()
        self._container=None

    def dispose_image(self):
        if not self._image:
             return
        print "removing image {}".format(self._image.tags[0])
        self._docker.images.remove(self._image.tags[0])
        self._image = None


    def _waitForServer(self,port):
        self._container.reload()
        addr=self._container.attrs[u'NetworkSettings'][u'IPAddress']
        c = httplib.HTTPConnection(addr,port)
        for i in range(30):
            time.sleep(1)
            try:
                c.connect()
            except (socket.error,httplib.HTTPException) as e:
                print "Waiting for connection on {}:{} ({})".format(addr,port,i)
                continue
            break

        c.close() 

    @property
    def container(self):
        if not self._container:
            cid = Container.generate_id()
            self._container_args["detach"]=True
            if not "name" in self._container_args:
                self._container_args["name"]=cid

            tag=self.image.tags[0]
            print "starting container {cid} built from path {pth}".format(cid=self._container_args["name"],pth=self._build_args["path"])
            print str(self._container_args)
            self._container = self._docker.containers.run(tag, **self._container_args) 

            for port in self._container_args["ports"]:
                self._waitForServer(port)

        return self._container

    @property
    def ip_address(self):
        return self.container.attrs[u'NetworkSettings'][u'IPAddress']
    

class TestBase(unittest.TestCase):

    def __init__(self,methodName='runTest', **container_args):
        super(TestBase,self).__init__(methodName=methodName)
        self.squid = Container(path='..')
        self.squid.set_container_args(volumes={},
                                      **container_args)

    @property
    def webserver_c(self):
        if not TestBase._webserver:
            TestBase._webserver = Container(path='containers/squid_webtest', quiet=False, tag='squid_webtest')
            TestBase._webserver.set_container_args(name='squid-webtest', ports={80:9080, 443:9443})

        return TestBase._webserver

    @property
    def server_cert(self):
      c = httplib.HTTPConnection(self.webserver_c.ip_address)
      c.request("GET","/server.crt")
      r = c.getresponse()
      if r.status != 200:
          raise Exception("Failed to get Certificate")

      content= r.read()
      c.close()
      return content

    @classmethod
    def tearDownClass(cls):
        #Container.cleanUp()
        pass

    def proxyFetch(self,url):
        c = httplib.HTTPConnection(self.squid.ip_address,3128)
        #c.set_tunnel("squid-webtest",80)
        c.request("GET",url)
        return c.getresponse()
      
    def proxyConnect(self,host,port,path,cadata=None):
        if not cadata:
            cadata = self.server_cert
        dercert = ssl.PEM_cert_to_DER_cert(cadata)
        c = httplib.HTTPSConnection(self.squid.ip_address,3128,context=ssl.create_default_context(cadata=dercert))
        c.set_tunnel(host,port)
        #c.putheader('Host',"squid-webtest")
        c.request("GET",path)
        return c.getresponse()

class StandardConfigTest(TestBase):

    def __init__(self,methodName='runTest'):
        super(StandardConfigTest,self).__init__(methodName=methodName, ports={3128:None}) 
                                               
    def testGet(self):
      self.assertEqual(200, self.proxyFetch("http://squid-webtest/").status)
      self.assertEqual(200, self.proxyFetch("https://squid-webtest/").status)
      self.assertEqual(403, self.proxyFetch("http://squid-webtest:22/").status)
          
    def testConnect(self):
      self.assertEqual(200, self.proxyConnect("squid-webtest",443,"/").status)
      self.assertRaisesRegexp(socket.error,"403",self.proxyConnect,"squid-webtest",80,"/")


class BumpConfigTest(TestBase):

    def __init__(self,methodName='runTest'):
        super(BumpConfigTest,self).__init__(methodName=methodName, ports={3128:None},
            environment={
                'sslbump':'1'
            }) 

    @property
    def squid_cert(self):
        c = httplib.HTTPConnection(self.squid.ip_address,3128)
        c.request("GET","http://squidproxy:80/bump.crt")
        r = c.getresponse()
        if r.status != 200:
            raise Exception("Failed to get Certificate: {} {}".format(r.status,r.msg))

        content= r.read()
        c.close()
        return content 


    def testConnect(self):
      self.assertEqual(200, self.proxyConnect("squid-webtest",443,"/",self.squid_cert).status)
      self.assertRaisesRegexp(socket.error,"403",self.proxyConnect,"squid-webtest",80,"/", self.squid_cert)


if __name__ == '__main__':
    unittest.main()
    #t=TestBase._'testGet')
    #t.setUp()

"""
  pwfile=/tmp/squidtest.passwd
  if [ -f $pwfile ] ; then
    rm $pwfile
  fi
  htpasswd -bc $pwfile bla bla

  docker run -e proxy_auth="$(cat $pwfile)" -e secondary_port=1 -e disk_cache_size=200 -e sslbump=1 --name=squidtest-c -v /var/tmp/squiddisk2:/var/spool/squid/cache -v /var/tmp/squidssl:/var/spool/squid/ssl -p 3333:3128 -p 4444:3127 --link squid-webtest:squid-webtest -d squidtest_i
"""
