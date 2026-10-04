#!/usr/bin/env python3
"""
VNC摄像头视频显示脚本
在VNC窗口中实时显示USB摄像头的视频画面


"""

import cv2
import numpy as np
import time
import threading
from datetime import datetime
import os


os.environ["DISPLAY"] = ":1" # 设置DISPLAY环境变量以确保在无头VNC中显示

class CameraViewer:
    def __init__(self, camera_index=0, window_name="Camera Stream"):
        self.camera_index = camera_index
        self.window_name = window_name
        self.cap = None
        self.is_running = False
        self.fps = 0
        self.frame_count = 0
        self.start_time = time.time()
        
    def initialize_camera(self):
        """初始化摄像头"""
        print(f"正在初始化摄像头 (设备索引: {self.camera_index})...")
        
        self.cap = cv2.VideoCapture(self.camera_index)
        
        if not self.cap.isOpened():
            print(f"✗ 无法打开摄像头 {self.camera_index}")
            return False
        
        # 设置分辨率
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        # 获取实际参数
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(self.cap.get(cv2.CAP_PROP_FPS))
        
        print(f"✓ 摄像头初始化成功")
        print(f"  分辨率: {width} x {height}")
        print(f"  帧率: {fps} FPS")
        
        return True
    
    def add_info_text(self, frame):
        """在帧上添加信息文本"""
        # 计算FPS
        self.frame_count += 1
        current_time = time.time()
        elapsed_time = current_time - self.start_time
        
        if elapsed_time > 1.0:
            self.fps = self.frame_count / elapsed_time
            self.frame_count = 0
            self.start_time = current_time
        
        # 添加时间戳
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, f"Time: {timestamp}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 添加FPS显示
        cv2.putText(frame, f"FPS: {self.fps:.1f}", (10, 70),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 添加分辨率信息
        height, width = frame.shape[:2]
        cv2.putText(frame, f"Resolution: {width}x{height}", (10, 110),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 添加操作提示
        cv2.putText(frame, "Press 'q' to quit, 's' to save", (10, height - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
        
        return frame
    
    def run(self):
        """运行摄像头显示循环"""
        if not self.initialize_camera():
            return
        
        self.is_running = True
        frame_count_for_save = 0
        
        print("\n开始显示摄像头画面...")
        print("操作说明：")
        print("  - 按 'q' 键退出")
        print("  - 按 's' 键保存当前帧")
        print("  - 按 'r' 键录制视频")
        print("  - 按 'p' 键暂停/继续")
        print("\n")
        
        is_paused = False
        video_writer = None
        is_recording = False
        
        try:
            while self.is_running:
                if not is_paused:
                    ret, frame = self.cap.read()
                    
                    if not ret:
                        print("✗ 无法读取帧数据")
                        break
                    
                    # 添加信息文本
                    frame = self.add_info_text(frame)
                    
                    # 如果正在录制，写入视频
                    if is_recording and video_writer is not None:
                        video_writer.write(frame)
                    
                    # 显示帧
                    cv2.imshow(self.window_name, frame)
                
                # 处理键盘输入
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    print("\n收到退出命令...")
                    self.is_running = False
                    
                elif key == ord('s'):
                    frame_count_for_save += 1
                    filename = f"camera_frame_{frame_count_for_save}_{int(time.time())}.jpg"
                    if ret:
                        cv2.imwrite(filename, frame)
                        print(f"✓ 已保存帧: {filename}")
                
                elif key == ord('r'):
                    if not is_recording:
                        # 开始录制
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        video_filename = f"camera_video_{timestamp}.avi"
                        
                        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
                        video_writer = cv2.VideoWriter(video_filename, fourcc, 30.0, (640, 480))
                        is_recording = True
                        print(f"\n▶ 开始录制: {video_filename}")
                    else:
                        # 停止录制
                        if video_writer is not None:
                            video_writer.release()
                            video_writer = None
                        is_recording = False
                        print(f"⏹ 录制已停止")
                
                elif key == ord('p'):
                    is_paused = not is_paused
                    if is_paused:
                        print("⏸ 视频已暂停")
                    else:
                        print("▶ 视频已继续")
                
        except KeyboardInterrupt:
            print("\n\n收到中断信号...")
            self.is_running = False
        
        finally:
            # 清理资源
            if is_recording and video_writer is not None:
                video_writer.release()
            
            if self.cap is not None:
                self.cap.release()
            
            cv2.destroyAllWindows()
            print("✓ 已释放所有资源")


class MultiCameraViewer:
    """多摄像头查看器"""
    def __init__(self):
        self.viewers = []
    
    def add_camera(self, camera_index, window_name):
        """添加一个摄像头"""
        viewer = CameraViewer(camera_index, window_name)
        self.viewers.append(viewer)
    
    def run_all(self):
        """运行所有摄像头"""
        if not self.viewers:
            print("没有添加任何摄像头")
            return
        
        threads = []
        for viewer in self.viewers:
            thread = threading.Thread(target=viewer.run)
            thread.daemon = True
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()


def single_camera_demo():
    """单摄像头演示"""
    print("\n╔" + "="*58 + "╗")
    print("║" + " "*15 + "VNC摄像头视频显示 - 单摄像头模式" + " "*10 + "║")
    print("╚" + "="*58 + "╝\n")
    
    viewer = CameraViewer(camera_index=0, window_name="Camera Stream")
    viewer.run()


def dual_camera_demo():
    """双摄像头演示（如果有多个摄像头）"""
    print("\n╔" + "="*58 + "╗")
    print("║" + " "*15 + "VNC摄像头视频显示 - 双摄像头模式" + " "*10 + "║")
    print("╚" + "="*58 + "╝\n")
    
    viewer_multi = MultiCameraViewer()
    viewer_multi.add_camera(0, "Camera 0")
    viewer_multi.add_camera(1, "Camera 1")
    viewer_multi.run_all()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="VNC摄像头视频显示工具")
    parser.add_argument('--camera', type=int, default=0, help='摄像头索引 (默认: 0)')
    parser.add_argument('--multi', action='store_true', help='多摄像头模式')
    parser.add_argument('--width', type=int, default=640, help='视频宽度 (默认: 640)')
    parser.add_argument('--height', type=int, default=480, help='视频高度 (默认: 480)')
    
    args = parser.parse_args()
    
    if args.multi:
        dual_camera_demo()
    else:
        viewer = CameraViewer(camera_index=args.camera, window_name="Camera Stream")
        viewer.run()


if __name__ == "__main__":
    main()
