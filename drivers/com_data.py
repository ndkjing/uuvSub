"""
串口数据收发
"""
import sys
import os
import re

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

sys.path.append(
    os.path.join(
        root_dir,
        'dataGetSend'))

sys.path.append(
    os.path.join(
        os.path.dirname(
            os.path.abspath(__file__)),
        'utils'))
import serial
from serial.tools import list_ports
import binascii
import time
import copy
from threading import Thread

from utils import log

logger = log.LogHandler('test_com')
ACCData = [0.0] * 8
GYROData = [0.0] * 8
AngleData = [0.0] * 8
FrameState = 0  # 通过0x后面的值判断属于哪一种情况
Bytenum = 0  # 读取到这一段的第几位
CheckSum = 0  # 求和校验位

a = [0.0] * 3
w = [0.0] * 3
Angle = [0.0] * 3


class ComData:
    def __init__(self, com, baud, timeout, logger=None):
        if logger is None:
            import logging
            logging.basicConfig(
                format='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s',
                level=logging.DEBUG)
            self.logger = logging
        else:
            self.logger = logger
        self.port = com
        self.baud = baud
        self.timeout = timeout
        try:
            # 打开串口，并得到串口对象
            self.uart = serial.Serial(
                self.port, self.baud, timeout=self.timeout)
            # 判断是否打开成功
            if not self.uart.is_open:
                self.logger.error('无法打开串口')
        except Exception as e:
            self.logger.error({"串口连接异常：": e})

    # 打印设备基本信息
    def print_info(self):
        info_dict = {
            'name': self.uart.name,  # 设备名字
            'port': self.uart.port,  # 读或者写端口
            'baudrate': self.uart.baudrate,  # 波特率
            'bytesize': self.uart.bytesize,  # 字节大小
            'parity': self.uart.parity,  # 校验位
            'stopbits': self.uart.stopbits,  # 停止位
            'timeout': self.uart.timeout,  # 读超时设置
            'writeTimeout': self.uart.writeTimeout,  # 写超时
            'xonxoff': self.uart.xonxoff,  # 软件流控
            'rtscts': self.uart.rtscts,  # 软件流控
            'dsrdtr': self.uart.dsrdtr,  # 硬件流控
            'interCharTimeout': self.uart.interCharTimeout,  # 字符间隔超时
        }
        self.logger.info(info_dict)
        return info_dict

    # 打开串口
    def open_serial(self):
        self.uart.open()

    # 关闭串口
    def close_Engine(self):
        self.uart.close()
        print(self.uart.is_open)  # 检验串口是否打开

    # 打印可用串口列表
    @staticmethod
    def print_ssed_com():
        port_list = list(list_ports.comports())
        print(port_list)

    # 接收指定大小的数据
    # 从串口读size个字节。如果指定超时，则可能在超时后返回较少的字节；如果没有指定超时，则会一直等到收完指定的字节数。
    def read_size(self, size):
        return self.uart.read(size=size)

    # 接收一行数据
    # 使用readline()时应该注意：打开串口时应该指定超时，否则如果串口没有收到新行，则会一直等待。
    # 如果没有超时，readline会报异常。
    def readline(self):
        data_read = self.uart.readline()
        return data_read
        # if str(data_read).count(',') > 2:
        #     return str(data_read)[2:-5]
        # else:
        #     return data_read

    # 发数据
    def send_data(self, data, b_hex=False):
        print('com send_data', data)
        if b_hex:
            self.uart.write(bytes.fromhex(data))
        else:
            self.uart.write(data.encode())

    # 更多示例
    # self.main_engine.write(chr(0x06).encode("utf-8"))  # 十六制发送一个数据
    # print(self.main_engine.read().hex())  #  # 十六进制的读取读一个字节
    # print(self.main_engine.read())#读一个字节
    # print(self.main_engine.read(10).decode("gbk"))#读十个字节
    # print(self.main_engine.readline().decode("gbk"))#读一行
    # print(self.main_engine.readlines())#读取多行，返回列表，必须匹配超时（timeout)使用
    # print(self.main_engine.in_waiting)#获取输入缓冲区的剩余字节数
    # print(self.main_engine.out_waiting)#获取输出缓冲区的字节数
    # print(self.main_engine.readall())#读取全部字符。

    # 接收数据
    # 一个整型数据占两个字节
    # 一个字符占一个字节

    def recive_data(self, way):
        # 循环接收数据，此为死循环，可用线程实现
        print("开始接收数据：")
        while True:
            try:
                # 一个字节一个字节的接收
                if self.uart.in_waiting:
                    if (way == 0):
                        for i in range(self.uart.in_waiting):
                            print("接收ascii数据：" + str(self.read_size(1)))
                            data1 = self.read_size(1).hex()  # 转为十六进制
                            data2 = int(
                                data1, 16)  # 转为十进制print("收到数据十六进制："+data1+"  收到数据十进制："+str(data2))
                    if (way == 1):
                        # 整体接收
                        # data =
                        # self.main_engine.read(self.main_engine.in_waiting).decode("utf-8")#方式一
                        data = self.uart.read_all()  # 方式二print("接收ascii数据：", data)
            except Exception as e:
                print("异常报错：", e)

    def get_laser_data(self):
        data = self.read_size(30)
        # print(time.time(), type(data), data)
        str_data = str(binascii.b2a_hex(data))[2:-1]
        # print(str_data)
        for i in str_data.split('aa'):
            if len(i) == 14 and i.startswith('55'):
                # print(i)
                distance = int(i[6:12], 16) / 1000
                return distance

    def get_weite_imu_data(self):
        data_weite_imu = self.read_size(33)

        def DueData(inputdata):  # 新增的核心程序，对读取的数据进行划分，各自读到对应的数组里
            global FrameState  # 在局部修改全局变量，要进行global的定义
            global Bytenum
            global CheckSum
            global a
            global w
            global Angle
            for data in inputdata:  # 在输入的数据进行遍历
                # Python2软件版本这里需要插入 data = ord(data)*****************************************************************************************************
                if FrameState == 0:  # 当未确定状态的时候，进入以下判断
                    if data == 0x55 and Bytenum == 0:  # 0x55位于第一位时候，开始读取数据，增大bytenum
                        CheckSum = data
                        Bytenum = 1
                        continue
                    elif data == 0x51 and Bytenum == 1:  # 在byte不为0 且 识别到 0x51 的时候，改变frame
                        CheckSum += data
                        FrameState = 1
                        Bytenum = 2
                    elif data == 0x52 and Bytenum == 1:  # 同理
                        CheckSum += data
                        FrameState = 2
                        Bytenum = 2
                    elif data == 0x53 and Bytenum == 1:
                        CheckSum += data
                        FrameState = 3
                        Bytenum = 2
                elif FrameState == 1:  # acc    #已确定数据代表加速度

                    if Bytenum < 10:  # 读取8个数据
                        ACCData[Bytenum - 2] = data  # 从0开始
                        CheckSum += data
                        Bytenum += 1
                    else:
                        if data == (CheckSum & 0xff):  # 假如校验位正确
                            a = get_acc(ACCData)
                        CheckSum = 0  # 各数据归零，进行新的循环判断
                        Bytenum = 0
                        FrameState = 0
                elif FrameState == 2:  # gyro

                    if Bytenum < 10:
                        GYROData[Bytenum - 2] = data
                        CheckSum += data
                        Bytenum += 1
                    else:
                        if data == (CheckSum & 0xff):
                            w = get_gyro(GYROData)
                        CheckSum = 0
                        Bytenum = 0
                        FrameState = 0
                elif FrameState == 3:  # angle

                    if Bytenum < 10:
                        AngleData[Bytenum - 2] = data
                        CheckSum += data
                        Bytenum += 1
                    else:
                        if data == (CheckSum & 0xff):
                            Angle = get_angle(AngleData)
                            d = a + w + Angle
                            print(
                                "a(g):%10.3f %10.3f %10.3f w(deg/s):%10.3f %10.3f %10.3f Angle(deg):%10.3f %10.3f %10.3f" % d)
                        CheckSum = 0
                        Bytenum = 0
                        FrameState = 0

        def get_acc(datahex):
            axl = datahex[0]
            axh = datahex[1]
            ayl = datahex[2]
            ayh = datahex[3]
            azl = datahex[4]
            azh = datahex[5]

            k_acc = 16.0

            acc_x = (axh << 8 | axl) / 32768.0 * k_acc
            acc_y = (ayh << 8 | ayl) / 32768.0 * k_acc
            acc_z = (azh << 8 | azl) / 32768.0 * k_acc
            if acc_x >= k_acc:
                acc_x -= 2 * k_acc
            if acc_y >= k_acc:
                acc_y -= 2 * k_acc
            if acc_z >= k_acc:
                acc_z -= 2 * k_acc

            return acc_x, acc_y, acc_z

        def get_gyro(datahex):
            wxl = datahex[0]
            wxh = datahex[1]
            wyl = datahex[2]
            wyh = datahex[3]
            wzl = datahex[4]
            wzh = datahex[5]
            k_gyro = 2000.0

            gyro_x = (wxh << 8 | wxl) / 32768.0 * k_gyro
            gyro_y = (wyh << 8 | wyl) / 32768.0 * k_gyro
            gyro_z = (wzh << 8 | wzl) / 32768.0 * k_gyro
            if gyro_x >= k_gyro:
                gyro_x -= 2 * k_gyro
            if gyro_y >= k_gyro:
                gyro_y -= 2 * k_gyro
            if gyro_z >= k_gyro:
                gyro_z -= 2 * k_gyro
            return gyro_x, gyro_y, gyro_z

        def get_angle(datahex):
            rxl = datahex[0]
            rxh = datahex[1]
            ryl = datahex[2]
            ryh = datahex[3]
            rzl = datahex[4]
            rzh = datahex[5]
            k_angle = 180.0

            angle_x = (rxh << 8 | rxl) / 32768.0 * k_angle
            angle_y = (ryh << 8 | ryl) / 32768.0 * k_angle
            angle_z = (rzh << 8 | rzl) / 32768.0 * k_angle
            if angle_x >= k_angle:
                angle_x -= 2 * k_angle
            if angle_y >= k_angle:
                angle_y -= 2 * k_angle
            if angle_z >= k_angle:
                angle_z -= 2 * k_angle

            return angle_x, angle_y, angle_z

        DueData(data)

    def read_deep(self, debug=False):
        """
        获取深度传感器数据
        return  [温度，深度]
        """
        data1 = self.readline()
        time.sleep(0.9)
        str_data = bytes(data1).decode('ascii')
        str_data = str_data.strip()
        t_list = re.findall(r'(..\...) deg', str_data)
        d_list = re.findall(r'(.\...) m$', str_data)
        r_t = None
        r_d = None
        if len(t_list) > 0:
            r_t = float(t_list[0])
        if len(d_list) > 0:
            r_d = float(d_list[0])
        if debug:
            print('data1', data1)
            print('str_data', str_data)
            print('r_t', r_t)
            print('r_d', r_d)
        return [r_t, r_d]


