#!/usr/bin/env python3

################################################################################
# Copyright (c) 2024,D-Robotics.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
################################################################################

import sys
import signal
import os
import time
import logging

# 导入python串口库
import serial
import serial.tools.list_ports


PORT = "/dev/ttyS1"      # RPLIDAR S1 默认串口
BAUDRATE = 256000        # RPLidar S1 默认波特率

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def signal_handler(signal, frame):
    logger.info("Received SIGINT, exiting...")
    sys.exit(0)

def serialTest(timeout_s: float = 5.0):
    
    """
    自动串口连通性测试:
    - 打开串口
    - 发送一帧测试数据
    - 在超时时间内等待任意返回数据
    返回: 0 表示通过, 非 0 表示失败
    """
    uart_dev = PORT
    baudrate = BAUDRATE

    try:
        ser = serial.Serial(uart_dev, int(baudrate), timeout=1)  # 1s timeout
    except Exception as e:
        logger.error(f"open serial failed: {e}")
        return 1

    logger.debug(f"Serial port opened: {ser}")
    logger.info("Starting serial test...")

    start_ts = time.time()
    try:

        # 使用二进制发送测试数据（不再使用字符串编码）
        test_data = b"\x20"
        write_num = ser.write(test_data)
        logger.debug(f"Send (hex): {test_data.hex()}")

        received_total = b""
        while time.time() - start_ts < timeout_s:
            chunk = ser.read(64)
            if chunk:
                received_total += chunk
                # 打印原始字节和十六进制表示，避免 UTF-8 解码错误
                logger.debug(f"Recv (raw bytes): {received_total}")
                logger.debug(f"Recv (hex): {received_total.hex(' ')}")
                return 0
            time.sleep(0.1)

        logger.warn("No data received within timeout")
        return 2
    
    finally:
        ser.close()
        logger.info("Serial closed")


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)

    ret = serialTest()
    if ret != 0:
        logger.error("Serial test failed!")
        sys.exit(1)
    else:
        logger.info("Serial test success!")
        sys.exit(0)
