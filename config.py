# 保存地图数据路径
import enum
import json
import os
import platform

root_path = os.path.dirname(os.path.abspath(__file__))
maps_dir = os.path.join(root_path, 'statics', 'mapsData')
if not os.path.exists(maps_dir):
    if not os.path.exists(os.path.join(root_path, 'statics')):
        os.mkdir(os.path.join(root_path, 'statics'))
    os.mkdir(os.path.join(root_path, 'statics', 'mapsData'))

base_setting_path = os.path.join(root_path, 'statics', 'configs', 'base_setting.json')
base_setting_default_path = os.path.join(root_path, 'statics', 'configs', 'base_setting_default.json')


class CurrentPlatform(enum.Enum):
    windows = 1
    linux = 2
    pi = 3
    others = 4


sysstr = platform.system()
if sysstr == "Windows":
    print("Call Windows tasks")
    current_platform = CurrentPlatform.windows
elif sysstr == "Linux":  # 树莓派上也是Linux
    print("Call Linux tasks")
    # 公司Linux电脑名称
    if platform.node() == 'raspberrypi':
        current_platform = CurrentPlatform.pi
    else:
        current_platform = CurrentPlatform.linux
else:
    print("other System tasks")
    current_platform = CurrentPlatform.others

# 速度等级 1到5级 速度从低到高，仅能控制手动模式下速度   1 级表示1600 5 2000
speed_grade = 2
calibration_compass = 0


def update_base_setting():
    global speed_grade
    global arrive_distance
    global find_points_num
    global path_search_safe_distance
    global row_gap
    global col_gap
    global pool_name
    global video_url
    if os.path.exists(base_setting_path):
        try:
            with open(base_setting_path, 'r') as f:
                base_setting_data = json.load(f)
            # 读取配置
            if base_setting_data.get('speed_grade'):
                try:
                    s_speed_grade = int(base_setting_data.get('speed_grade'))
                    if s_speed_grade >= 5:
                        s_speed_grade = 5
                    elif s_speed_grade <= 1:
                        s_speed_grade = 1
                    speed_grade = s_speed_grade
                except Exception as e:
                    print({'error': e})
            if base_setting_data.get('arrive_range'):
                try:
                    s_arrive_distance = float(base_setting_data.get('arrive_range'))
                    if s_arrive_distance < 2:
                        s_arrive_distance = 2.0
                    elif s_arrive_distance > 10:
                        s_arrive_distance = 10.0
                    arrive_distance = s_arrive_distance
                except Exception as e:
                    print({'error': e})

            if base_setting_data.get('keep_point'):
                try:
                    s_keep_point = int(base_setting_data.get('keep_point'))
                    if s_keep_point <= 0:
                        s_keep_point = 0
                    elif s_keep_point >= 1:
                        s_keep_point = 1
                    keep_point = s_keep_point
                except Exception as e:
                    print({'error': e})

            if base_setting_data.get('secure_distance'):
                try:
                    s_path_search_safe_distance = int(base_setting_data.get('secure_distance'))
                    if s_path_search_safe_distance > 100:
                        s_path_search_safe_distance = 100
                    elif s_path_search_safe_distance < 2:
                        s_path_search_safe_distance = 2
                    path_search_safe_distance = s_path_search_safe_distance
                except Exception as e:
                    print({'error': e})

            if base_setting_data.get('row'):
                try:
                    s_row_gap = int(base_setting_data.get('row'))
                    if s_row_gap < 0:
                        s_row_gap = 10
                    row_gap = s_row_gap
                except Exception as e:
                    print({'error': e})

            if base_setting_data.get('col'):
                try:
                    s_col_gap = int(base_setting_data.get('col'))
                    if s_col_gap < 0:
                        s_col_gap = 10
                    col_gap = s_col_gap
                except Exception as e:
                    print({'error': e})
            if base_setting_data.get('pool_name'):
                try:
                    s_pool_name = base_setting_data.get('pool_name')
                    pool_name = s_pool_name
                except Exception as e:
                    print({'error': e})
            if base_setting_data.get('video_url'):
                try:
                    s_video_url = base_setting_data.get('video_url')
                    video_url = s_video_url
                except Exception as e:
                    print({'error': e})
        except Exception as e:
            print({'error': e})

