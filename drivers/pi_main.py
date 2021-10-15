import os
import sys
import threading
import pigpio
import time

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)
from utils import log
from drivers import pi_softuart
import config
from moveControl import simple_pid
from drivers import com_data

logger = log.LogHandler('pi_log')
"""
行 为八个电机运动力 -1 为吸  1 为推   其中 5 8并联   6 7 并联
列为9种运动  0：停止
            1：前进
            2：后退
            3：左转
            4：右转
            5：上升
            6：下降
            7: 左移
            8: 右移
电机正反桨也
绿色：>1500推，<1500吸（1,2,5,8）
蓝色：>1500吸，<1500推（3,4,6,7）
    
"""
move_force = [
    [0, 0, 0, 0, 0, 0],
    [-1, -1, -1, 1, 0, 0],
    [1, 1, 1, -1, 0, 0],
    [1, -1, 1, -1, 0, 0],
    [-1, 1, -1, 1, 0, 0],
    [0, 0, 0, 0, -1, -1],
    [0, 0, 0, 0, 1, 1],
    [1, -1, -1, 1, 0, 0],
    [-1, 1, 1, -1, 0, 0],
]
cw_list = [3, 4, 6, 7]  # 反桨叶大于1500 吸
ccw_list = [1, 2, 5, 8]  # 正桨叶 大于1500 推


class PiMain:
    def __init__(self, logger_=None):
        if logger_ is not None:
            self.logger_obj = logger_
        else:
            self.logger_obj = logger
        # 树莓派pwm波控制对象 1 2 3 4 5 6 7 8  8个电机pwm值
        self.current_pwm_list = [config.stop_pwm] * 8
        self.target_pwm_list = [config.stop_pwm] * 8
        self.pice = 20000
        self.diff = int(20000 / self.pice)
        self.hz = 50
        self.pi = pigpio.pi()
        # gpio脚的编号顺序依照Broadcom number顺序，请自行参照gpio引脚图里面的“BCM编码”，
        for motor_pin in config.motor_pin_list:
            self.pi.set_PWM_frequency(motor_pin, self.hz)  # 设定左侧电机引脚产生的pwm波形的频率为50Hz
            self.pi.set_PWM_range(motor_pin, self.pice)
        self.imu_compass_obj = self.get_imu_compass_obj()
        self.deep_obj = None
        if os.path.exists(config.arduino_com):
            self.deep_obj = PiMain.get_com_obj(port=config.arduino_com,
                                               baud=config.arduino_baud,
                                               timeout=config.arduino_timeout)
        # 罗盘角度
        self.theta_z = 0  # z轴角度
        self.theta_list = [0,0,0]  # 依次放 x,y,z 角度
        self.last_theta = 0
        # 深度
        self.deep = 0
        # 温度
        self.temperature = 0
        # 仓压
        self.press = 0
        # 是否漏水
        self.is_leak_water = 0
        # 灯
        self.is_big_light = 0
        # 声呐
        self.is_sonar = 0
        # 摄像头角度
        self.camera_angle_pwm = 1500
        # 机械臂
        self.arm_pwm = 1500
        # 动力占比 %
        self.speed = 40

    # 获取串口对象
    @staticmethod
    def get_com_obj(port, baud, logger_=None, timeout=0.4):
        return com_data.ComData(
            port,
            baud,
            timeout=timeout,
            logger=logger_)

    def get_imu_compass_obj(self):
        return pi_softuart.PiSoftuart(pi=self.pi, rx_pin=config.pin_imu_compass_rx, tx_pin=config.pin_imu_compass_tx,
                                      baud=config.pin_imu_compass_baud, time_out=0.1)

    # 罗盘角度滤波
    def compass_filter(self, theta_):
        current_time = time.time()
        if theta_:
            if len(self.theta_list) >= 20:
                self.theta_list.pop(0)
            self.theta_list.append((current_time, theta_))
            if len(self.theta_list) >= 4:
                self.angular_velocity = round((self.theta_list[-1][1] - self.theta_list[-4][1]) / (
                        self.theta_list[-1][0] - self.theta_list[-4][0]), 1)
                self.last_angular_velocity = self.angular_velocity
            if not self.last_theta:
                self.last_theta = theta_
                return_theta = theta_
            else:
                if abs(theta_ - self.last_theta) > 180:
                    return_theta = self.last_theta
                else:
                    self.last_theta = theta_
                    return_theta = theta_
                self.last_theta = theta_
        else:
            self.angular_velocity = self.last_angular_velocity
            return_theta = self.last_theta
        return return_theta

    def move(self, move_type=0):
        """
        前进
        :param move_type 运动方向
        0：停止
        1：前进
        2：后退
        3：左转
        4：右转
        5：上升
        6：下降
        7: 左移
        8: 右移
        """
        output_pwm = []
        delta_pwm = int(config.speed_grade) * 100
        for index, force in enumerate(move_force[move_type]):
            if force == 1:
                if index in cw_list:
                    output_pwm.append(config.stop_pwm - delta_pwm)
                else:
                    output_pwm.append(config.stop_pwm + delta_pwm)
            elif force == -1:
                if index in cw_list:
                    output_pwm.append(config.stop_pwm + delta_pwm)
                else:
                    output_pwm.append(config.stop_pwm - delta_pwm)
            else:
                output_pwm.append(config.stop_pwm)
        self.set_pwm(output_pwm)

    # 初始化电机
    def init_motor(self):
        stop_pwm_list = [config.stop_pwm] * 8
        print('stop_pwm_list', stop_pwm_list)
        self.set_pwm(stop_pwm_list)
        time.sleep(2)
        up_pwm = [i + 200 for i in stop_pwm_list]
        print('up pwm', up_pwm)
        self.set_pwm(up_pwm)
        time.sleep(3)
        low_pwm = [i + 200 for i in stop_pwm_list]
        self.set_pwm(low_pwm)
        time.sleep(2)
        self.set_pwm(stop_pwm_list)
        time.sleep(1)

    def set_pwm(self, set_pwm_list: list):
        """
        设置pwm波数值
        :param set_pwm_list:
        :return:
        """
        for index, pwm in enumerate(set_pwm_list):
            # 判断是否大于阈值
            if pwm >= config.max_pwm:
                pwm = config.max_pwm
            if pwm <= config.min_pwm:
                pwm = config.min_pwm
            self.target_pwm_list[index] = int(pwm / (20000 / self.pice) / (50 / self.hz))
            # 如果有反桨叶反转电机pwm值
            # if config.left_motor_cw == 1:
            #     set_left_pwm = config.stop_pwm - (pwm - config.stop_pwm)
            # if config.right_motor_cw == 1:
            #     set_right_pwm = config.stop_pwm - (pwm - config.stop_pwm)

    # 循环修改pwm波值
    def loop_change_pwm(self):
        """
        一直修改输出pwm波到目标pwm波
        :return:
        """
        sleep_time = 0.01
        change_pwm_ceil = 5
        while True:
            self.pi.set_servo_pulsewidth(26, 1800)
            for index, current_pwm in enumerate(self.current_pwm_list):
                if abs(self.current_pwm_list[index] - self.target_pwm_list[index]) != 0:
                    self.current_pwm_list[index] = self.current_pwm_list[index] + (
                            self.target_pwm_list[index] - self.current_pwm_list[index]) // abs(
                        self.target_pwm_list[index] - self.current_pwm_list[index]) * change_pwm_ceil
                    self.pi.set_PWM_dutycycle(config.motor_pin_list[index],
                                              self.current_pwm_list[index])  # 1000=2000*50%
                else:
                    pass
            time.sleep(sleep_time)

    def read_deep(self, debug=False):
        while True:
            if self.deep_obj:
                return_deep = self.deep_obj.read_deep(debug=debug)
                if return_deep[0]:
                    self.temperature = return_deep[0]
                if return_deep[1]:
                    self.deep = return_deep[1]
            else:
                time.sleep(1)

    # 读取维特加速度计带罗盘数据
    def read_imu_compass(self, debug=False):
        while True:
            theta_list = self.imu_compass_obj.read_weite_imu_data(debug=debug)
            for index, value in enumerate(theta_list):
                if value:
                    self.theta_list[index] = value  # 依次放 x,y,z 角度
                if index == 2:
                    self.theta_z = value


