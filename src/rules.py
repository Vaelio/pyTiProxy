from re import findall, IGNORECASE
from time import asctime
from os import listdir
from logging import info

hacker_agent = {b'SQLMAP', b'USERAGENT', b'NIKTO', b'VEGA', b'BLACKSUN', b'NESSUS'}
hacker_data = [b'\'', b'SELECT', b'UNION', b'AND', b'LIKE', b'%2520',
               b'DROP', b'LOAD', b'FILE', b'SCRIPT', b'DOCUMENT', b'COOKIE']
hacker_uri = {b'%3D', b'%27', b'%', b'\'', b'SELECT', b'UNION', b'AND', b'LIKE'}


def dump_infos(msg, sock_client, fdclient):
    try:
        uri = msg.split(b' ')[1].split(b' ')[0]
        return {
                'uri': uri,
                'data': msg.split(b'\r\n\r\n')[1] if len(msg.split(b'\r\n\r\n')) > 0 else b'',
                'user_agent': msg.split(b'User-Agent: ')[1].split(b'\r\n')[0] if b'User-Agent: ' in msg else b'',
                'host': msg.split(b'Host: ')[1].split(b'\r\n')[0]
               }
    except IndexError:
        sock_client.close()
        generate_404(fdclient)


def generate_404(fdclient):
    try:
        error = """HTTP/1.1 404 File not found
        Date: {} GMT
        Connection: close
        Content-Type: text/html
        Content-Length: 194

        <head>
        <title>Error response</title>
        </head>
        <body>
        <h1>Error response</h1>
        <p>Error code 404.
        <p>Message: File not found.
        <p>Error code explanation: 404 = Nothing matches the given URI.
        </body>""".format(asctime())
        fdclient.write(bytes(error.encode('utf-8')))
    except Exception:
        return 1


def catch_hackers(client_infos, sock_client, fdclient, rules, detect=False):
    for item in rules:
        if client_infos['host'] == item:
            sock_client.close()
            generate_404(fdclient)
            detect = True
    try:
        finder_agent = findall(b'\s*\(?(.+?)[/\s][\d.]+', client_infos['user_agent'], flags=IGNORECASE)
        for item in finder_agent:
            if item.upper() in hacker_agent:
                detect = True
                return detect
        for item in hacker_uri:
            if item in client_infos['uri']:
                detect = True
                return detect
        if client_infos['data'] is not None:
            for item in hacker_data:
                if item.upper() in client_infos['data']:
                    detect = True
                    return detect
    except (IndexError, TypeError):
        sock_client.close()
        generate_404(fdclient)
        detect = True
    return detect


def read_blacklist(logger, basedir="/var/lib/blacklist/"):
    try:
        content = []
        for item in listdir(basedir):
            for files in listdir(basedir + item):
                if files == 'domains':
                    with open(basedir  + item + '/' + files, 'r') as fd:
                        content += fd.read().split('\n')[:-1]
    except FileNotFoundError:
        info(logger(date=asctime(), type='WARNING',
                    msg='No blacklist detected'))
    return content
