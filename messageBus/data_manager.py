"""
管理数据收发
"""
import time
import enum
import copy

from utils.log import LogHandler
from drivers import pi_main
import config
from moveControl import simple_pid
from messageBus import tcpClient


class RelayType(enum.Enum):
    """
    控制继电器种类
    headlight 前大灯
    audio_light 声光报警器
    side_light 舷灯
    """
    headlight = 0
    audio_light = 1
    side_light = 2


class ShipStatus(enum.Enum):
    """
    船状态
    idle  等待状态
    remote_control 遥控器控制
    computer_control 页面手动控制
    computer_auto 自动控制
    backhome_low_energy 低电量返航状态
    backhome_network 低电量返航状态
    at_home 在家
    tasking  执行检测/抽水任务中
    """
    idle = 1
    remote_control = 2
    computer_control = 3
    computer_auto = 4
    tasking = 5
    avoidance = 6
    backhome_low_energy = 7
    backhome_network = 8
    at_home = 9


class Nwse(enum.Enum):
    """
    北东南西方向
    """
    north = 0
    west = 1
    south = 2
    east = 3


class DataManager:
    def __init__(self):
        # 日志对象
        self.logger = LogHandler('data_manager_log', level=20)
        self.data_save_logger = LogHandler('data_save_log', level=20)
        self.com_data_read_logger = LogHandler('com_data_read_logger', level=20)
        self.com_data_send_logger = LogHandler('com_data_send_logger', level=20)
        self.server_log = LogHandler('server_data', level=20)
        self.gps_log = LogHandler('gps_log', level=20)
        self.path_track_obj = simple_pid.SimplePid()
        self.tcp_obj = tcpClient.TcpClient()
        # 开机时间
        self.start_time = time.time()
        # 进入自稳时当前角度和深度
        self.auto_theta_list = None
        self.auto_deep = None
        if config.current_platform == config.CurrentPlatform.pi:
            self.pi_main_obj = pi_main.PiMain()
        # 当前运动方向
        self.direction = 0

    def connect_uuv_server(self):
        while True:
            print('try connect server', self.tcp_obj.is_connected)
            if not self.tcp_obj.is_connected:
                self.tcp_obj.connect_server()
            time.sleep(2)
            # else:
            #     return

    def send_stc_data(self, data):
        """
        :param data:
        :return:
        """
        self.com_data_send_logger.info(data)
        if config.b_arduino:
            self.pi_main_obj.deep_obj.send_stc_data(data)
        # elif os.path.exists(config.arduino_com):
        #     self.pi_main_obj.deep_obj.send_data(data)

    def send_server_data(self):
        """
        持续给上位机发送当前状态数据
        """
        while True:
            time.sleep(0.2)
            if self.tcp_obj.is_connected:
                if not config.home_debug:
                    data = "{\"pressure\":%4.2f,\"water\":%d,\"light\":%d,\"sonar\":%d,\"camera\":%d,\"arm\":%d,\"pitch\":%.3f,\"roll\":%.3f,\"yaw\":%.3f,\"depth\":%2.2f,\"tem\":%2.1f,\"speed\":%d}\r\n" % (
                        self.pi_main_obj.press, self.pi_main_obj.is_leak_water, self.pi_main_obj.is_big_light,
                        self.pi_main_obj.is_sonar, self.pi_main_obj.camera_angle_pwm, self.pi_main_obj.arm_pwm,
                        self.pi_main_obj.theta_list[0],
                        self.pi_main_obj.theta_list[1],
                        self.pi_main_obj.theta_list[2],
                        self.pi_main_obj.deep,
                        self.pi_main_obj.temperature,
                        self.pi_main_obj.speed)
                    self.tcp_obj.write_data(data)
                else:
                    data = 'windows has no data'
                    self.tcp_obj.write_data(data)
            else:
                time.sleep(1)

    # 处理电机控制
    def move_control(self):
        while True:
            time.sleep(0.1)
            self.control_info = ''
            # 手动控制模式
            if self.tcp_obj.mode == 0:
                # 获取上位机发送的控制命令
                if self.auto_deep is not None:
                    self.auto_deep = None
                if self.auto_theta_list is not None:
                    self.auto_theta_list = None
                self.direction = int(self.tcp_obj.move)
                """
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
                self.control_info_dict = {0: ' 停止', 1: ' 前进', 2: ' 后退', 3: ' 左转', 4: ' 右转', 5: ' 上升', 6: ' 下降',
                                          7: ' 左移',
                                          8: ' 右移'}
                if self.direction in self.control_info_dict:
                    self.control_info += self.control_info_dict[self.direction]
                else:
                    self.control_info += '运动方向错误  '
                    self.control_info += self.direction
                # print('self.control_info', self.control_info)
                if not config.home_debug:
                    self.pi_main_obj.move(self.direction)
            # 自稳模式
            elif self.tcp_obj.mode == 1:
                # 记录进入自稳时的角度和深度
                if self.auto_deep is None:
                    self.auto_deep = self.pi_main_obj.deep
                if self.auto_theta_list is None:
                    self.auto_theta_list = copy.deepcopy(self.pi_main_obj.theta_list)
                # 判断当前偏差 执行控制
                delta_deep = self.auto_deep - self.pi_main_obj.deep  # 深度偏差
                delta_deep_pwm = self.path_track_obj.pid_pwm_deep(delta_deep)
                delta_theta_x = self.auto_theta_list[0] - self.pi_main_obj.theta_list[0]  # x轴角度
                delta_x_pwm = self.path_track_obj.pid_pwm_steer(delta_theta_x)  #
                delta_theta_y = self.auto_theta_list[1] - self.pi_main_obj.theta_list[1]  # y轴角度
                delta_y_pwm = self.path_track_obj.pid_pwm_steer(delta_theta_y)
                delta_theta_z = self.auto_theta_list[2] - self.pi_main_obj.theta_list[2]  # z轴角度
                delta_z_pwm = self.path_track_obj.pid_pwm_steer(delta_theta_z)
                self.pi_main_obj.set_pwm()
