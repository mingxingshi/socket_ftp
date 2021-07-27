#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author  :  smx
@file    :  main.py
@time    :  2021/7/14 15:56
"""


import socketserver
import json
import os, sys
import logging
from hashlib import md5
import shutil

BASEDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASEDIR)
from conf import settings

logging.basicConfig(level = logging.DEBUG,format = '%(asctime)s | %(name)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)


class FtpServer(socketserver.BaseRequestHandler):
    current_path = ''
    userHome = ''
    login_status = False


    def handle(self):
        while True:
            try:
                data = json.loads(self.request.recv(1024).strip().decode('utf-8'))
                # if not self.login_status:
                #     self.auth(data)
                action = data['action']
                if hasattr(self, action):
                    func = getattr(self, action)
                    func(data)
            except ConnectionResetError:
                logger.warning('{}|{}|disconnected'.format(self.client_address[0], self.client_address[1]))
                break
            except json.decoder.JSONDecodeError:
                logger.info('{}|{}|disconnected'.format(self.client_address[0], self.client_address[1]))
                break


    def register(self, *args):
        while True:
            msg1 = {'code': '100.1', 'content': settings.status_code['100.1']['desc']}
            self.request.send(json.dumps(msg1).encode('utf-8'))
            rsp1 = json.loads(self.request.recv(1024).strip().decode('utf-8'))
            if rsp1['code'] == '200':
                username = rsp1['content']
                if os.path.isfile(os.path.join(os.path.join(BASEDIR, 'data'), '{}.json'.format(username))):
                    msg2 = {'code': '409', 'content': 'Username already exist'}
                    self.request.send(json.dumps(msg2).encode('utf-8'))
                    continue
                while True:
                    msg3 = {'code': '100.2', 'content': settings.status_code['100.2']['desc']}
                    self.request.send(json.dumps(msg3).encode('utf-8'))
                    rsp2 = json.loads(self.request.recv(1024).strip().decode('utf-8'))
                    if rsp2['code'] == '200':
                        password1 = rsp2['content']
                        msg4 = {'code': '100.3', 'content': settings.status_code['100.3']['desc']}
                        self.request.send(json.dumps(msg4).encode('utf-8'))
                        rsp3 = json.loads(self.request.recv(1024).strip().decode('utf-8'))
                        if rsp3['code'] == '200':
                            password2 = rsp3['content']
                            if password1 == password2:
                                m = md5()
                                m.update(password1.encode('utf-8'))
                                userHome = os.path.join(os.path.join(BASEDIR, 'users'), username)
                                try:
                                    os.makedirs(userHome)
                                except FileExistsError:
                                    pass
                                userInfo = {'username': username, 'password': m.hexdigest(), 'userHome': userHome}
                                f = open(os.path.join(os.path.join(BASEDIR, 'data'), '{}.json'.format(username)), 'w')
                                json.dump(userInfo, f)
                                msg5 = {'code': '200', 'content': 'user [{}] registered'.format(username)}
                                logger.info('{}|200|user [{}] registered'.format(username, username))
                                self.request.send(json.dumps(msg5).encode('utf-8'))
                                f.flush()
                                f.close()
                                break
                            else:
                                continue
                        else:
                            break
                    else:
                        break
            else:
                break


    def auth(self, *args):
        data = args[0]
        username = data['username']
        password = data['password']
        if not os.path.isfile(os.path.join(os.path.join(BASEDIR, 'data'), '{}.json'.format(username))):
            code = '404.0'
            status_desc = settings.status_code[code]['desc']
            logger.error('{}|{}|{}'.format(username, code, status_desc))
        else:
            f = open(os.path.join(os.path.join(BASEDIR, 'data'), '{}.json'.format(username)), 'r')
            userInfo = json.load(f)
            if password == userInfo['password']:
                code = '200'
                status_desc = settings.status_code[code]['desc']
                self.current_path = userInfo['userHome']
                self.userHome = userInfo['userHome']
                self.login_status = True
                logger.info('{}|auth|{}|{}'.format(username, code, status_desc))
            else:
                code = '401'
                status_desc = settings.status_code[code]['desc']
                logger.error('{}|auth|{}|{}'.format(username, code, status_desc))
        msg = {'code': code}
        self.request.send(json.dumps(msg).encode('utf-8'))


    def dir(self, *args):
        files = os.listdir(self.current_path)
        if files:
            msg = 'type | size | name\n' + '='.center(50, '=') + '\n'
            for file in files:
                file_type = ''
                if os.path.isfile(os.path.join(self.current_path, file)):
                    file_type = 'file'
                elif os.path.isdir(os.path.join(self.current_path, file)):
                    file_type = 'dir'
                elif os.path.islink(os.path.join(self.current_path, file)):
                    file_type = 'link'
                elif os.path.ismount(os.path.join(self.current_path, file)):
                    file_type = 'mount'
                msg += ('{} | {} | {}\n'.format(file_type, os.stat(os.path.join(self.current_path, file)).st_size, file))
            msg = msg.rstrip('\n').encode('utf-8')
        else:
            msg = '\n'.encode('utf-8')
        self.request.send(str(len(msg)).encode('utf-8'))
        self.request.recv(1024)  # 接收确认消息，防止粘包
        self.request.send(msg)


    def rm(self, *args):
        data = args[0]
        force = data['force']
        files = data['files']
        for file in files:
            file_path = os.path.join(self.current_path, file)
            if os.path.isfile(file_path):
                if force:
                    os.remove(file_path)
                else:
                    msg = {'code': '100', 'content': 'Delete normal file "{}"? '.format(file)}
                    self.request.send(json.dumps(msg).encode('utf-8'))
                    if self.request.recv(1024).decode('utf-8') in ['y', 'yes']:
                        os.remove(file_path)
                    else:
                        continue
            elif os.path.isdir(file_path):
                if force:
                    shutil.rmtree(file_path)
                else:
                    msg = {'code': '100', 'content': 'Delete directory "{}"? '.format(file)}
                    self.request.send(json.dumps(msg).encode('utf-8'))
                    if self.request.recv(1024).decode('utf-8').strip() in ['y', 'yes']:
                        shutil.rmtree(file_path)
                    else:
                        continue
        self.request.send(json.dumps({'code': '226'}).encode('utf-8'))


    def mkdir(self, *args):
        data = args[0]
        dirname = data['dirname']
        if os.path.isdir(os.path.join(self.current_path, dirname)):
            msg = {'code': '409', 'content': '"{}" already exist'.format(dirname)}
        else:
            os.mkdir(os.path.join(self.current_path, dirname))
            msg = {'code': '200', 'content': 'success'}
        self.request.send(json.dumps(msg).encode('utf-8'))


    def cd(self, *args):
        data = args[0]
        path = data['path']
        if path:
            current_path_tmp = os.path.abspath(os.path.join(self.current_path, path))
        else:
            current_path_tmp = self.userHome
        msg = {}
        if current_path_tmp.startswith(self.userHome):
            if os.path.isdir(current_path_tmp):
                self.current_path = current_path_tmp
                msg = {'code': '200', 'content': 'success'}
            elif os.path.isfile(current_path_tmp):
                msg = {'code': '400', 'content': '"{}" Not a directory'.format(path)}
            elif not os.path.exists(current_path_tmp):
                msg = {'code': '400', 'content': '"cd {}" : no such file or directory'.format(path)}
        else:
            msg = {'code': '401', 'content': 'Permission denied'}
        self.request.send(json.dumps(msg).encode('utf-8'))


    def pwd(self, *args):
        path = self.current_path.replace(os.path.commonprefix([self.current_path, os.path.dirname(self.userHome)]), '', 1)
        self.request.send(path.encode('utf-8'))


    def put(self, *args):
        cmd = args[0]
        filename = cmd['filename']
        fileSize = cmd['fileSize']
        overwrite = cmd['overwrite']
        if os.path.isfile(os.path.join(self.current_path, filename)) and not overwrite:
            msg = {'code': '409', 'content': '"{}" already exist'.format(filename)}
            self.request.send(json.dumps(msg).encode('utf-8'))
        else:
            msg = {'code': '202', 'content': 'ready to accept file'}
            self.request.send(json.dumps(msg).encode('utf-8'))
            received_size = 0
            m = md5()
            f = open(os.path.join(self.current_path, filename), 'wb')
            while received_size < fileSize:
                if fileSize - received_size > 1024:
                    size = 1024
                else:
                    size = fileSize - received_size
                data = self.request.recv(size)
                f.write(data)
                m.update(data)
                received_size += len(data)
            f.close()
            src_md5 = self.request.recv(1024).decode('utf-8')
            dest_md5 = m.hexdigest()
            if src_md5 == dest_md5:
                msg = {'code': '200', 'content': '"{}" put success'.format(filename)}
            else:
                msg = {'code': '410', 'content': '"{}" md5 check failed'.format(filename)}
            self.request.send(json.dumps(msg).encode('utf-8'))


    def get(self, *args):
        cmd = args[0]
        filename = cmd['filename']
        file_abs_path = os.path.join(self.current_path, filename)
        if os.path.isfile(file_abs_path):
            fileSize = os.stat(file_abs_path).st_size
            msg = {'code': '202', 'content': 'ready to send file', 'fileSize': fileSize}
            self.request.send(json.dumps(msg).encode('utf-8'))
            self.request.recv(1024) # 接收客户端的确认消息，防止粘包
            m = md5()
            f = open(file_abs_path, 'rb')
            for line in f:
                m.update(line)
                self.request.send(line)
            f.close()
            self.request.send(m.hexdigest().encode('utf-8'))
        else:
            msg = {'code': '404', 'content': '"{}" file dose not exist'.format(filename)}
            self.request.send(json.dumps(msg).encode('utf-8'))


if __name__ == '__main__':
    host, port = 'localhost', 10021
    server = socketserver.ThreadingTCPServer((host, port), FtpServer)  # 多线程
    # server = socketserver.ForkingTCPServer((host, port), FtpServer) # 多进程，无法在windows使用，因为windows上的os模块没有fork方法
    logger.info('ftp server started')
    server.serve_forever()
