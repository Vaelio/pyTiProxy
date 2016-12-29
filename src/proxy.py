#!/bin/env python2
#-*- coding:utf-8 -*-

__doc__ = """The main script of the package. It'll start the proxy server and handle everything
"""
__all__ = ['__init_serv__', 'loger', 'worker', 'cltthread']
__author__ = ['Eudeline Valentin', 'Benoît Decampenaire']
__reason__ = """ My own little project """
__date__ = """ v2rc1 24 dec 2016 """

from socket import socket, SOL_SOCKET, SO_REUSEADDR, error as sock_err
from multiprocessing import Process as Thread, Queue
from sys import api_version
from time import time, sleep
from requests import get
from threadlib2 import loger, worker, cltthread
from sys import version_info, exit

if version_info[0] < 3:
    exit("This program won't work with python version below python 3")

def __init_serv__():
    """ This func inits everything. Defines the queue, starts the pool of http workers,
        starts the logger thread, bind our script to 0.0.0.0:8080, and finally starts new
        thread for each client that connects
    """

    # Defines a FIFO queue for requests threads
    queue = Queue()
    # Defines another FIFO queue for LOG thread
    logqueue = Queue()
    ownqueue = Queue()

    # We start a pool of N workers
    # They are used to serve each requests independently from the source client
    for num in range(6):
        thread = Thread(target=worker, args=(queue, logqueue, num))
        # We set each worker to Daemon
        # This is important because we can safely ^C now
        thread.start()
    for num in range(6):
        thread = Thread(target=cltthread, args=(queue, logqueue, ownqueue))
        # We set each worker to Daemon
        # This is important because we can safely ^C now
        thread.start()

    # We start the thread that will log every thing into http.log
    for num in range(3):
        logthread = Thread(target=loger, args=(logqueue,))
        # Once again, we are setting this thread to daemonic mode
        # for ^C sakes
        logthread.start()

    sock = socket()
    # We bind ourselves to port 8080 (usual port for proxy though)
    # We use SO_REUSEADDR argument to be able to restart the proxy script right after we kill it
    # Doesn't work every time sadly
    # There is probably a lot of timeout errors
    sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    try:
        sock.bind(('0.0.0.0', 8080))
    except sock_err:
        print(
            '%s - [INFO] Exception SOCKET_ERROR: Can\'t bind.Please try again later.' %
            (time()))
    else:
        print('%s - [INFO] Server listening to 0.0.0.0:8080' % (time()))
    try:
        # Here we just wait until we received a new connection (from a client)
        # We then start a thread to handle this specific client / request
        sock.listen(0)
        while True:
            # max connection is set to 0, but i guess we could set it to the number of
            # started workers. Possibly using threading.activeCount()
            cltsock, cltaddr = sock.accept()
            ownqueue.put([cltsock, cltaddr])
    except KeyboardInterrupt:
        sock.close()
        print('Bye')
        exit(0)

if __name__ == '__main__':
    __init_serv__()
