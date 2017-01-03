from ssl import create_default_context, Purpose
from socket import socket, SOL_SOCKET, SO_REUSEADDR, error as sock_err


def start_standard_socket():
    sock = socket()
    # We bind ourselves to port 8080 (usual port for proxy though)
    # We use SO_REUSEADDR argument to be able to restart the proxy script right after we kill it
    # Doesn't work every time sadly
    # There is probably a lot of timeout errors
    sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    return sock, None


def start_ssl_socket(crt, key, server_side):
    context = create_default_context(Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=crt, keyfile=key)
    sock = socket()
    if server_side:
        sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    return sock, context
