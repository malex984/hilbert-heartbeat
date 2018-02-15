#! /usr/bin/env python3

# import sched, time
from time import time
from time import sleep
from random import randint
from threading import Timer

import os  # environment vars
import sys # sys.version_info


if sys.version_info[0] == 3:
    from urllib.request import urlopen
    # import urllib.request, urllib.parse, urllib.error  # what? why?
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from urllib.parse import urlparse
    from urllib.parse import unquote
elif sys.version_info[0] == 2:
    from urllib2 import urlopen
    from urlparse import urlparse, unquote
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
#    import urllib  # what? why?


# https://docs.python.org/2/library/sched.html
#### SH = sched.scheduler(time, sleep)

PORT_NUMBER = int(os.getenv('HB_PORT', 8888))
HOST_NAME = os.getenv('HB_HOST', '127.0.0.1')
HB_SERVER_URL = os.getenv('HB_URL', "http://" + HOST_NAME + ":" + str(PORT_NUMBER))

# For the HB test client:
APP_ID = os.getenv('APP_ID', 'heartbeat')

# localhost:8888/hb_init?48&appid=test_client_python =>
#         /hb_init
#         [*] 
#         ['48', 'appid=test_client_python']
#         Accept-Encoding: identity
#         Host: localhost:8080
#         Connection: close
#         User-Agent: Python-urllib/2.7
#         
#         ID: Python-urllib/2.7@127.0.0.1

visits = {}

# overdue = 0 # Just for now... TODO: FIXME?: should be a part of visit data, right?!

# TODO: add logging, fix for Python2 and Python3? Better Timer handling!

def toolate(ID):
    ts = time()
    print("[", ts, "] [", ID, "]: ", visits[ID])

    d = visits[ID]
    # Collect statistics about ID    

    if d[3] > 6:
        print("TOO overdue - dropping!!!")  # TODO: early detection of overdue clients!!???
        del visits[ID]
    else:
        visits[ID] = (d[0], d[1], Timer(d[1], toolate, [ID]), d[3] + 1)
        visits[ID][2].start()  # Another Chance???


class MyHandler(BaseHTTPRequestHandler):
    #        s.headers, s.client_address, s.command, s.path, s.request_version, s.raw_requestline
    def status(s, ID):
        d = visits[ID]

        t = d[0]
        dd = d[1]
        od = d[3]

        app = "application [" + str(ID) + "]| od=" + str(od) + ";1;3;0;10 delay=" + str(dd) + ";;; "

        ## STATUS CODE???
        if od == 0:
            s.wfile.write(bytes("OK - fine " + app, 'UTF-8'))
        elif od > 2:
            s.wfile.write(bytes("WARNING - somewhat late " + app, 'UTF-8'))
        elif od > 4:
            s.wfile.write(bytes("CRITICAL - somewhat late " + app, 'UTF-8'))

    def do_GET(s):
        global visits
        #        global overdue

        s.send_response(200)
        s.send_header('Content-type', 'text/html')
        s.send_header('Access-Control-Allow-Origin', '*')
        s.end_headers()

        ### TODO: FIXME: the following url parsing is neither failsafe nor secure! :-(
        path, _, tail = s.path.partition('?')
        path = unquote(path)

        if path == "/list":
            for k, v in visits.items():
                s.wfile.write(bytes(str(k) + "\n", 'UTF-8'))
            return

        query = tail.split('&')

        if path == "/status":
            if tail != "":
                ID = query[0].split('=')[1]  # + " @ " + s.client_address[0] # " || " + s.headers['User-Agent']
                if ID in visits:
                    s.status(ID)
                else:
                    s.wfile.write(bytes("CRITICAL - no application record for " + str(ID), 'UTF-8'))
            else:
                if len(visits) == 1:
                    ID = next(iter(visits.keys()))
                    s.status(ID)
                elif len(visits) > 1:
                    s.wfile.write(bytes("WARNING - multiple (" + str(len(visits)) + ") applications", 'UTF-8'))
                else:
                    s.wfile.write(bytes("UNKNOWN -  no heartbeat clients yet...", 'UTF-8'))

            return

        # PARSING: s.path -->>> path ? T & appid = ID        
        T = int(query[0])
        ID = query[1].split('=')[1] + " @ " + s.client_address[0]  # " || " + s.headers['User-Agent']

        if ID in visits:
            print("PREVIOUS STATE", visits[ID])
            visits[ID][2].cancel()  # !

        ts = time()

        if (((path == "/hb_init") or (path == "/hb_ping")) and (ID not in visits)):
            # Hello little brother! Big Brother is watching you!
            print("Creation from scratch : ", ID, " at ", ts)
            T = T + 1  # max(10, (T*17)/16)
            visits[ID] = (ts, T, Timer(T, toolate, [ID]), 0)
            s.wfile.write(bytes(str(T), 'UTF-8'))  # ?
            visits[ID][2].start()

        elif ((path == "/hb_done") and (ID in visits)):
            print("Destruction: ", ID, " at ", ts)
            del visits[ID]
            s.wfile.write(bytes("So Long, and Thanks for All the Fish!", 'UTF-8'))

        elif (((path == "/hb_ping") or (path == "/hb_init")) and (ID in visits)):  #
            # TODO: make sure visits[ID] exists!
            print("HEART-BEAT for: ", ID, " at ", ts)  # Here i come again... 
            lastts = visits[ID][0]
            lastt = visits[ID][1]
            overdue = visits[ID][3]
            #            if (ts - lastts) > lastt: # Sorry Sir, but you are too late :-(
            #                overdue += 1

            if overdue > 3:
                print("Overdue counter: ", overdue)  # TODO: early detection of overdue clients!!???
                # s.wfile.write("dead")  # ?
            #                del visits[ID] #??
            T = T + 1  # max(3, (T*11)/8)
            visits[ID] = (ts, T, Timer(T, toolate, [ID]), 0)
            s.wfile.write(bytes(str(T), 'UTF-8'))
            visits[ID][2].start()
            # WHAT ELSE????
        return

    def do_POST(s):
        MyHandler.do_GET(s)

