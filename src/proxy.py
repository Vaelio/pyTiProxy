#!/usr/bin/env python3
#-*- coding:utf-8 -*-


from time import time
from threadlib2 import cltthread
from sys import version_info, exit
from sock_builder import start_ssl_socket, start_standard_socket
from argparse import ArgumentParser
from logger import init_logger
from socket import error as sock_err


__doc__ = """The main script of the package. It'll start the proxy server and handle everything
"""
__all__ = ['__init_serv__', 'loger', 'worker', 'cltthread']
__author__ = ['Eudeline Valentin', 'Benoît Decampenaire']
__reason__ = """ My own little project """
__date__ = """ v2rc1 24 dec 2016 """

if version_info[0] < 3:
    exit("This program won't work with python version below python 3")


def __init_serv__(ssl, address, port, crt, key):

    """ This func inits everything. Defines the queue, starts the pool of http workers,
        starts the logger thread, bind our script to 0.0.0.0:8080, and finally starts new
        thread for each client that connects
    """

    from multiprocessing import Process as Child, Queue
    # Defines a FIFO queue for requests process
    ownqueue = Queue()
    logger = init_logger("log/proxy.log")
    if ssl:
        sock, context = start_ssl_socket(crt, key, server_side=True)
    else:
        sock, context = start_standard_socket()
    # We now don't need workers anymore because we had to adjust for ssl
    # We start a pool of N workers
    # They are used to serve each requests independently from the source client
    for num in range(15):
        thread = Child(target=cltthread, args=(logger, ownqueue, context, ssl))
        # thread = Process(target=cltthread, args=(queue, logqueue, ownqueue))
        # We set each worker to Daemon
        # This is important because we can safely ^C now
        thread.daemon = True
        thread.start()
    # We start the thread that will log every thing into http.log
    try:
        sock.bind((address, port))
    except sock_err:
        print(
            '%s - [INFO] Exception SOCKET_ERROR: Can\'t bind.Please try again later.' %
            (time()))
    else:
        print('%s - [INFO] Server listening on %s:%s' % (time(), address, port))
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
    parser = ArgumentParser(description='ProxyPy is a reverse proxy for lulz :)')
    parser.add_argument('--ssl', '-s', action='store_true', required=False)
    parser.add_argument('--address', '-i', metavar='IP address of interface that should listen',
                        nargs='?', type=str, required=True)
    parser.add_argument('--port', '-p', metavar='Port that should listen', nargs='?', type=int, required=False,
                        default=8080)
    parser.add_argument('--crt', '-c', metavar='crt file for ssl purpose', nargs='?', type=str, required=False)
    parser.add_argument('--key', '-k', metavar='key file for ssl purpose', nargs='?', type=str, required=False)
    args = parser.parse_args()
    __init_serv__(args.ssl, args.address, args.port, args.crt, args.key)
