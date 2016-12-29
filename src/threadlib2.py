#!/bin/python2.7
#-*- coding:utf-8 -*-
__doc__ = '''
    thread library for proxy script. It provides every function that we are threading
'''

__all__ = ['cltthread', 'loger', 'worker', 'time']

from time import time
from multiprocessing import Lock
from datetime import datetime
from rules import catch_hackers, dump_infos
from sock_builder import start_ssl_socket,start_standard_socket


def cltthread(queue, logger, ownqueue):
    """ This func is what manages each client connecting, for ONE requests


    @type sock: socket
    @param sock: Communication socket between proxy and client
    @type addr: tuple (ipv4, port)
    @param addr: Address representation of the client
    @type queue: queue
    @param queue: queue that will contain HTTP request to treat
    """
    # we receive what the client wanna do
    try:
        transmission_over = False
        while not transmission_over:
            sock, addr = ownqueue.get()
            content = b""
            received_all_data = False
            while not received_all_data:
                buffer_string = sock.recv(536)
                content += buffer_string
                if len(buffer_string) < 536:
                    received_all_data = True
            msg = content
            if not len(msg):
                pass
            # we parse it
            try:
                dst = msg.split(b'Host: ')[1].split()[0]
                port = int(dst.split(b':')[1]) if b':' in dst else 80
                dst = msg.split(b':')[0] if b':' in dst else dst
            except IndexError:
                # format of msg does not match usual stuff
                # Somebody else is probably attempting to get through our proxy
                # We need to do something here
                sock.close()
                continue
            # msg = ' '.join(msg.split()[0].split(' ')[1:])
            # then we put it in the queue so that the workers will do their job
            logger.info("%s requested %s:%s"%(addr, dst, port))
            queue.put([sock, dst, port, msg, addr])
            # finally LOG the file
            #print '%s - [INFO] %s - %s'%(time(), addr, repr(msg))
            # then returns
    except KeyboardInterrupt:
        return 0



def loger(queue):
    """
    This func handles any log a client may produce

    @type queue: queue
    @param queue: queue that will contain all the log from HTTP request
    """
    try:
        while True:
            event = queue.get()
            content = '%s - [INFO] %s - %s\n'%(\
                        time(),\
                        event[0],\
                        repr(event[1]).replace('\r\n', '\\r\\n')\
                        )
            with Lock():
                print('%s - [INFO] %s - %s [BACKLOG: %s]'%(time(),event[0], repr(event[1]).replace('\r\n', '\\r\\n'), queue.qsize()))
                with open('http.log', 'a+') as file_descriptor:
                    file_descriptor.write(content)
    except KeyboardInterrupt:
        return 0

def generate_404(fdclient):
    fdclient.write(b"""HTTP/1.1 404 File not found\r\nDate: %s\r\nConnection: close\r\nContent-Type: text/html\r\nContent-Length: 194\r\n\r\n<head>\r\n<title>Error response</title>\r\n</head>\r\n<body>\r\n<h1>Error response</h1>\r\n<p>Error code 404.\r\n<p>Message: File not found.\r\n<p>Error code explanation: 404 = Nothing matches the given URI.\r\n</body>"""%datetime.now())
    try:
        fdclient.close()
    except :
        # wtf is this shit
        return 1
    return 0

def decidebufflength(length):
    if length < (0.5 * 1024):
        # file is really small
        bufflength = length
        # we download it in one time
    elif length < (5 * 1024):
        # file size < 5 ko
        bufflength = 1024
        # We download at 1 ko at a time
    elif length < (100 * 1024):
        # medium sized file
        bufflength = 16 * 1024
        # We download 16 ko each time
    else:
        # Really big file (over 100k bytes)
        bufflength = 32 * 1024
        # We download 32 ko each time
    return bufflength



def getheaders(fdserver):
    headers = b""
    while True:
        try:
            serverbuffer = fdserver.readline()
            headers += serverbuffer
            if not len(serverbuffer.split()):
                return headers
        except ConnectionResetError:
            return False


def exit_con(fdclient, sock_client, fdserver, sock_server):
    try:
        if not fdclient.closed:
            fdclient.close()
            sock_client.close()
        if not fdserver.closed:
            fdserver.close()
            sock_server.close()
    except sock_err:
        ################ LOG ######################
        # We should log whenever we have this case happening. 
        # That means that the socket got closed between the begining and the end of the communication
        return False
    else:
        return True