if __name__ == '__main__':
    pi_main_obj = PiMain()
    # if os.path.exists(config.stc_port):
    #     com_data_obj = com_data.ComData(
    #         config.stc_port,
    #         config.stc_baud,
    #         timeout=config.stc2pi_timeout,
    #         logger=logger)
    loop_change_pwm_thread = threading.Thread(target=pi_main_obj.loop_change_pwm)
    loop_change_pwm_thread.start()

    while True:
        try:
            # 按键后需要按回车才能生效
            print('w:前进  a:后退  s:左转  d:右转  z:上升  c:下降  q:左移  e:右移  x:停止\n'
                  'r 初始化电机\n'
                  'g 读取一次imu数据，G 持续读取数据\n'
                  'f 读取深度传感器数据 F 持续读取数据\n'
                  )
            key_input = input('please input:')
            # 前 后 左 右 停止  右侧电机是反桨叶 左侧电机是正桨叶
            if key_input.startswith('w'):
                pi_main_obj.move(move_type=1)
            elif key_input.startswith('a'):
                pi_main_obj.move(move_type=2)
            elif key_input.startswith('s'):
                pi_main_obj.move(move_type=3)
            elif key_input.startswith('d'):
                pi_main_obj.move(move_type=4)
            elif key_input == 'z':
                pi_main_obj.move(move_type=5)
            elif key_input == 'c':
                pi_main_obj.move(move_type=6)
            elif key_input == 'q':
                pi_main_obj.move(move_type=7)
            elif key_input == 'e':
                pi_main_obj.move(move_type=8)
            elif key_input == 'x':
                pi_main_obj.move(move_type=0)
            elif key_input.startswith('r'):
                pi_main_obj.init_motor()
            # 获取读取单片机数据
            elif key_input.startswith('f'):
                stc_data = pi_main_obj.deep_obj.read_deep(debug=True)
            elif key_input.startswith('F'):
                stc_data = pi_main_obj.read_deep(debug=True)
            elif key_input.startswith('g'):
                imu_data = pi_main_obj.imu_compass_obj.read_weite_imu_data(debug=True)
                print('imu_data', imu_data)
            elif key_input.startswith('G'):
                pi_main_obj.read_imu_compass(debug=True)
        except KeyboardInterrupt:
            break
        # except Exception as e:
        #     print({'error': e})
        #     continue
