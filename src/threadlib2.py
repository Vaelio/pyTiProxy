from time import sleep, asctime
from ssl import SSLWantWriteError, SSLWantReadError
from socket import error as sock_err, socket, SHUT_RDWR
from rules import (dump_infos, generate_404, catch_hackers)
from select import select
from math import ceil
from logging import info


def cltthread(logger, ownqueue, context, ssl):
    '''
    This is the main worker function.
    
    logger: logger object. Will be used for any logging and printing
    ownqueue: the queue where the worker will take its job from
    context: the SSL context to wrap the socket with
    ssl: the SSL switch. Setting it to True will make the worker use the given context to wrap the socket.
    '''
    try:
        while True:
            sock, addr = ownqueue.get() # Getting a new job *o*
            info(logger(date=asctime(), type='INFO', message='Accepting new connection from %s' % addr[0]))
            if ssl:
                # wrap the socket if ssl mode ON
                try:
                    sock = context.wrap_socket(sock, server_side=True)
                except OSError:
                    # meh, couldnt wrapp. It appears that it could be that the certificate is not in the good case
                    print('are you sure you got the corresponding certificate?')
                    # shut every thing off
                    shutdown(sock, logger)
                    # and go get a new job
                    continue
            sock.setblocking(False) # POWEEEEEERR !
            msg = b""
            for data in recvall_sock(sock):
                # accumulate the data sent by the client
                msg += data
            # recvall returned good data
            if not msg:
                # if the returned data is empty. we should not have too much of it now. 
                # In the past it was caused by keep alive, but now we bypass it.
                info(logger(date=asctime(), type='WARNING', msg = 'Received empty request, closing socket'))
                # shut every thing off
                shutdown(sock, logger)
                # and again, go get a new job
                continue
            # if everything is fine, retrieve (host, port) from the request
            fdclient = sock.makefile('rwb', 0)
            dst, port = parserequest(msg, ssl)
            client_infos = dump_infos(msg, sock, fdclient)
            if not dst or not port:
                # if the request was malformed
                info(logger(date=asctime(), type='WARNING', msg='Meh, i think %s is fuzzing us' % (addr[0])))
                # properly close the socket :D
                shutdown(sock, logger)
                # once again, go get a new job
                continue
            detect = catch_hackers(client_infos, sock, fdclient)
            if not detect:
                try:
                    # send the request to the server and forward the data to the client
                    request_and_forward(sock, (dst, port), msg, context if ssl else None, logger)
                except AssertionError:
                    # if anything crashed during this step, log and quit :) [yes, again]
                    info(logger(date=asctime(), type='WARNING',
                                msg='Oops ! Something wrong happened with %s requesting %s' % (addr[0], dst)))
                # anyway this is over, shutdown the socket,
                shutdown(sock, logger)
                # and go get a new job
                info(logger(date=asctime(), type='INFO',
                            msg=b'job "' + msg.split(b' ')[0] + b' ' + dst + msg.split(b' ')[1].split(b'\r\n')[0] + b'" is ok'))
            else:
                generate_404(fdclient)
                shutdown(sock, logger)
                info(logger(date=asctime(), type='WARNING',
                            msg='Hacker detected ! {} from {}'.format(addr, client_infos)))
    except KeyboardInterrupt:
        # handle the Ctrl+ C
        pass


def shutdown(sock, logger):
    '''
    wrapper to properly shut socket down. closing socket is often not enough to keep the client from hanging.
    shutting down the socket should be enough though
    
    sock: socket to shutdown
    logger: logger object to handle exception
    '''
    try:
        sock.shutdown(SHUT_RDWR) # shuts off READ / WRITE mode on the socket
        sock.close() # and closes it
    except Exception as e:
        info(logger(date=asctime(), type='EXCEPTION', msg=e))
        # if for some weird reason, something happened while trying to close the socket. Log and quit
    return


def waitforsock(sock, action):
    '''
    Wrapper for waiting until socket is ready for given action (READ/WRITE)
    [ use with care. At this state it has a DOS vulnerability ]
    
    sock: socket object to wait for
    action: either read or write (TRUE means READ and FALSE means WRITE)
    '''
    waiting = True
    while waiting:
        # this loop will probably generate a lot of CPU Consumption if the socket nevers gets ready.
        # It's probably an ez DOS method. 
        # TODO:
        #      - make a timeout system on this function. this way it will patch the DOS vulnerabilit in this version
        if action:
            # if we want to wait for the socket to be readable
            r, w, e = select((sock,), (), (), 0)
            if r and r[0] == sock:
                # if the list returned by select is really a list and the first element of the list is our socket
                # the socket is ready! yepeee!
                waiting = False
        else:
            # if we want to wait for the socket to be writable
            r, w, e = select((), (sock,), (), 0)
            if w and w[0] == sock:
                # if the list returned by select is really a list and the first element of the list is our socket
                # the socket is ready ! hehehe
                waiting = False
    # every thing was fine, return the socket
    return sock