def test_server(HandlerClass=MyHandler, ServerClass=HTTPServer, protocol="HTTP/1.0"):
    """Test the HTTP request handler class.
    """

    server_address = (HOST_NAME, PORT_NUMBER)

    HandlerClass.protocol_version = protocol
    httpd = ServerClass(server_address, HandlerClass)

    sa = httpd.socket.getsockname()
    print("Serving HTTP on", sa[0], "port", sa[1], "...")
    httpd.serve_forever()


def hb_read(msg):
    return str(urlopen(HB_SERVER_URL + msg).read().decode('UTF-8'))

def test_client():
    t = randint(2, 5)
    #    APP_ID =  # + str(randint(99999999, 9999999999)) # TODO: get unique ID from server?

    print("List HB apps: {}".format(hb_read("/list")))
    print("APP HB Status: {}".format(hb_read("/status")))

    tt = hb_read("/hb_init?" + str(t) + "&appid=" + APP_ID)
    print("Initial response: ", tt)

    overdue = 0

    i = 0
    #    for i in xrange(1, 25):
    #    while True:
    while tt != "dead":
        i = i + 1
        d = randint(0, int((int(t) * 5) / 4))

        try:
            if d > int(tt):
                print(d, " > ", tt, "?")
                overdue += 1
        except:
            pass

        print("heart-beat: ", i, "! Promise: ", t, ", Max: ", tt, ", Delay: ", d, " sec........ overdues?: ", overdue)
        sleep(d)

        # heartbeat: 
        t = randint(0, 5)

        #        print "List HB apps: " + urlopen(HB_SERVER_URL + "/list" ).read()
        #        print "APP HB Status: " + urlopen(HB_SERVER_URL + "/status" ).read()

        print("Ping: ", t)
        tt = hb_read("/hb_ping?" + str(t) + "&appid=" + APP_ID)
        print("Pong: ", tt)

    #        print "List HB apps: " + urlopen(HB_SERVER_URL + "/list" ).read()
    #        print "APP HB Status: " + urlopen(HB_SERVER_URL + "/status" ).read()

    print("Ups: we run out of time...")
    tt = hb_read("/hb_done?0" + "&appid=" + APP_ID)
    print("Goodbye message: ", tt)

    print("List HB apps: {}".format(hb_read("/list")))
    print("APP HB Status: {}".format(hb_read("/status")))


if __name__ == '__main__':
    print(sys.argv)
    if len(sys.argv) == 1:
        test_client()
    else:  # Any Arguments? => Start HB Server
        #        if (sys.argv[1] == "-server"):
        test_server()