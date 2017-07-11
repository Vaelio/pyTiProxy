#!/usr/bin/env python3
#-*- coding:utf-8 -*-

from sys import version_info, exit
if version_info[0] < 3:
    # could maybe work with py2 now ?
    exit("This program won't work with python version below python 3")

from time import time, sleep
from threadlib2 import cltthread
from sock_builder import start_ssl_socket, start_standard_socket
from argparse import ArgumentParser
from logger import init_log
from socket import error as sock_err
from utils import readconfs
from multiprocessing import Process as Child, Queue

__doc__ = """The main script of the package. It'll start the proxy server and handle everything
"""
__all__ = ['__init_serv__', 'loger', 'worker', 'cltthread']
__author__ = ['Eudeline Valentin', 'Benoît Decampenaire']
__date__ = """ v2rc1 24 dec 2016 """



def __init_serv__(ssl, address, port, crt, key, config):

    """ This func inits everything. Defines the queue, starts the pool of http workers,
        starts the logger thread, bind our script to 0.0.0.0:8080, and finally starts new
        thread for each client that connects
    """
    # Defines a FIFO queue for requests process
    if not config and not address:
         exit('Please at least use --address/-i or --config/-C')
    elif config:
         parsed_config_file = readconfs(config)
         address = parsed_config_file['basic']['address']
         path = parsed_config_file['basic']['basic_path']
         port = int(parsed_config_file['basic']['port'])
         ssl = False if parsed_config_file['basic']['ssl'] == 'False' else True
         if ssl:
             crt = path + 'config/' + parsed_config_file['ssl']['crt']
             key = path + 'config/' + parsed_config_file['ssl']['key']
    ownqueue = Queue()
    logger = init_log()
    if ssl:
        sock, context = start_ssl_socket(crt, key, server_side=True)
    else:
        sock, context = start_standard_socket()
    # We now don't need workers anymore because we had to adjust for ssl
    # We start a pool of N workers
    # They are used to serve each requests independently from the source client
    # We start the thread that will log every thing into http.log
    try:
        sock.bind((address, port))
    except sock_err as e:
        print(
            '%s - [INFO] Exception SOCKET_ERROR: Can\'t bind.Please try again later.' %
            (time()))
    else:
        print('%s - [INFO] Server listening on %s:%s' % (time(), address, port))
        try:
            # Here we just wait until we received a new connection (from a client)
            # We then start a thread to handle this specific client / request
            sock.listen(0)
            for num in range(15):
                thread = Child(target=cltthread, args=(logger, sock, context, ssl))
                # thread = Process(target=cltthread, args=(queue, logqueue, ownqueue))
                # We set each worker to Daemon
                # This is important because we can safely ^C now
                thread.daemon = True
                thread.start()
            while True:
                # max connection is set to 0, but i guess we could set it to the number of
                # started workers. Possibly using threading.activeCount()
                sleep(1)
        except KeyboardInterrupt:
            sock.close()
            print('Bye')
            exit(0)


if __name__ == '__main__':
    parser = ArgumentParser(description='pyTiProxy is a reverse proxy/transparent proxy for lulz :)')
    parser.add_argument('--ssl', '-s', action='store_true', required=False)
    parser.add_argument('--address', '-i', metavar='IP address of interface that should listen',
                        nargs='?', type=str, required=False)
    parser.add_argument('--config', '-C', metavar='Config file to read', nargs='?', type=str, required=False)
    parser.add_argument('--port', '-p', metavar='Port that should listen', nargs='?', type=int, required=False,
                        default=8080)
    parser.add_argument('--crt', '-c', metavar='crt file for ssl purpose', nargs='?', type=str, required=False)
    parser.add_argument('--key', '-k', metavar='key file for ssl purpose', nargs='?', type=str, required=False)
    args = parser.parse_args()
    __init_serv__(args.ssl, args.address, args.port, args.crt, args.key, args.config)