if __name__ == '__main__':
    import config

    b_imu_compass = 0
    b_deep = 1
    check_type = input('check_type: 1 imu_compass  2 deep   >')
    if int(check_type) == 1:
        b_imu_compass = 1
    elif int(check_type) == 2:
        b_deep = 1

    if b_imu_compass:
        serial_obj = ComData('com0',
                             '9600',
                             timeout=0.7,
                             logger=logger)
        while True:
            data = serial_obj.read_size(4)
            # print(time.time(),type(data),data)
            str_data = str(binascii.b2a_hex(data))[2:-1]
            # print(str_data)
            print(int(str_data[2:-2], 16) / 1000)
    elif b_deep:
        serial_obj = ComData(config.arduino_com,
                             config.arduino_baud,
                             timeout=1,
                             logger=logger)
        while True:
            data1 = serial_obj.readline()
            str_data1 = bytes(data1).decode('ascii')
            print('data1', data1)
            print('str_data1', str_data1)
            time.sleep(0.9)

    # str_data = data.decode('ascii')[:-3]
    # # print('str_data',str_data,type(str_data))
    # if len(str_data)<2:
    #     continue
    # # str_data = str_data.encode('utf8')
    # # print(str_data.split('.'))
    # float_data = float(str_data)
    # print(time.time(),'float_data', float_data,type(float_data))
    # time.sleep(0.1)
    # t1 = Thread(target=get_com_data)
    # t2 = Thread(target=send_com_data)
    # t1.start()
    # t2.start()
    # t1.join()
    # t2.join()
    # print(str(obj.Read_Line())[2:-5])
