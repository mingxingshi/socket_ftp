#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author  :  smx
@file    :  main.py
@time    :  2021/7/14 16:38
"""


import socket
import os, sys
from hashlib import md5
import logging
import json
import shutil

BASEDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASEDIR)
from conf import settings

logging.basicConfig(level = logging.DEBUG,format = '%(asctime)s | %(name)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

class FtpClient(object):
    def __init__(self, ip, port):
        self.client = socket.socket()
        self.server_ip = ip
        self.server_port = port
        self.username = ''
        self.local_path = BASEDIR


    @staticmethod
    def help():
        msg = r"""
        You should use commands below.  Commands are:
        auth username password      Authenticate with username and password to login to the server
        put filename                Upload files to server, use "-f" to overwrite exist files
        get filename                Get file from server, use "-f" to overwrite exist files
        mkdir dirname               Create directories
        rm                          Delete files or directories, use "-f" to rm with force mode
        cd                          Change server path
        lcd                         Change local path
        pwd                         Print server path
        lpwd                        Print local path
        dir                         List files or directories of current path
        ldir                        List local files or directories of current path
        bye                         Disconnect from server
        """
        print(msg)


    def auth(self, *args):
        try:
            cmd = args[0]
            username = cmd.split()[1]
            password = cmd.split()[2]
            m = md5()
            m.update(password.encode('utf-8'))
            msg = {
                'action': 'auth',
                'username': username,
                'password': m.hexdigest()
            }
            self.client.send(json.dumps(msg).encode('utf-8'))
            rsp = self.client.recv(1024)
            code = json.loads(rsp.decode('utf-8'))['code']
            status = settings.status_code[code]['status']
            status_desc = settings.status_code[code]['desc']
            if status:
                print(status_desc)
                self.username = username
            else:
                print(status_desc)
        except IndexError:
            print('Syntax error')


    def register(self, *args):
        msg = {
            'action': 'register'
        }
        self.client.send(json.dumps(msg).encode('utf-8'))
        while True:
            try:
                rsp = json.loads(self.client.recv(1024))
                print(rsp['content'])
                code = rsp['code']
                if code == '200':
                    break
                else:
                    while True:
                        content = input('>>: ').strip()
                        if content:
                            msg = {
                                'code': '200',
                                'content': content
                            }
                            self.client.send(json.dumps(msg).encode('utf-8'))
                            break
                        else:
                            print('The input cannot be empty, please re-enter')
            except KeyboardInterrupt:
                msg = {
                    'code': '205',
                    'content': 'Reset content'
                }
                self.client.send(json.dumps(msg).encode('utf-8'))
                break


    def interactive(self):
        self.client.connect((self.server_ip, self.server_port))
        # self.auth()
        while True:
            try:
                cmd_str = input('>>: ').strip()
                if not cmd_str: continue
                cmd = cmd_str.split()[0]
                if hasattr(self, cmd):  # 使用反射，如果有该命令则调用该命令的方法，否则打印帮助
                    func = getattr(self, cmd)
                    func(cmd_str)
                else:
                    self.help()
            except KeyboardInterrupt:
                pass


    def lcd(self, *args):
        try:
            path = args[0].split()[1]
            if os.path.isabs(path):
                path = os.path.abspath(path)
            else:
                path = os.path.abspath(os.path.join(self.local_path, path))
            if os.path.isdir(path):
                self.local_path = path
            else:
                print('"{}" No such file or directory'.format(path))
        except IndexError:
            self.local_path = BASEDIR


    def lpwd(self, *args):
        print(self.local_path)


    def ldir(self, *args):
        files = os.listdir(self.local_path)
        if files:
            print('type | size | name')
            print('='.center(50,'='))
            for file in files:
                file_type = ''
                if os.path.isfile(os.path.join(self.local_path, file)):
                    file_type = 'file'
                elif os.path.isdir(os.path.join(self.local_path, file)):
                    file_type = 'dir'
                elif os.path.islink(os.path.join(self.local_path, file)):
                    file_type = 'link'
                elif os.path.ismount(os.path.join(self.local_path, file)):
                    file_type = 'mount'
                print('{} | {} | {}'.format(file_type, os.stat(os.path.join(self.local_path, file)).st_size, file))


    def put(self, *args):
        cmd = args[0].split()
        if cmd[0:2] == ['put', '-f']:
            overwrite = True
            files = cmd[2:]
        else:
            overwrite = False
            files = cmd[1:]
        if files:
            for filename in files:
                file_abs_path = os.path.join(self.local_path, filename)
                if os.path.isfile(file_abs_path):
                    fileSize = os.stat(file_abs_path).st_size
                    msg = {
                        'action': 'put',
                        'filename': filename,
                        'fileSize': fileSize,
                        'overwrite': overwrite
                    }
                    self.client.send(json.dumps(msg).encode('utf-8'))
                    rsp = json.loads(self.client.recv(1024).decode('utf-8'))  # 接收服务端返回的确认消息
                    code = rsp['code']
                    content = rsp['content']
                    if code == '202':
                        f = open(file_abs_path, 'rb')
                        m = md5()
                        for line in f:
                            m.update(line)
                            self.client.send(line)
                        f.close()
                        self.client.send(m.hexdigest().encode('utf-8'))
                        result = json.loads(self.client.recv(1024).decode('utf-8'))['content']
                        print(result)
                    elif code == '409':
                        print(content)
                    elif code == '401':
                        print(content)
                        break
                else:
                    print('"{}" dose not exist'.format(filename))
        else:
            print('Syntax error')


    def get(self, *args):
        cmd = args[0].split()
        if cmd[0:2] == ['get', '-f']:
            overwrite = True
            files = cmd[2:]
        else:
            overwrite = False
            files = cmd[1:]
        if files:
            for filename in files:
                file_abs_path = os.path.join(self.local_path, filename)
                if os.path.isfile(file_abs_path) and not overwrite:
                    print('"{}" already exist'.format(filename))
                else:
                    msg = {
                        'action': 'get',
                        'filename': filename
                    }
                    self.client.send(json.dumps(msg).encode('utf-8'))
                    rsp = json.loads(self.client.recv(1024).decode('utf-8'))
                    code = rsp['code']
                    content = rsp['content']
                    if code == '202':
                        fileSize = rsp['fileSize']
                        self.client.send('read to accept file'.encode('utf-8')) # 随便发送一个消息，防止粘包
                        m = md5()
                        received_size = 0
                        f = open(file_abs_path, 'wb')
                        while fileSize > received_size:
                            if fileSize - received_size > 1024:
                                size = 1024
                            else:
                                size = fileSize - received_size
                            data = self.client.recv(size)
                            f.write(data)
                            m.update(data)
                            received_size += len(data)
                        f.close()
                        src_md5 = self.client.recv(1024).decode()
                        dest_md5 = m.hexdigest()
                        if src_md5 == dest_md5:
                            print('"{}" get success'.format(filename))
                        else:
                            print('"{}" md5 check failed'.format(filename))
                    elif code == '401':
                        print(content)
                        break
                    else:
                        print(content)
        else:
            print('Syntax error')


    def mkdir(self, *args):
        dirname = args[0].split()[1]
        msg = {
            'action': 'mkdir',
            'dirname': dirname
        }
        self.client.send(json.dumps(msg).encode('utf-8'))
        rsp = json.loads(self.client.recv(1024).decode('utf-8'))
        content = rsp['content']
        print(content)


    def dir(self, *args):
        msg = {
            'action': 'dir'
        }
        self.client.send(json.dumps(msg).encode('utf-8'))
        rsp_size = int(self.client.recv(1024).decode('utf-8'))
        self.client.send(b'200ok')
        received_size = 0
        data = b''
        while rsp_size > received_size:
            if rsp_size - received_size > 1024:
                size = 1024
            else:
                 size = rsp_size - received_size
            data_tmp = self.client.recv(size)
            data += data_tmp
            received_size += len(data_tmp)
        print(data.decode('utf-8'))


    def rm(self, *args):
        cmd = args[0].split()
        if cmd[0:2] == ['rm', '-f']:
            force_mode = True
            files = cmd[2:]
        else:
            force_mode = False
            files = cmd[1:]
        if files:
            for file in files:
                msg = {
                    'action': 'rm',
                    'force': force_mode,
                    'file': file
                }
                self.client.send(json.dumps(msg).encode('utf-8'))
                rsp = json.loads(self.client.recv(1024).decode('utf-8'))
                if not force_mode:
                    if rsp['code'] == '100':  # 确认是否删除
                        confirm_msg = input(rsp['content'])
                        if not confirm_msg:
                            self.client.send(b'n')
                        else:
                            self.client.send(confirm_msg.encode('utf-8'))
                    elif rsp['code'] == '401':
                        print(rsp['content'])
                        break
                    else:
                        print(rsp['content'])
                else:
                    if rsp['code'] == '401':
                        print(rsp['content'])
                        break
        else:
            print('Syntax error')


    def cd(self, *args):
        cmd = args[0].split()
        if len(cmd) > 1:
            msg = {
                'action': 'cd',
                'path': cmd[1]
            }
        else:
            msg = {
                'action': 'cd',
                'path': ''
            }
        self.client.send(json.dumps(msg).encode('utf-8'))
        rsp = json.loads(self.client.recv(1024).decode('utf-8'))
        if rsp['code'] != '200':
            print(rsp['content'])


    def pwd(self, *args):
        msg = {'action': 'pwd'}
        self.client.send(json.dumps(msg).encode('utf-8'))
        print(self.client.recv(1024).decode('utf-8'))


    def bye(self, *args):
        self.client.close()
        exit()


if __name__ == '__main__':
    try:
        client = FtpClient('localhost', 10021)
        client.interactive()
    except ConnectionRefusedError as e:
        print(e)