import time
import pigpio
import os
import sys
import binascii
import config

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

sys.path.append(
    os.path.join(
        root_dir,
        'dataGetSend'))
sys.path.append(
    os.path.join(
        root_dir,
        'utils'))
sys.path.append(
    os.path.join(
        root_dir,
        'piControl'))

ACCData = [0.0] * 8
GYROData = [0.0] * 8
AngleData = [0.0] * 8
FrameState = 0  # 通过0x后面的值判断属于哪一种情况
Bytenum = 0  # 读取到这一段的第几位
CheckSum = 0  # 求和校验位

a = [0.0] * 3
w = [0.0] * 3
Angle = [0.0] * 3


class PiSoftuart(object):
    def __init__(self, pi, rx_pin, tx_pin, baud, time_out=0.1):
        self._rx_pin = rx_pin
        self._tx_pin = tx_pin
        self.baud = baud
        self._pi = pi
        self._pi.set_mode(self._rx_pin, pigpio.INPUT)
        self._pi.set_mode(self._tx_pin, pigpio.OUTPUT)
        self.distance = 0
        # ATTR
        self._thread_ts = time_out
        self.flushInput()
        self.last_send = None

    def flushInput(self):
        pigpio.exceptions = False  # fatal exceptions off (so that closing an unopened gpio doesn't error)
        self._pi.bb_serial_read_close(self._rx_pin)
        pigpio.exceptions = True
        # self._pi.bb_serial_read_open(self._rx_pin, config.ultrasonic_baud,
        #                              8)  # open a gpio to bit bang read, 1 byte each time.
        self._pi.bb_serial_read_open(self._rx_pin, self.baud,
                                     8)  # open a gpio to bit bang read, 1 byte each time.

    def read_ultrasonic(self, len_data=None):
        if len_data is None:
            len_data = 4
            try:
                time.sleep(self._thread_ts / 2)
                count, data = self._pi.bb_serial_read(self._rx_pin)
                print(time.time(), 'count', count, 'data', data)
                if count == len_data:
                    str_data = str(binascii.b2a_hex(data))[2:-1]
                    distance = int(str_data[2:-2], 16) / 1000
                    # print(time.time(),'distance',distance)
                    # 太近进入了盲区 返回 -1
                    if distance <= 0.25:
                        return -1
                    else:
                        return distance
                elif count > len_data:
                    str_data = str(binascii.b2a_hex(data))[2:-1]
                    # print('str_data', str_data)
                    print(r'str_data.split', str_data.split('ff'))
                    # print(r'str_data.split', int(str_data.split('ff')[0][:4], 16))
                    distance = 0
                    for i in str_data.split('ff'):
                        if i:
                            distance = int(i[:4], 16) / 1000
                    # print(str_data.split('ff')[0][:4])
                    if distance <= 0.25:
                        return -1
                    else:
                        return distance
                time.sleep(self._thread_ts)
            except Exception as e:
                print({'error': e})
                time.sleep(self._thread_ts / 2)
                return None

    def read_compass(self, send_data='31', len_data=None, debug=False):
        if len_data is None:
            len_data = 4
            try:
                self.write_data(send_data)
                time.sleep(self._thread_ts)
                count, data = self._pi.bb_serial_read(self._rx_pin)
                if debug:
                    print(time.time(), 'count', count, 'data', data)
                if count > len_data:
                    str_data = data.decode('utf-8')[2:-1]
                    theta = float(str_data)
                    return 360 - theta
            except Exception as e:
                print({'error read_compass': e})
                return None

    def read_weite_compass(self, send_data=None, len_data=None, debug=False):
        if len_data is None:
            len_data = 4
            try:
                if send_data:
                    print('send_data', send_data)
                    self.write_data(send_data)
                time.sleep(self._thread_ts)
                time.sleep(0.1)
                count, data1 = self._pi.bb_serial_read(self._rx_pin)
                time.sleep(0.1)
                count, data2 = self._pi.bb_serial_read(self._rx_pin)
                time.sleep(0.1)
                count, data3 = self._pi.bb_serial_read(self._rx_pin)
                if debug:
                    print('send_data', send_data)
                    print('self._rx_pin', self._rx_pin, self.baud)
                    print(time.time(), 'count', count, 'data', data1, 'data2', data2, 'data3', data3)
                if count > len_data:
                    str_data = data1.decode('utf-8')[2:-1]
                    theta = float(str_data)
                    return 360 - theta
                # time.sleep(self._thread_ts)
            except Exception as e:
                print({'error read_compass': e})
                return None

    def read_gps(self, len_data=None, debug=False):
        if len_data is None:
            len_data = 4
            try:
                count, data = self._pi.bb_serial_read(self._rx_pin)
                if debug:
                    print(time.time(), 'count', count, 'data', data)
                if count > len_data:
                    str_data = data.decode('utf-8', errors='ignore')
                    for i in str_data.split('$'):
                        i = i.strip()
                        if i.startswith('GPGGA') or i.startswith('$GPGGA') or i.startswith('GNGGA') or i.startswith(
                                '$GNGGA'):
                            gps_data = i
                            data_list = gps_data.split(',')
                            if len(data_list) < 8:
                                continue
                            if data_list[2] and data_list[4]:
                                lng, lat = round(float(data_list[4][:3]) +
                                                 float(data_list[4][3:]) /
                                                 60, 6), round(float(data_list[2][:2]) +
                                                               float(data_list[2][2:]) /
                                                               60, 6)
                                if lng < 1 or lat < 1:
                                    pass
                                else:
                                    lng_lat_error = float(data_list[8])
                                    return [lng, lat, lng_lat_error]
                time.sleep(self._thread_ts * 10)
            except Exception as e:
                print({'error read_gps': e})
                return None

    def read_laser(self, send_data=None):
        try:
            if send_data:
                self.write_data(send_data, baud=115200)
                time.sleep(self._thread_ts * 4)
            count, data = self._pi.bb_serial_read(self._rx_pin)
            # print(time.time(), type(data), count, data)
            if count == 0:
                time.sleep(1 / config.laser_hz)
                return 0
            str_data = str(binascii.b2a_hex(data))[2:-1]
            # print('str_data', str_data, 'len(str_data)', len(str_data))
            for i in str_data.split('aa'):
                if len(i) == 14 and '07' in i:
                    distance = int(i[6:12], 16) / 1000
                    # 超出量程返回None
                    if distance > 40:
                        return 0
                        # print(time.time(), type(data), count, data)
                        # print(str_data)
                    return distance
            time.sleep(1 / config.laser_hz)
        except Exception as e:
            time.sleep(1 / config.laser_hz)
            print({'error read_laser': e})
            return 0

    def read_sonar(self):
        len_data = 10
        try:
            time.sleep(self._thread_ts / 2)
            count, data = self._pi.bb_serial_read(self._rx_pin)
            print(time.time(), 'count', count, 'data', data)
            if count == len_data:
                str_data = str(binascii.b2a_hex(data))[2:-1]
                distance = int(str_data[2:-2], 16) / 1000
                # print(time.time(),'distance',distance)
                # 太近进入了盲区 返回 -1
                if distance <= 0.25:
                    return -1
                else:
                    return distance
            elif count > len_data:
                str_data = str(binascii.b2a_hex(data))[2:-1]
                # print('str_data', str_data)
                print(r'str_data.split', str_data.split('ff'))
                # print(r'str_data.split', int(str_data.split('ff')[0][:4], 16))
                distance = 0
                for i in str_data.split('ff'):
                    if i:
                        distance = int(i[:4], 16) / 1000
                # print(str_data.split('ff')[0][:4])
                if distance <= 0.25:
                    return -1
                else:
                    return distance
            time.sleep(self._thread_ts)
        except Exception as e:
            print({'error': e})
            time.sleep(self._thread_ts / 2)
            return None

    def pin_stc_read(self, debug=False):
        """
        软串口单片机数据读取
        :return:
        """
        count, data = self._pi.bb_serial_read(self._rx_pin)
        if debug:
            print(time.time(), 'count', count, 'data', data)

    def pin_stc_write(self, stc_write_data, debug=False):
        """
        软串口单片机数据发送
        :param stc_write_data:
        :param debug
        :return:
        """
        str_16_stc_write_data = str(binascii.b2a_hex(stc_write_data.encode('utf-8')))[2:-1]  # 字符串转16进制字符串
        self.write_data(str_16_stc_write_data, baud=self.baud, debug=debug)

    def read_remote_control(self, len_data=None, debug=False):
        """
        读取自己做的lora遥控器数据
        :param len_data:限制接受数据最短长度
        :param debug:是否是调试  调试则print打印输出数据
        :return:
        """
        if len_data is None:
            try:
                # 发送数据让遥控器接受变为绿灯
                s = 'S9'
                str_16 = str(binascii.b2a_hex(s.encode('utf-8')))[2:-1]  # 字符串转16进制字符串
                # str_16 = '41305a'
                if self.last_send is None:
                    self.write_data(str_16, baud=self.baud, debug=debug)
                    self.last_send = time.time()
                else:
                    if time.time() - self.last_send > 1:
                        self.write_data(str_16, baud=self.baud, debug=debug)
                        self.last_send = time.time()
                count, data = self._pi.bb_serial_read(self._rx_pin)
                if debug:
                    print(time.time(), 'count', count, 'data', data)
                if count > 40:
                    str_data = str(data, encoding="utf8")
                    data_list = str_data.split(r'\r\nZ')
                    if debug:
                        print(time.time(), 'str_data', str_data, 'data_list', data_list)
                    for item in data_list:
                        temp_data = item.strip()
                        if temp_data[0] == 'A' and temp_data[-1] == 'Z':
                            item_data = temp_data[1:-1]
                            item_data_list = item_data.split(',')
                            if len(item_data_list) >= 13:
                                left_row = int(item_data_list[1])
                                left_col = int(item_data_list[0])
                                right_row = int(item_data_list[3])
                                right_col = int(item_data_list[2])
                                fine_tuning = int(item_data_list[4])
                                button_10 = int(item_data_list[9])
                                button_11 = int(item_data_list[10])
                                button_12 = int(item_data_list[11])
                                button_13 = int(item_data_list[12])
                                lever_6 = int(item_data_list[5])
                                lever_7 = int(item_data_list[6])
                                lever_8 = int(item_data_list[7])
                                lever_9 = int(item_data_list[8])
                                return [left_col,
                                        left_row,
                                        right_col,
                                        right_row,
                                        fine_tuning,
                                        lever_6,
                                        lever_7,
                                        lever_8,
                                        lever_9,
                                        button_10,
                                        button_11,
                                        button_12,
                                        button_13,
                                        ]

                time.sleep(self._thread_ts)
            except Exception as e:
                time.sleep(self._thread_ts)
                print({'error read_remote_control': e})
                return None

    def write_data(self, msg, baud=None, debug=False):
        if debug:
            print('send data', msg)
        self._pi.wave_clear()
        if baud:
            self._pi.wave_add_serial(self._tx_pin, baud, bytes.fromhex(msg))
        else:
            self._pi.wave_add_serial(self._tx_pin, 9600, bytes.fromhex(msg))
        data = self._pi.wave_create()
        self._pi.wave_send_once(data)
        if self._pi.wave_tx_busy():
            pass
        self._pi.wave_delete(data)

    def set_thread_ts(self, thread_ts):
        self._thread_ts = thread_ts

    def get_thread_ts(self):
        return self._thread_ts

    def read_millimeter_wave(self, len_data=None, debug=False):
        if len_data is None:
            len_data = 4
            try:
                time.sleep(self._thread_ts)
                count, data = self._pi.bb_serial_read(self._rx_pin)
                if debug:
                    print(time.time(), 'count', count, 'data', data)
                if count > len_data:
                    str_data = str(binascii.b2a_hex(data))[2:-1]
                    split_str = 'aaaa'
                    data_dict = {}
                    for i in str_data.split(split_str):
                        if i.startswith('0c07'):
                            index = int(i[4:6], 16)
                            distance = 0.01 * (int(i[8:10], 16) * 256 + int(i[10:12], 16))
                            angle = 2 * int(i[12:14], 16) - 90
                            speed = 0.05 * (int(i[14:16], 16) * 256 + int(i[16:18], 16)) - 35
                            data_dict.update({index: [distance, angle, speed]})
                            # print('distance:{},angle:{},speed:{}'.format(distance,angle,speed))
                    return data_dict
                else:
                    return None
            except Exception as e:
                # print({'read_millimeter_wave':e})
                time.sleep(self._thread_ts)
                return None

    def send_stc_data(self, send_data):
        try:
            self.pin_stc_write(send_data)
            time.sleep(self._thread_ts)
            return None
            # time.sleep(self._thread_ts)
        except Exception as e:
            print({'error send_stc_data': e})
            return None

    def read_stc_data(self, debug=False):
        try:
            count, data = self._pi.bb_serial_read(self._rx_pin)
            if debug:
                print(count, data, )
            if count > 4:
                str_data = data.decode('utf-8')[0:-1]
                if debug:
                    print('str_data', str_data, str_data.startswith('G'))
                # 返回电量
                if str_data.startswith('G'):
                    int_data = int(str_data[1:5])
                    if debug:
                        print('[int_data]', [int_data])
                    return [int_data]
            # time.sleep(self._thread_ts * 10)
        except Exception as e:
            print({'error read_stc_data': e})
            return None

    def read_weite_imu_data(self, debug=False):
        time.sleep(self._thread_ts)
        count, data = self._pi.bb_serial_read(self._rx_pin)
        if debug:
            print(time.time(), 'len,data', len(data), data)
            print('str_data', str(binascii.b2a_hex(data))[2:-1])

        def DueData(inputdata):  # 新增的核心程序，对读取的数据进行划分，各自读到对应的数组里
            angle_x = None
            angle_y = None
            angle_z = None
            global FrameState  # 在局部修改全局变量，要进行global的定义
            global Bytenum
            global CheckSum
            global a
            global w
            global Angle
            for data in inputdata:  # 在输入的数据进行遍历
                try:
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
                                # d = a + w + Angle
                                # d = a + w + Angle
                                # print('a',a,'w',w,'angle',Angle)
                                if len(Angle) == 3 and isinstance(Angle[2], float):
                                    angle_x = round(Angle[0], 1)
                                    angle_y = round(Angle[1], 1)
                                    angle_z = round(Angle[2], 1)
                                # print(
                                #     "a(g):%10.3f %10.3f %10.3f w(deg/s):%10.3f %10.3f %10.3f Angle(deg):%10.3f %10.3f %10.3f" % d)
                            CheckSum = 0
                            Bytenum = 0
                            FrameState = 0
                except Exception as e:
                    print('parser imu error', e)
            return [angle_x,angle_y,angle_z]

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

            return [angle_x, angle_y, angle_z]

        angle_z = DueData(data)
        return angle_z
        # print('angle_z', angle_z)


if __name__ == '__main__':
    pass
