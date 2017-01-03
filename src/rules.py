from re import findall

hacker_agent = {b'SQLMAP', b'USERAGENT', b'NIKTO', b'VEGA', b'BLACKSUN', b'NESSUS'}
hacker_data = [b'\'', b'SELECT', b'UNION', b'AND', b'LIKE', b' ', b'%20', b'%2520',
               b'DROP', b'LOAD', b'FILE', b'SCRIPT', b'DOCUMENT', b'COOKIE']
hacker_referer = {'%3D', '%27', "'", "%"}

def dump_infos(msg):
    return {
            'referer' : msg.split(b'Referer: ')[1].split(b'\r\n')[0] if b'Referer: ' in msg else b'',\
            'data' : msg.split(b'\r\n\r\n')[1] if len(msg.split(b'\r\n\r\n')) > 0 else b'',\
            'user_agent' : msg.split(b'User-Agent: ')[1].split(b'\r\n')[0] if b'User-Agent: ' in msg else b''
           }

def catch_hackers(client_infos, addr, sock_client, fdclient, msg, detect=False):
    try:
        finder_agent = findall(b'\s*\(?(.+?)[/\s][\d.]+', client_infos['user_agent'])
        for string in finder_agent:
            if string in hacker_agent:
                generate_404(fdclient)
                sock_client.close()
                detect = True
        for item in client_infos['referer']:
            if item in hacker_referer:
                generate_404(fdclient)
                sock_client.close()
                detect = True
        if client_infos['data'] is not None:
            for item in hacker_data:
                if item in client_infos['data']:
                    generate_404(fdclient)
                    sock_client.close()
                    detect = True
    except IndexError as  e:
        print(e)
        sock_client.close()
        generate_404(fdclient)
        detect = True
    return detect


