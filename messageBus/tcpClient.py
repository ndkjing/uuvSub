"""
tcp连接接收数据
"""
# TCPclient.py

import socket
import sys
import time
import re
import config


class TcpClient:
    def __init__(self):
        self.target_host = config.server_ip  # 服务器端地址
        self.target_port = config.server_port  # 必须与服务器的端口号一致
        # self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s = None
        # 保存接收到的数据
        self.move = 0
        self.camera = 1500
        self.light = 0
        self.sonar = 0
        self.arm = 0
        self.pid_list = [0, 0, 0]
        self.mode = 0
        # 记录tcp 是否连接
        self.is_connected = 0

    def connect_server(self):
        try:
            print('(self.target_host, self.target_port)', (self.target_host, self.target_port))
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.connect((self.target_host, self.target_port))  # 尝试连接服务端
            self.is_connected = 1
        except Exception:
            print('[!] Server not found ot not open')

    def write_data(self, data):
        """
        向服务器发送数据
        """
        if isinstance(data, str):
            try:
                self.s.send(data.encode("UTF-8"))
            except ConnectionAbortedError:
                self.is_connected = 0
                return

    def start_receive(self):
        while True:
            if not self.is_connected:
                time.sleep(1)
                continue
            try:
                data = self.s.recv(1024)
            except ConnectionAbortedError:
                time.sleep(1)
                continue
            data = data.decode()
            print('recieved:', data)
            try:
                move_find = re.findall(r'move(.?)z', data)
                if len(move_find) > 0:
                    self.move = int(move_find[0])
                camera_find = re.findall(r'camera(.*?)z', data)
                if len(camera_find) > 0:
                    self.camera = int(camera_find[0])
                light_find = re.findall(r'move(.*?)z', data)
                if len(light_find) > 0:
                    self.light = int(light_find[0])
                sonar_find = re.findall(r'sonar(.?)z', data)
                if len(sonar_find) > 0:
                    self.sonar = int(sonar_find[0])
                arm_find = re.findall(r'arm(.*?)z', data)
                if len(arm_find) > 0:
                    self.arm = int(arm_find[0])
                pid_find = re.findall(r'pid(.*?)z', data)
                if len(pid_find) > 0:
                    pid_list = str(pid_find[0]).split(',')
                    for i, v in enumerate(pid_list):
                        self.pid_list[i] = float(v)
                mode_find = re.findall(r'mode(.?)z', data)
                if len(mode_find) > 0:
                    self.move = int(mode_find[0])
                print('self.move ,self.camera,self.light,self.sonar,self.arm,self.pid ,self.mode', self.move,
                      self.camera, self.light, self.sonar, self.arm, self.pid_list, self.mode)
            except Exception as e:
                print('error client recvive ', e)
            if not data:
                time.sleep(0.2)


if __name__ == '__main__':
    obj = TcpClient()
    obj.start_receive()
#
#
# import socket
# import threading
# client_list = []
# def read_server(client_socket):
#     while True:
#         content = client_socket.recv(2048).decode('UTF-8')
#         if content is not None:
#             print("content:",content)
#
# client_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
# ## 绑定USR-K7 开启的IP地址和端口号
# client_socket.connect(('192.168.0.7',23))
# threading.Thread(target=read_server,args=(client_socket,)).start()
# while True:
#     line = input('')
#     if line is None or line =='exit':
#         break
#     client_socket.send(line.encode("UTF-8"))
