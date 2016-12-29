#!/bin/env python
# -*- coding:utf-8 -*-

from re import findall

hacker_agent = {b'SQLMAP', b'USERAGENT', b'NIKTO', b'VEGA', b'BLACKSUN', b'NESSUS'}
hacker_data = [b'\'', b'SELECT', b'UNION', b'AND', b'LIKE', b' ', b'%20', b'%2520',
               b'DROP', b'LOAD', b'FILE', b'SCRIPT', b'DOCUMENT', b'COOKIE']
hacker_referer = {'%3D', '%27', "'", "%"}

def dump_infos(msg):
    return {
            'referer' : msg.split('Referer: ')[1].split('\r\n')[0] if 'Referer: ' in msg else None,\
            'data' : msg.split('\r\n\r\n')[1] if len(msg.split('\r\n\r\n')) > 0 else None,\
            'user_agent' : msg.split('User-Agent: ')[1].split('\r\n')[0] if 'User-Agent: ' in msg else None
           }

def catch_hackers(client_infos, addr, sock_client, fdclient, msg, detect):
    try:
        finder_agent = re.findall(b'\s*\(?(.+?)[/\s][\d.]+', client_infos[b'user_agent'][0])
        for string in finder_agent:
            if string in hacker_agent:
                generate_404(fdclient)
                sock_client.close()
                detect = True
        for item in client_infos[b'referer']:
            if item in hacker_referer:
                generate_404(fdclient)
                sock_client.close()
                detect = True
        if client_infos[b'data'] is not None:
            for item in hacker_data:
                if item in client_infos[b'data']:
                    generate_404(fdclient)
                    sock_client.close()
                    detect = True
    except IndexError as  e:
        print(e)
        sock_client.close()
        generate_404(fdclient)
        detect = True
    return detect