def worker(queue, logger, num, ssl, crt, key):
    """
    This function is the threaded one that will be treating all HTTP request in live.
    It is meant to use inside a pool of thread. It will pickup any requests in its queue,
    will forward the request to the destinated webserver,
    and then forward back the returned packets to the client.

    @type queue: queue
    @param queue: queue that will contain all HTTP requests
    @type num: int
    @param num: the number of the thread.
    """
    try:
        while True:
            # If the queue is not empty (means that client wants something)
            # We should delete this line, i think it is killing the process
            # if not queue.empty():
            # We take the last oldest instruction from the queue
            # format of each element:
            # [client socket, remote host, remote port, client request]
            sock_client, dst, port, msg, addr = queue.get()
            fdclient = sock_client.makefile('rwb', 0)
            if catch_hackers(dump_infos(msg), addr, sock_client, fdclient, msg):
                generate_404(fdclient)
                #LOG HERE
            try:
                if ssl:
                    sock = start_ssl_socket(crt, key, server_side=False)
                else:
                    sock = start_standard_socket()
                sock = socket()
                # Connect to remote host
                sock.connect((dst, port))
                fdserver = sock.makefile('rwb', 0)
                # Send the HTTP Request
                fdserver.write(msg)
                #print 'Worker %s connected to remote host'%num
            except TimeoutError:
                # Could not connect to host
                # Before closing we should send some data to the user
                # 503 maybe ? or Bad Gateway
                fdclient.close()
                sock_client.close()
                continue
            except sock_err:
                fdclient.close()
                sock_client.close()
                continue
            except OSError:
                # no route to host
                # Before closing we should send some data to the user
                # 503 maybe ? or Bad Gateway
                fdclient.close()
                sock_client.close()
                if not exit_con(fdclient, sock_client, fdserver, sock):
                    # we should log. something wrong happened
                    pass
                continue
            # Setup every thing for server communication
            content, length, chunked = b'', 0, False
            done = False
            # Now we will work out with the server
            # We loop on the recv to get everything

            headers = getheaders(fdserver)
            if not headers:
                # We should send again some kind of message saying that something wrong happened between here and the server
                # right now we just ignore
                logger.warning("Could not connect to %s:%s for %s"%(dst, port, addr))
                continue
            fdclient.write(headers)
            chunked = True if b'Transfer-Encoding' in headers and b'chunked' in headers.split(b'Transfer-Encoding')[1].split(b'\r\n')[0] else False
            length = int(headers.split(b'Content-Length: ')[1].split(b'\r\n')[0]) if b'Content-Length' in headers else 0
            if msg.split(b' ')[0] in [b'HEAD', b'OPTIONS', b'TRACE', b'DELETE']:
                exit_con(fdclient, sock_client, fdserver, sock)
            elif length and not chunked:
                #case: Content-Length: X
                # We should build some kind of coefficient, to see in how many
                # times it is faster to download (ie you shouldn't download small
                # files in 256 parts, nor you should download big files in 3 parts)
                bufflength = decidebufflength(length)
                while len(content) < length:
                    minibuff = fdserver.read(bufflength if length - len(content) > bufflength else length - len(content))
                    content += minibuff
                # We should be done downloading the page. Gotta send it back
                fdclient.write(content)
                exit_con(fdclient, sock_client, fdserver, sock) 
            elif chunked:
                #case: Transfert-Encoding: Chunked
                if length:
                    # Chunked = True and length = True
                    # I dont think it is possible
                    try:
                        fdclient.write('Not implemented')
                    except sock_err:
                        pass
                else:
                    # Chunked = True and length = False
                    # Probably will be the most used case
                    transmission_over = False
                    while not transmission_over:
                        rawchunksize = fdserver.readline()
                        if rawchunksize == b'\r\n':
                            content += rawchunksize
                        elif rawchunksize == b'0\r\n':
                            content += rawchunksize + b'\r\n'
                            fdclient.write(content)
                            exit_con(fdclient, sock_client, fdserver, sock)
                            transmission_over = True
                        else:
                            content += rawchunksize
                            chunksize = int(rawchunksize.split(b'\r\n')[0], 16)
                            data = b''
                            # we had to implement this loop because on py3 when the internet is slow
                            # you can have the issue where not all the data is read but only part of it
                            # which then crashes because the programs tries to read the next chunk size 
                            # with random http data
                            while not len(data) == chunksize:
                                data += fdserver.read(chunksize-len(data))
                            content += data
    except KeyboardInterrupt:
        return 0

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
