#!/usr/bin/env python3
"""
USB摄像头检测和测试脚本
检测系统中是否存在USB摄像头，并进行基础功能测试
"""

import os
import subprocess
import cv2
import sys

def check_usb_devices():
    """使用 lsusb 检查USB设备"""
    print("="*60)
    print("【方法1】检查USB设备列表")
    print("="*60)
    try:
        result = subprocess.run(['lsusb'], capture_output=True, text=True, timeout=5)
        devices = result.stdout.strip().split('\n')
        print(f"\n检测到 {len(devices)} 个USB设备：\n")
        
        camera_devices = []
        for device in devices:
            print(f"  {device}")
            # 查找可能是摄像头的设备（通常包含Camera、Video等关键字）
            if any(keyword in device.lower() for keyword in ['camera', 'video', 'imaging', 'webcam']):
                camera_devices.append(device)
        
        if camera_devices:
            print(f"\n✓ 找到 {len(camera_devices)} 个可能的摄像头设备：")
            for cam in camera_devices:
                print(f"    {cam}")
        else:
            print("\n⚠ 在设备名称中没有找到明显的摄像头标识")
        
        return len(devices) > 0
    except FileNotFoundError:
        print("[错误] lsusb 命令不存在，请确保安装了 usbutils 包")
        return False
    except Exception as e:
        print(f"[错误] 检查USB设备失败: {e}")
        return False


def check_video_devices():
    """检查 /dev/video* 设备"""
    print("\n" + "="*60)
    print("【方法2】检查 /dev/video* 设备")
    print("="*60 + "\n")
    
    video_devices = []
    for i in range(10):  # 检查 /dev/video0 到 /dev/video9
        device_path = f"/dev/video{i}"
        if os.path.exists(device_path):
            video_devices.append(device_path)
            print(f"✓ 找到设备: {device_path}")
    
    if video_devices:
        print(f"\n✓ 共找到 {len(video_devices)} 个视频设备")
        return video_devices
    else:
        print("\n✗ 未找到 /dev/video* 设备")
        return []


def test_camera_with_opencv(device_path=0):
    """使用 OpenCV 测试摄像头"""
    print("\n" + "="*60)
    print("【方法3】使用 OpenCV 测试摄像头")
    print("="*60 + "\n")
    
    print(f"尝试打开摄像头 (device: {device_path})...")
    
    try:
        cap = cv2.VideoCapture(device_path)
        
        if not cap.isOpened():
            print(f"✗ 无法打开摄像头 {device_path}")
            return False
        
        print(f"✓ 成功打开摄像头 {device_path}")
        
        # 获取摄像头信息
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        
        print(f"\n摄像头参数：")
        print(f"  分辨率: {width} x {height}")
        print(f"  帧率: {fps} FPS")
        
        # 尝试读取几帧
        print(f"\n尝试读取摄像头帧...")
        successful_reads = 0
        failed_reads = 0
        
        for i in range(5):
            ret, frame = cap.read()
            if ret:
                successful_reads += 1
                print(f"  帧 {i+1}: ✓ 读取成功 (形状: {frame.shape})")
            else:
                failed_reads += 1
                print(f"  帧 {i+1}: ✗ 读取失败")
        
        cap.release()
        
        if successful_reads > 0:
            print(f"\n✓ 摄像头工作正常 ({successful_reads}/5 帧读取成功)")
            return True
        else:
            print(f"\n✗ 无法从摄像头读取数据")
            return False
            
    except Exception as e:
        print(f"✗ OpenCV 测试失败: {e}")
        return False


def check_camera_permissions():
    """检查摄像头权限"""
    print("\n" + "="*60)
    print("【方法4】检查摄像头权限")
    print("="*60 + "\n")
    
    for i in range(10):
        device_path = f"/dev/video{i}"
        if os.path.exists(device_path):
            try:
                # 检查读权限
                if os.access(device_path, os.R_OK):
                    print(f"✓ {device_path}: 有读权限")
                else:
                    print(f"✗ {device_path}: 无读权限")
                
                # 获取设备权限信息
                stat_info = os.stat(device_path)
                mode = oct(stat_info.st_mode)[-3:]
                print(f"   权限: {mode}")
                
            except Exception as e:
                print(f"✗ 检查 {device_path} 权限失败: {e}")


def list_v4l2_devices():
    """列出 v4l2 设备详细信息"""
    print("\n" + "="*60)
    print("【方法5】V4L2 设备详细信息")
    print("="*60 + "\n")
    
    try:
        result = subprocess.run(['v4l2-ctl', '--list-devices'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(result.stdout)
            return True
        else:
            print("⚠ v4l2-ctl 命令执行失败")
            return False
    except FileNotFoundError:
        print("⚠ v4l2-ctl 未安装，无法获取详细的V4L2信息")
        print("  可通过以下命令安装: sudo apt-get install v4l-utils")
        return False
    except Exception as e:
        print(f"✗ 获取V4L2信息失败: {e}")
        return False


def main():
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "USB摄像头检测和测试工具" + " "*16 + "║")
    print("╚" + "="*58 + "╝")
    
    results = {}
    
    # 方法1: 检查USB设备
    results['usb_devices'] = check_usb_devices()
    
    # 方法2: 检查 /dev/video* 设备
    video_devices = check_video_devices()
    results['video_devices'] = len(video_devices) > 0
    
    # 方法3: 检查权限
    check_camera_permissions()
    
    # 方法4: OpenCV测试
    if video_devices:
        print(f"\n[提示] 找到视频设备，准备进行OpenCV测试...")
        for device in video_devices:
            # 尝试转换设备路径为索引
            try:
                device_index = int(device.split('video')[1])
                if test_camera_with_opencv(device_index):
                    results['opencv_test'] = True
                    break
            except:
                pass
    else:
        results['opencv_test'] = False
    
    # 方法5: V4L2详细信息
    list_v4l2_devices()
    
    # 总结
    print("\n" + "="*60)
    print("【测试总结】")
    print("="*60)
    
    if video_devices or results.get('usb_devices') or results.get('opencv_test'):
        print("\n✓ 检测到USB摄像头")
        print(f"\n检测结果：")
        print(f"  - USB设备检查: {'✓ 通过' if results.get('usb_devices') else '✗ 失败'}")
        print(f"  - /dev/video* 设备: {'✓ 找到' if results.get('video_devices') else '✗ 未找到'}")
        print(f"  - OpenCV测试: {'✓ 通过' if results.get('opencv_test') else '✗ 失败或未执行'}")
        
        if video_devices:
            print(f"\n已识别的视频设备：")
            for device in video_devices:
                print(f"  - {device}")
    else:
        print("\n✗ 未检测到USB摄像头")
        print("\n可能的原因：")
        print("  1. 摄像头未连接或未被系统识别")
        print("  2. 缺少摄像头驱动程序")
        print("  3. 权限不足（尝试使用 sudo）")
        print("  4. USB接口有问题")
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()
