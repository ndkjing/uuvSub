"""
入口函数
"""
import threading
import time
import config
from utils import log
from messageBus import data_manager
from drivers import audios_manager
import sys
import os

sys.path.append(
    os.path.join(
        os.path.dirname(
            os.path.abspath(__file__)),
        'drivers'))
sys.path.append(
    os.path.join(
        os.path.dirname(
            os.path.abspath(__file__)),
        'moveControl'))
sys.path.append(
    os.path.join(
        os.path.dirname(
            os.path.abspath(__file__)),
        'statics'))
sys.path.append(
    os.path.join(
        os.path.dirname(
            os.path.abspath(__file__)),
        'storage'))
sys.path.append(
    os.path.join(
        os.path.dirname(
            os.path.abspath(__file__)),
        'utils'))
logger = log.LogHandler('main_log')


def main():
    # 数据处理对象
    data_manager_obj = data_manager.DataManager()
    # 通用调用函数
    common_func_list = [data_manager_obj.connect_uuv_server,
                        data_manager_obj.move_control,
                        data_manager_obj.send_server_data,
                        data_manager_obj.tcp_obj.start_receive
                        ]
    common_thread_list = []
    # 树莓派对象数据处理
    pi_func_list = []
    pi_func_flag = []
    pi_thread_list = []
    if config.current_platform == config.CurrentPlatform.pi:
        pi_func_list = [data_manager_obj.pi_main_obj.loop_change_pwm,
                        data_manager_obj.pi_main_obj.read_deep,
                        data_manager_obj.pi_main_obj.read_imu_compass,
                        ]
        pi_func_flag.append(True)
        pi_func_flag.append(True)
        pi_func_flag.append(True)
    for common_func in common_func_list:
        common_thread_list.append(threading.Thread(target=common_func))
    if config.current_platform == config.CurrentPlatform.pi:
        for index, pi_func in enumerate(pi_func_list):
            if pi_func_flag[index]:
                pi_thread_list.append(threading.Thread(target=pi_func))
            else:
                pi_thread_list.append(None)
    for common_thread in common_thread_list:
        common_thread.start()

    if config.current_platform == config.CurrentPlatform.pi:
        for pi_thread in pi_thread_list:
            if pi_thread:
                pi_thread.start()
    print('home_debug', config.home_debug)
    thread_restart_time = 1
    #  判断线程是否死亡并重启线程
    while True:
        if config.current_platform == config.CurrentPlatform.pi:
            for index_common_thread, common_thread in enumerate(common_thread_list):
                if common_thread is not None and not common_thread.is_alive():
                    logger.error({'restart common_thread': index_common_thread})
                    print(index_common_thread, common_func_list[index_common_thread])
                    common_thread_list[index_common_thread] = threading.Thread(
                        target=common_func_list[index_common_thread])
                    common_thread_list[index_common_thread].start()
            for index_pi_thread, pi_thread in enumerate(pi_thread_list):
                if pi_thread and not pi_thread.is_alive():
                    logger.error({'restart pi_thread': index_pi_thread})
                    print(index_pi_thread, pi_func_list[index_pi_thread])
                    pi_thread_list[index_pi_thread] = threading.Thread(target=pi_func_list[index_pi_thread])
                    pi_thread_list[index_pi_thread].start()
            time.sleep(thread_restart_time)


if __name__ == '__main__':
    main()
