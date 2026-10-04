
"""
ChassisDriver – I²C 4-channel motor driver board control module (differential drive)

This module provides a high-level interface for a 4-wheel motor driver board
communicating over I²C.  It supports:

* Motor parameter configuration (type, reduction ratio, encoder lines, dead-zone)
* Closed-loop speed control in RPM
* Raw PWM control
* Differential-drive kinematics (linear + angular velocity)
* Battery voltage monitoring
* Flexible motor-ID mapping and direction inversion

Usage
-----
>>> chassis = ChassisDriver(bus_num=5, addr=0x26)
>>> chassis.configure_motors(motor_type=1, reduction_ratio=30, magnetic_lines=11)
>>> chassis.set_movement(linear_x=0.5, angular_z=0.0)   # 0.5 m/s straight
>>> chassis.stop()

Author
------
<esjian@gmail.com>

License
-------
MIT
"""


import logging
import time
import struct
import math
from smbus2 import SMBus
from src.support.config_loader import load_chassis_config

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChassisDriver:
    
    """
    4路电机驱动板控制类 (差速模型)
    """
    
    def __init__(self, bus_num=None, addr=None, wheel_diameter_mm=None, wheel_base_mm=None):
        """
        初始化驱动板 - Load parameters from config/chasis_params.yaml but allow overrides
        
        - param bus_num: I2C总线号 (Optional, overrides config)
        - param addr: 设备地址 (Optional, overrides config)
        - param wheel_diameter_mm: 轮子直径 (mm) (Optional, overrides config)
        - param wheel_base_mm: 轮距 (mm) (Optional, overrides config)
        """
        config = load_chassis_config()

        # Load Register Config
        reg_conf = config.get('register_config', {})
        self.REG_MOTOR_TYPE = reg_conf.get('REG_MOTOR_TYPE', 0x01)
        self.REG_DEADZONE = reg_conf.get('REG_DEADZONE', 0x02)
        self.REG_MAGNETIC_LINES = reg_conf.get('REG_MAGNETIC_LINES', 0x03)
        self.REG_REDUCTION_RATIO = reg_conf.get('REG_REDUCTION_RATIO', 0x04)
        self.REG_WHEEL_DIAMETER = reg_conf.get('REG_WHEEL_DIAMETER', 0x05)
        self.REG_SPEED_CONTROL = reg_conf.get('REG_SPEED_CONTROL', 0x06)
        self.REG_PWM_CONTROL = reg_conf.get('REG_PWM_CONTROL', 0x07)
        self.REG_BATTERY_VOLTAGE = reg_conf.get('REG_BATTERY_VOLTAGE', 0x08)
        
        self.REG_SPEED_INFO = reg_conf.get('REG_SPEED_INFO', 0x09)

        # Encoder Registers (Updated)
        self.REG_M1_ENCODER = reg_conf.get('REG_M1_ENCODER', 0x20)
        self.REG_M2_ENCODER = reg_conf.get('REG_M2_ENCODER', 0x22)
        self.REG_M3_ENCODER = reg_conf.get('REG_M3_ENCODER', 0x24)
        self.REG_M4_ENCODER = reg_conf.get('REG_M4_ENCODER', 0x26)
        
        # I2C Config
        i2c_conf = config.get('i2c_config', {})
        self.bus_num = bus_num if bus_num is not None else i2c_conf.get('bus_num', 5)
        self.addr = addr if addr is not None else i2c_conf.get('device_addr', 0x26)
        
        # Wheel Config
        self.wheel_diameter_mm = wheel_diameter_mm if wheel_diameter_mm is not None else config.get('wheel_diameter_mm', 65)
        self.wheel_base_mm = wheel_base_mm if wheel_base_mm is not None else config.get('wheel_base_mm', 160)
        
        self.bus = None
        
        # Motor Mapping
        motor_mapping = config.get('motor_mapping', {})
        self.left_motor_id = motor_mapping.get('left_id', 3) 
        self.right_motor_id = motor_mapping.get('right_id', 2)
        
        # 电机方向修正 (1 或 -1)
        self.left_motor_dir = motor_mapping.get('left_dir', 1)
        self.right_motor_dir = motor_mapping.get('right_dir', 1)
        
        # 速度修正系数 (默认为1.0)
        speed_correction = config.get('speed_correction', {})
        self.left_scale = speed_correction.get('left_scale', 1.0)
        self.right_scale = speed_correction.get('right_scale', 1.0)
        
        self._connect()
        
        # Auto-configure motors
        motor_conf = config.get('motor_config', {})
        self.reconfig_motors(
            motor_type=motor_conf.get('motor_type', 1),
            reduction_ratio=motor_conf.get('reduction_ratio', 30),
            magnetic_lines=motor_conf.get('magnetic_lines', 11),
            deadzone=motor_conf.get('deadzone', 1600)
        )
        
        # Encoder state for speed calculation
        self._last_encoders = {1: 0, 2: 0, 3: 0, 4: 0}
        self._last_time = time.time()
        # Initialize encoder values
        self._init_encoders()

    def _init_encoders(self):
        """
            Initialize encoder values to avoid jump on first speed read
        """
        try:
            for motor_id in range(1, 5):
                val = self._read_encoder(motor_id)
                if val is not None:
                    self._last_encoders[motor_id] = val
        except Exception:
            pass

    def reconfig_speed_correction(self, left_scale=1.0, right_scale=1.0):
        """
        重设速度修正系数
        - param left_scale: 左轮速度缩放系数
        - param right_scale: 右轮速度缩放系数
        """
        self.left_scale = left_scale
        self.right_scale = right_scale



    def reconfig_motor_mapping(self, left_id=3, right_id=2, left_dir=1, right_dir=1):
        """
        重设左右后轮电机ID和方向修正参数
        
        - param left_id: 左轮电机ID (1-4)
        - param right_id: 右轮电机ID (1-4)
        - param left_dir: 左轮方向修正 (1 或 -1)
        - param right_dir: 右轮方向修正 (1 或 -1)

        """
        # 验证电机ID是否在1-4范围内
        if not (1 <= left_id <= 4 and 1 <= right_id <= 4):
            logger.error(f"Invalid motor IDs: left={left_id}, right={right_id}")
            raise ValueError("Motor IDs must be between 1 and 4")
        
        self.left_motor_id = left_id
        self.right_motor_id = right_id
        self.left_motor_dir = left_dir
        self.right_motor_dir = right_dir

    def reconfig_motors(self, motor_type=1, reduction_ratio=30, magnetic_lines=11, deadzone=1600):
        """
        重设电机参数
        - param motor_type: 1=520, 2=310, 3=TT(Enc), 4=TT(NoEnc)
        - param reduction_ratio: 减速比
        - param magnetic_lines: 磁环线数
        - param deadzone: 死区
        """
        self.reduction_ratio = reduction_ratio
        self.magnetic_lines = magnetic_lines
        
        if not self.bus: return False
        
        try:
            # 1. 类型
            self.bus.write_byte_data(self.addr, self.REG_MOTOR_TYPE, motor_type)
            time.sleep(0.1)
            
            # 2. 死区
            self.bus.write_i2c_block_data(self.addr, self.REG_DEADZONE, list(struct.pack('>h', deadzone)))
            time.sleep(0.1)
            
            # 3. 线数
            self.bus.write_byte_data(self.addr, self.REG_MAGNETIC_LINES, magnetic_lines)
            time.sleep(0.1)
            
            # 4. 减速比
            self.bus.write_byte_data(self.addr, self.REG_REDUCTION_RATIO, reduction_ratio)
            time.sleep(0.1)
            
            return True
        except OSError as e:
            logger.error(f"Config failed: {e}")
            return False

    def _connect(self):
        try:
            self.bus = SMBus(self.bus_num)
        except Exception as e:
            logger.error(f"I2C Bus {self.bus_num} connection failed: {e}")


    def _set_motors_speed(self, speeds):
        """
        底层发送4路电机速度指令
        - param speeds: 长度为4的列表/元组，对应 [M1, M2, M3, M4] 的速度值
        """
        if not self.bus: return
        
        data_bytes = bytearray()
        for s in speeds:
            # 限制范围 -1000 ~ 1000
            s = max(-1000, min(1000, int(s)))
            data_bytes.extend(struct.pack('>h', s))
            
        try:
            self.bus.write_i2c_block_data(self.addr, self.REG_SPEED_CONTROL, list(data_bytes))
        except OSError as e:
            logger.error(f"Write speed failed: {e}")

    def _set_motors_pwm(self, pwms):
        """
        底层发送4路电机PWM
        - param pwms: 长度为4的列表/元组，对应 [M1, M2, M3, M4] 的PWM值
        """
        if not self.bus: return
        
        data_bytes = bytearray()
        for p in pwms:
            # 限制范围 -3600 ~ 3600
            p = max(-3600, min(3600, int(p)))
            data_bytes.extend(struct.pack('>h', p))
            
        try:
            self.bus.write_i2c_block_data(self.addr, self.REG_PWM_CONTROL, list(data_bytes))
        except OSError as e:
            logger.error(f"Write PWM failed: {e}")



    def _calculate_rpm(self, speed_mps):
        """
        Helper to convert wheel speed in m/s to RPM
        """
        D = self.wheel_diameter_mm / 1000.0  # mm -> m
        return (speed_mps * 60) / (math.pi * D)

    def _read_encoder(self, motor_id):
        """
        Read 32-bit encoder value for a specific motor.
        
        Registers:
        M1: 0x20(High), 0x21(Low)
        M2: 0x22(High), 0x23(Low)
        M3: 0x24(High), 0x25(Low)
        M4: 0x26(High), 0x27(Low)
        """
        if not self.bus: return 0
        
        reg_map = {
            1: self.REG_M1_ENCODER,
            2: self.REG_M2_ENCODER,
            3: self.REG_M3_ENCODER,
            4: self.REG_M4_ENCODER
        }
        
        base_reg = reg_map.get(motor_id)
        if base_reg is None: return 0
        
        try:
            # Read High 16 bits
            high_bytes = self.bus.read_i2c_block_data(self.addr, base_reg, 2)
            high_val = struct.unpack('>h', bytes(high_bytes))[0] # Signed 16-bit
            
            # Read Low 16 bits
            low_bytes = self.bus.read_i2c_block_data(self.addr, base_reg + 1, 2)
            low_val = struct.unpack('>H', bytes(low_bytes))[0]   # Unsigned 16-bit
            
            # Combine: (High << 16) | Low
            # Note: high_val is signed. Python handles shifting signed integers by preserving sign bit if negative?
            # No, logic: 32-bit int constructed from 4 bytes.
            # data = buf[0]<<24 | buf[1]<<16 | bf[0]<<8 | bf[1]
            
            # Alternative using 4 bytes directly if possible, but registers are split.
            # Reconstruct 4 bytes:
            all_bytes = bytes(high_bytes + low_bytes)
            val = struct.unpack('>i', all_bytes)[0] # Signed 32-bit int
            
            return val
            
        except OSError as e:
            # logger.error(f"Read encoder {motor_id} failed: {e}")
            return None


    def set_twist(self, linear_x, angular_z):
        """
        Set chassis movement using linear and angular velocities (Differential Drive).
        
        Args:
            linear_x (float): Linear velocity in m/s (forward is positive).
            angular_z (float): Angular velocity in rad/s (CCW is positive).
        """
        # Calculate wheel speeds
        # v_l = v - (w * L / 2)
        # v_r = v + (w * L / 2)
        L = self.wheel_base_mm / 1000.0  # mm -> m
        
        v_l = linear_x - (angular_z * L / 2.0)
        v_r = linear_x + (angular_z * L / 2.0)
        
        # Convert to RPM
        rpm_l = self._calculate_rpm(v_l)
        rpm_r = self._calculate_rpm(v_r)
        
        # Apply direction and scale corrections
        # Left Motor
        target_speed_l = rpm_l * self.left_motor_dir * self.left_scale
        
        # Right Motor
        target_speed_r = rpm_r * self.right_motor_dir * self.right_scale
        
        # Build 4-channel speed array
        speeds = [0, 0, 0, 0]
        
        # Map to IDs
        if 1 <= self.left_motor_id <= 4 and 1 <= self.right_motor_id <= 4:
            speeds[self.left_motor_id - 1] = target_speed_l
            speeds[self.right_motor_id - 1] = target_speed_r
            
        self._set_motors_speed(speeds)

    def move(self, linear_x):
        """
        底盘直线运动控制
        - param linear_x: 线速度 (m/s), 前进为正
        """

        # Convert to RPM
        rpm = self._calculate_rpm(linear_x)
        
        # Apply direction and scale corrections
        target_speed_l = rpm * self.left_motor_dir * self.left_scale
        target_speed_r = rpm * self.right_motor_dir * self.right_scale
        
        # Build 4-channel speed array
        speeds = [0, 0, 0, 0]
        
        # Map to IDs
        if 1 <= self.left_motor_id <= 4 and 1 <= self.right_motor_id <= 4:
            speeds[self.left_motor_id - 1] = target_speed_l
            speeds[self.right_motor_id - 1] = target_speed_r
            
        self._set_motors_speed(speeds)
        


    def rotate(self, angular_z):
        """
        底盘自转运动控制
        - param angular_z: 角速度 (rad/s), 左转(逆时针)为正
        """
        # For in-place rotation: linear_x = 0
        L = self.wheel_base_mm / 1000.0  # mm -> m
        
        # Calculate speed magnitude based on angular velocity
        # v = omega * L / 2
        speed_mps = abs(angular_z * L / 2.0)
        
        # Convert to RPM
        rpm = self._calculate_rpm(speed_mps)
        
        # Determine directions based on angular_z sign
        # angular_z > 0 (Left Turn/CCW): Left Back, Right Forward
        # angular_z < 0 (Right Turn/CW): Left Forward, Right Back
        if angular_z > 0:
            # Spin Left (CCW)
            # Left Wheel: Backward (Reverse direction coefficient)
            # Right Wheel: Forward (Keep direction coefficient)
            target_speed_l = rpm * self.left_motor_dir * self.left_scale * -1
            target_speed_r = rpm * self.right_motor_dir * self.right_scale * 1
        else:
            # Spin Right (CW)
            # Left Wheel: Forward (Keep direction coefficient)
            # Right Wheel: Backward (Reverse direction coefficient)
            target_speed_l = rpm * self.left_motor_dir * self.left_scale * 1
            target_speed_r = rpm * self.right_motor_dir * self.right_scale * -1
            
        # Build 4-channel speed array
        speeds = [0, 0, 0, 0]
        
        # Map to IDs
        if 1 <= self.left_motor_id <= 4 and 1 <= self.right_motor_id <= 4:
            speeds[self.left_motor_id - 1] = target_speed_l
            speeds[self.right_motor_id - 1] = target_speed_r
            
        self._set_motors_speed(speeds)


    def wheel_speed(self):
        """
        Report left wheel speed and right wheel speed in m/s using encoder feedback.
        
        Returns:
            - tuple: (left_wheel_speed_mps, right_wheel_speed_mps)
        """
        if not self.bus: return (0.0, 0.0)
        
        current_time = time.time()
        dt = current_time - self._last_time
        
        if dt < 0.01: # Avoid division by zero or too small interval
            return (0.0, 0.0) # Return 0 or last speed? Better 0 or wait.
        
        # Read encoders
        left_enc = self._read_encoder(self.left_motor_id)
        right_enc = self._read_encoder(self.right_motor_id)
        
        if left_enc is None or right_enc is None:
            return (0.0, 0.0)
            
        # Calculate delta with overflow handling (32-bit)
        def calc_delta(curr, last):
            diff = curr - last
            # Handle 32-bit overflow/wrap
            if diff > 2147483647:
                diff -= 4294967296
            elif diff < -2147483648:
                diff += 4294967296
            return diff
            
        d_left = calc_delta(left_enc, self._last_encoders[self.left_motor_id])
        d_right = calc_delta(right_enc, self._last_encoders[self.right_motor_id])
        
        # Update state
        self._last_encoders[self.left_motor_id] = left_enc
        self._last_encoders[self.right_motor_id] = right_enc
        self._last_time = current_time
        
        # Calculate Speed
        # RPM = (d_ticks / dt) / (lines * ratio) * 60
        # MPS = RPM * PI * D / 60
        # Combined: MPS = (d_ticks / dt) / (lines * ratio) * PI * D
        
        # Avoid division by zero
        if self.magnetic_lines == 0 or self.reduction_ratio == 0:
            return (0.0, 0.0)
            
        factor = (math.pi * self.wheel_diameter_mm / 1000.0) / (self.magnetic_lines * self.reduction_ratio)
        
        left_speed = (d_left / dt) * factor
        right_speed = (d_right / dt) * factor
        
        # Direction correction:
        # If motor direction is reversed (-1), moving "forward" (command > 0) makes motor spin "backward".
        # Encoder counts "backward" (negative delta).
        # We want positive speed for forward movement.
        # So multiply by direction coefficient.
        
        return (left_speed * self.left_motor_dir, right_speed * self.right_motor_dir)
        
        
    def battery_voltage(self):
        """
            report battery voltage in V
        
        Returns:
            - float: battery voltage in V
        """
        if not self.bus: return 0.0
        try:    
            data = self.bus.read_i2c_block_data(self.addr, self.REG_BATTERY_VOLTAGE, 2)
            if len(data) >= 2:
                return (data[0] << 8 | data[1]) / 10.0
        except OSError as e:
            logger.error(f"Read battery voltage failed: {e}")
        return 0.0


    def stop(self):
        """
        底盘停止所有电机
        """
        self._set_motors_speed([0, 0, 0, 0])
        self._set_motors_pwm([0, 0, 0, 0])

    def close(self):
        """
        底盘关闭I2C总线连接
        """

        if self.bus:
            self.bus.close()