# pid三参数
kp = 2.0
ki = 0.3
kd = 1.0
# 最大pwm值
max_pwm = 1800
# 最小pwm值
min_pwm = 1200
# 停止中位pwm
stop_pwm = 1500
# 左侧电机正反桨  0 正桨叶   1 反桨叶
left_motor_cw = 1
# 右侧电机正反桨  0 正桨叶   1 反桨叶
right_motor_cw = 0
# pid间隔
pid_interval = 0.1
# 开机前等待时间
start_sleep_time = 6
# 电机初始化时间
motor_init_time = 1
# 检查网络连接状态间隔
check_network_interval = 10
if current_platform == CurrentPlatform.pi:
    home_debug = 0
else:
    home_debug = 1


# 保存配置到文件中
def write_setting(b_base=False, b_height=False, b_base_default=False, b_height_default=False):
    if b_base:
        with open(base_setting_path, 'w') as bf:
            json.dump({'speed_grade': speed_grade,
                       'arrive_range': arrive_distance,
                       'keep_point': find_points_num,
                       'secure_distance': path_search_safe_distance,
                       'row': row_gap,
                       'col': col_gap,
                       'pool_name': pool_name,
                       'video_url': video_url
                       },
                      bf)
    if b_base_default:
        with open(base_setting_default_path, 'w') as bdf:
            json.dump({'speed_grade': speed_grade,
                       'arrive_range': arrive_distance,
                       'keep_point': find_points_num,
                       'secure_distance': path_search_safe_distance,
                       'row': row_gap,
                       'col': col_gap,
                       'pool_name': pool_name,
                       'video_url': video_url
                       },
                      bdf)


########### 树莓派GPIO端口相关设置 均使用BCM编码端口
# 电机信号输出控制口
motor_pin_list = [4, 17, 27, 22, 5, 6]
motor_1 = 4
motor_2 = 17
motor_3 = 27
motor_4 = 22
motor_5_8 = 5
motor_6_7 = 6
# 配置电机控制方向 1 为逆时针转产生正向推力   -1为 顺时针转正向推力
motor_direction = [1, 1, -1, -1, 1, -1, 1, -1]

# Roll Factor     Pitch Factor    Yaw Factor      Throttle Factor     Forward Factor      Lateral Factor

VECTORED_6DOF = (
    (0, 0, 1.0, 0, -1.0, 1.0),
    (0, 0, -1.0, 0, -1.0, -1.0),
    (0, 0, -1.0, 0, 1.0, 1.0),
    (0, 0, 1.0, 0, 1.0, -1.0),
    (1.0, -1.0, 0, -1.0, 0, 0),
    (-1.0, -1.0, 0, -1.0, 0, 0),
    (1.0, 1.0, 0, -1.0, 0, 0),
    (-1.0, 1.0, 0, -1.0, 0, 0),
)

SELF_6DOF = (
    (0, 0, 1.0, 0, -1.0, 1.0),
    (0, 0, -1.0, 0, -1.0, -1.0),
    (0, 0, -1.0, 0, 1.0, 1.0),
    (0, 0, 1.0, 0, 1.0, -1.0),
    (1.0, -1.0, 0, -1.0, 0, 0),
    (-1.0, -1.0, 0, -1.0, 0, 0),
    (1.0, 1.0, 0, -1.0, 0, 0),
    (-1.0, 1.0, 0, -1.0, 0, 0),
)
motor_config = VECTORED_6DOF

# 软串口imu罗盘
b_pin_imu_compass = 1
pin_imu_compass_baud = 9600
pin_imu_compass_tx = 18
pin_imu_compass_rx = 23

# 深度
b_deep_iic = 1
# 使用arduino转接
b_arduino=1
if os.path.exists('/dev/ttyUSB0'):
    arduino_com = '/dev/ttyUSB0'
elif os.path.exists('/dev/ttyUSB1'):
    arduino_com = '/dev/ttyUSB1'
elif os.path.exists('/dev/ttyUSB2'):
    arduino_com = '/dev/ttyUSB2'
arduino_baud = 9600
arduino_timeout = 1

# tcp 服务器地址和端口
target_server_type = 0  # 0 1002 wifi地址  1 1002网线地址   2 控制箱地址
if target_server_type == 0:
    server_ip = '192.168.199.222'
elif target_server_type == 1:
    server_ip = '192.168.9.19'
else:
    server_ip = '192.168.2.2'
server_port = 5566

if __name__ == '__main__':
    write_setting(True, True, True, True)