def request_and_forward(sc, dest, msg, context, logger):
    '''
    This function is executed after the main worker received what the client wants to get.
    It sends the request to the server and then transfer the answer to the client.
    
    sc: socket connected to the client
    dest: tuple containing the host (and its port) that the client wants to join
    msg: the complete request
    context: SSL context to wrap socket with
    logger: logger object to handle exceptions
    '''
    ss = socket()
    if context:
        ss = context.wrap_socket(ss, server_side=False)
    # from now on we use builtin assert in order to easily handle any network/http default 
    # and stop the communication straight away, the client will redo the request anyway.
    assert ss.connect_ex((dest[0], dest[1])) == 0 # assert the connection state, 0 means every thing is fine
    ss.setblocking(0) # Non blocking socket for more power ! :-p
    msg = handleKeepAlive(msg)
    assert sendall_sock(ss, msg) == len(msg) # if not all data was sent, meh something went wrong
    for data in recvall_sock(ss):
        # for each data yielded from our generator (data received from the server)
        data = handleKeepAlive(data) # keep alive patch
        try:
            assert sendall_sock(sc, data) == len(data) # if we did not send to the client the whole data returned
                                                       # redo the request, once again.
        except BrokenPipeError:
            shutdown(ss, logger) # communication between client and proxy crashed. properly close the server socket
            raise AssertionError # before raising the AssertionError
    shutdown(ss, logger) # if everything was fine, close the server socket 
    return # and return properly :-)

def handleKeepAlive(data):
    '''
    Parse data to patch eventual keep alive headers.
    We CANNOT afford to have worker stuck with one client forever
    
    data: string to parse and patch
    '''
    if b'Keep-Alive' in data.split(b'\r\n\r\n')[0] or b'keep-alive' in data.split(b'\r\n\r\n')[0]:
        data = data.replace(b'Connection: Keep-Alive', b'Connection: close')
        data = data.replace(b'Connection: keep-alive', b'Connection: close')
    return data

def parserequest(data, ssl, pssl=443, pstd=80):
    '''
    Wrapper to parse the data and return the tuple (host, port) if everything is fine else (None, None)
    
    data: string holding the data to parse
    ssl: ssl switch to turn its mode ON or OFF
    pssl: this is the port used in case of ssl
    pstd: this is the port used in case of http
    '''
    try:
        dst = data.split(b'Host: ')[1].split(b'\r\n')[0]
        # get the host header
        if b':' in dst:
            # if it has this form: www.host.com:1234
            port = int(dst.split(b':')[1]) # retrieve the port
            dst = dst.split(b':')[0] # and retrieve the real host
        elif ssl:
            # if no port were given (www.host.com) and ssl mode ON
            port = pssl 
        else:
            # if no port were given (www.host.com) and ssl mode OFF
            port = pstd
        return dst, port # every thing was fine, return (Host, port)
    except IndexError:
        # the client didn't specify a host
        # I think it's probably a fuzzing attempt but anyway this is not a proper http request.
        return None, None


def recvall_sock(sock, maxtc=5):
    '''
    This is the generator that will yield the data received from remote
    
    sock: the socket to read
    maxtc: the max timeout count. (default is 5; it means 5 * 0.1 s, so 0.5s)
    '''
    over, sb, tc, buffsize = False, b"", 0, 536
    waitforsock(sock, True)
    while not over:
        # while the transmission still continue
        # (transmission is over when:
        #                             - the timeout has been reached
        #                             - the buffer returned was just empty ( which means, distant server closed the socket)
        try:
            sb = sock.recv(buffsize)
        except SSLWantReadError:
            # this error is triggered is SSL mode, when there is no enough data in the socket
            # for it to be successfully decrypted. We decided to still increment the timeout counter. this is for speed sake
            tc += 1
            if tc >= maxtc:
                # if the timeout has been reached
                over = True
            else:
                # if the timeout hasn't been reached, just wait a bit before re recv'ing
                sleep(0.1)
                continue
        except Exception:
            # in case another exception appeared
            # we could merge both except. But the point of doing both is that we could log differently
            # the "normal SSL Exception" and the "something wrong happened Exception"
            tc += 1
            if tc >= maxtc:
                # if the timeout has been reached
                over = True
            else:
                # if the timeout hasn't been reached, just wait a bit before re recv'ing
                sleep(0.1)
                continue
        else:
            # no exception were generated
            # reset the timeout counter, and parse the buffer
            tc = 0
            if not len(sb):
                # buffer was empty, usually it is caused when the socket has been closed remotely
                over = True
            else:
                # buffer was not empty, we can yield data hehe
                if len(sb) == buffsize:
                    # little optimization in order to speed the data transfert.
                    # if the whole buffer was filled, then increase its size
                    # you can change the multiplicator at will,
                    # we have put a ceil just in case, because we cant recv a float amount
                    # of data.
                    buffsize = ceil(buffsize * 2)
                # and finally yield the data :-)
                yield sb


def sendall_sock(sock, data):
    # This function doesn't manage timeout. It Could be not safe.
    over, buff, size = False, data, 0
    while not over:
        try:
            waitforsock(sock, False)
            # it looks like this works better for sending
            # but did we not just convert non blocking socket to blocking sockets ? :/
            # let's just hope we don't need to do that for recvall_sock, otherwise the performance
            # we gained using non blocking socket migtht be gone.
            size = sock.send(buff)
            # little precision on this previous instruction:
            # there is no way it will always send the whole data in one turn. This is why it is important to
            # get the size of the data sent. We will handle this in the "else" part
        except SSLWantWriteError:
            # we should not go there i think
            # I think it means, no enough data to encrypt ? wtf
            pass
        except sock_err:
            # something wrong happened during communication, it's broken
            over = True
        else:
            # everything is fine,
            # resize the buffer if not every thing were sent
            buff = buff[size:]
            if not size:
                # if no data were sent at all
                # the socket is probably lagging a bit, wait a bit
                sleep(0.1)
            if not len(buff):
                # if the buffer is now empty, we finally sent all the data we were provided :-)
                over = True
    # return the size of the whole data if every thing was fine,
    # else, the size of the leftover in negative (ie: return -len(buff))
    return len(data) if len(buff) == 0 else -len(buff)

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
