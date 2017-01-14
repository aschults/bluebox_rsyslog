import docker
import unittest
import httplib
import time
import socket
import atexit
import json

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
                print json.loads(l)["stream"]
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

            if "ports" in self._container_args:
                for port in self._container_args["ports"]:
                    self._waitForServer(port)
            else:
                time.sleep(2)

            self._container.reload()
            if self._container.status == 'exited':
                raise Exception("container {} exited unexpectedly".format(self.container.name))
        return self._container

    @property
    def ip_address(self):
        return self.container.attrs[u'NetworkSettings'][u'IPAddress']
    
