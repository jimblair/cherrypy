"""Tests for managing HTTP issues (malformed requests, etc).

Some of these tests check timeouts, etcetera, and therefore take a long
time to run. Therefore, this module should probably not be included in
the 'comprehensive' test suite (test.py).
"""

from cherrypy.test import test
test.prefer_parent_path()

import gc
import httplib
import threading
import cherrypy
from cherrypy import _cprequest


data = object()

def get_instances(cls):
    return [x for x in gc.get_objects() if isinstance(x, cls)]

def setup_server():
    
    class Root:
        def index(self, *args, **kwargs):
            cherrypy.request.thing = data
            return "Hello world!"
        index.exposed = True
        
        def gc_stats(self):
            return "%s %s %s %s" % (gc.collect(),
                                    len(get_instances(_cprequest.Request)),
                                    len(get_instances(_cprequest.Response)),
                                    len(gc.get_referrers(data)))
        gc_stats.exposed = True
        
        def gc_objtypes(self):
            data = {}
            for x in gc.get_objects():
                data[type(x)] = data.get(type(x), 0) + 1
            
            data = [(v, k) for k, v in data.iteritems()]
            data.sort()
            return "\n".join([repr(pair) for pair in data])
        gc_objtypes.exposed = True
    
    cherrypy.tree.mount(Root())
    cherrypy.config.update({'environment': 'test_suite'})


from cherrypy.test import helper

class HTTPTests(helper.CPWebCase):
    
    def test_sockets(self):
        # By not including a Content-Length header, cgi.FieldStorage
        # will hang. Verify that CP times out the socket and responds
        # with 411 Length Required.
        c = httplib.HTTPConnection("localhost:%s" % self.PORT)
        c.request("POST", "/")
        self.assertEqual(c.getresponse().status, 411)


class ReferenceTests(helper.CPWebCase):
    
    def test_threadlocal_garbage(self):
        def getpage():
            self.getPage('/')
            self.assertBody("Hello world!")
        
        ts = []
        for _ in range(25):
            t = threading.Thread(target=getpage)
            ts.append(t)
            t.start()
        
        for t in ts:
            t.join()
        
        self.getPage("/gc_stats")
        self.assertBody("0 1 1 1")
        
        # If gc_stats fails, choose "ignore" to see the type counts for
        # all the unreachable objects in this body.
        self.getPage("/gc_objtypes")
        self.assertBody("")


if __name__ == '__main__':
    setup_server()
    helper.testmain()
