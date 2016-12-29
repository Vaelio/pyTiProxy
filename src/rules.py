#!/bin/env python
# -*- coding:utf-8 -*-

from re import findall

hacker_agent = {b'SQLMAP', b'USERAGENT', b'NIKTO', b'VEGA', b'BLACKSUN', b'NESSUS'}
hacker_data = [b'\'', b'SELECT', b'UNION', b'AND', b'LIKE', b' ', b'%20', b'%2520',
               b'DROP', b'LOAD', b'FILE', b'SCRIPT', b'DOCUMENT', b'COOKIE']
hacker_referer = {'%3D', '%27', "'", "%"}

def catch_hackers(client_infos, addr, sock_client, fdclient, msg, detect):
    try:
        finder_agent = re.findall(b'\s*\(?(.+?)[/\s][\d.]+', client_infos[b'user_agent'][0])
        if addr[0] not in hackers:
            hackers[addr[0]] = {b'count': 0}
        for string in finder_agent:
            if string in hacker_agent:
                hackers[addr[0]][b'message'] = msg
                generate_404(fdclient)
                sock_client.close()
                detect = True
        for item in client_infos[b'referer']:
            if item in hacker_referer:
                hackers[addr[0]][b'message'] = msg
                generate_404(fdclient)
                sock_client.close()
                detect = True
        if client_infos[b'data'] is not None:
            for item in hacker_data:
                if item in client_infos[b'data']:
                    hackers[addr[0]][b'message'] = msg
                    generate_404(fdclient)
                    sock_client.close()
                    detect = True
    except IndexError as  e:
        print(e)
        sock_client.close()
        generate_404(fdclient)
        detect = True
    return detect


