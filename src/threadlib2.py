from time import sleep
from ssl import SSLWantWriteError, SSLWantReadError
from socket import error as sock_err, socket, SHUT_RDWR
from select import select
from math import ceil


def cltthread(logger, ownqueue, context, ssl):
    try:
        while True:
            sock, addr = ownqueue.get()
            logger.info('Accepting new connection from %s' % addr[0])
            if ssl:
                try:
                    sock = context.wrap_socket(sock, server_side=True)
                except OSError:
                    print('are you sure you got the corresponding certificate?')
                    shutdown(sock)
                    continue
            sock.setblocking(False)
            msg = b""
            for data in recvall_sock(sock):
                msg += data
            # recvall returned good data
            if not msg:
                logger.warning('Received empty request, closing socket')
                shutdown(sock)
                continue
            dst, port = parserequest(msg, ssl)
            if not dst or not port:
                logger.warning('Meh, i think %s is fuzzing us' % (addr[0]))
                continue
            # work to be done :)
            # check wether or not the request is legit
            # now we should be able to send it to worker
            try:
                request_and_forward(sock, (dst, port), msg, context if ssl else None)
            except AssertionError:
                logger.warning('Oops ! Something wrong happened with %s requesting %s' % (addr[0], dst))
            shutdown(sock)
            logger.info(b'job "' + msg.split(b' ')[0] + b' ' + dst + msg.split(b' ')[1].split(b'\r\n')[0] + b'" is ok')
    except KeyboardInterrupt:
        pass


def shutdown(sock):
    try:
        sock.shutdown(SHUT_RDWR)
        sock.close()
    except Exception:
        pass
    return


def waitforsock_r(sock):
    waiting = True
    while waiting:
        r, w, e = select((sock,), (), (), 0)
        if r and r[0] == sock:
            waiting = False
    return sock


def waitforsock_w(sock):
    waiting = True
    while waiting:
        r, w, e = select((), (sock,), (), 0)
        if w and w[0] == sock:
            waiting = False
    return sock


def request_and_forward(sc, dest, msg, context):
    ss = socket()
    if context:
        ss = context.wrap_socket(ss, server_side=False)
    assert ss.connect_ex((dest[0], dest[1])) == 0
    ss.setblocking(0)
    if b'Keep-Alive' in msg.split(b'\r\n\r\n')[0] or b'keep-alive' in msg.split(b'\r\n\r\n')[0]:
        msg = msg.replace(b'Connection: Keep-Alive', b'Connection: close')
        msg = msg.replace(b'Connection: keep-alive', b'Connection: close')
    assert sendall_sock(ss, msg) == len(msg)
    for data in recvall_sock(ss):
        if b'Keep-Alive' in data.split(b'\r\n\r\n')[0] or b'keep-alive' in data.split(b'\r\n\r\n')[0]:
            data = data.replace(b'Connection: Keep-Alive', b'Connection: close')
            data = data.replace(b'Connection: keep-alive', b'Connection: close')
        try:
            assert sendall_sock(sc, data) == len(data)
        except BrokenPipeError:
            shutdown(ss)
            raise AssertionError
    shutdown(ss)
    return


def parserequest(data, ssl, pssl=443, pstd=80):
    try:
        dst = data.split(b'Host: ')[1].split(b'\r\n')[0]
        if b':' in dst:
            port = int(dst.split(b':')[1])
            dst = dst.split(b':')[0]
        elif ssl:
            port = pssl 
        else:
            port = pstd
        return dst, port
    except IndexError:
        # the client didn't specify a host
        return None, None


def recvall_sock(sock, maxtc=5):
    over, sb, tc, buffsize = False, b"", 0, 536
    waitforsock_r(sock)
    while not over:
        try:
            sb = sock.recv(buffsize)
        except SSLWantReadError:
            tc += 1
            if tc >= maxtc:
                break
            else:
                sleep(0.1)
                continue
        except Exception:
            tc += 1
            if tc >= maxtc:
                break
            else:
                sleep(0.1)
                continue
        else:
            tc = 0
            if not len(sb):
                over = True
            else:
                if len(sb) == buffsize:
                    # put a ceil just in case, because we cant recv a float amount
                    # of data.
                    buffsize = ceil(buffsize * 2)
                yield sb


def sendall_sock(sock, data):
    # This function doesn't manage timeout. It Could be not safe.
    over, buff, size = False, data, 0
    while not over:
        try:
            waitforsock_w(sock)
            # it looks like this works better for sending
            # but did we not just convert non blocking socket to blocking sockets ? :/
            # let's just hope we don't need to do that for recvall_sock, otherwise the performance
            # we gained using non blocking socket migtht be gone.
            size = sock.send(buff)
        except SSLWantWriteError:
            # we should not go there i think
            pass
        except sock_err:
            over = True
        else:
            buff = buff[size:]
            if not size:
                sleep(0.1)
            if not len(buff):
                over = True
    return len(data) if len(buff) == 0 else -len(buff)

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
