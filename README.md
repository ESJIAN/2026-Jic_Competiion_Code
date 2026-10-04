
<h1><b><center>AGENT AGV — BCI × 具身智能 × MR 四层闭环系统</center></b></h1>

> 基于地瓜机器人 RDK X5 的模块化移动操作臂系统，融合脑机接口（BCI）、具身智能、混合现实（MR）空间反馈，构建"意图接入 → Agent 调度 → 具身执行 → MR 反馈"四层认知-执行闭合回路。

<p align="center">
  <img src="https://img.shields.io/badge/Platform-RDK_X5-orange?style=flat-square" />
  <img src="https://img.shields.io/badge/Architecture-Four--Layer_Closed--Loop-blue?style=flat-square" />
  <img src="https://img.shields.io/badge/ROS-2_Humble-green?style=flat-square" />
  <img src="https://img.shields.io/badge/MR-Meta_Quest_3-purple?style=flat-square" />
  <img src="https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square" />
</p>

------

## 目录

- [项目概述](#项目概述)
- [四层闭环架构](#四层闭环架构)
- [核心创新](#核心创新)
- [硬件平台](#硬件平台)
- [软件技术栈](#软件技术栈)
- [当前进度](#当前进度)
- [工程路线图](#工程路线图)
- [通信接口](#通信接口)
- [快速开始](#快速开始)
- [仓库结构](#仓库结构)

------

## 项目概述

本项目为本科毕业设计，旨在构建一套完整的 **"BCI × 具身智能 × MR"四层闭环移动操作臂原型系统**。

与传统"BCI 触发机器人"方案不同，本系统的核心命题在于：将操作者的脑电意图、智能体任务调度、具身机器人执行、混合现实空间反馈四个环节串联成一个完整的 **认知-执行闭环**，使人成为回路中的有效调节环节。

**闭环运行流程：** 操作者通过 MR 眼镜感知机器人状态与路径预览 → 调整注意力集中程度 → BCI 捕获专注度变化并触发指令 → Agent 调度分解任务 → 机器人执行导航与抓取 → 传感器数据回传至 MR 渲染 → 循环。

------

## 四层闭环架构

```
【L1 意图接入层】 BCI / EEG → 专注度阈值 → START 指令
        ↓ START
【L2 Agent 调度层】 任务状态机 → 任务分解 → cmd_vel / 臂控指令
        ↓ cmd_vel
【L3 具身执行层】 Nav + 机械臂 + 视觉 → 抓取搬运 → Sensor data
        ↓ Sensor data
【L4 MR 反馈层】  Meta Quest 3 → 路径预览 + 任务状态 HUD → Visual feedback → L1
```

| 层级 | 名称           | 核心功能                                     | 关键技术                                  |
| ---- | -------------- | -------------------------------------------- | ----------------------------------------- |
| L1   | BCI 意图接入层 | EEG 专注度采集，阈值触发 START/PAUSE/ABORT   | 非侵入式 EEG、Python SDK                  |
| L2   | Agent 调度层   | 任务分解、状态机管理、行为树、异常处理       | ROS2 Action/Service                       |
| L3   | 具身执行层     | 底盘导航、机械臂控制、视觉感知、末端模块驱动 | Nav2、MoveIt2、YOLO-tiny                  |
| L4   | MR 空间反馈层  | 接收传感器数据，渲染路径/状态 AR 叠加层      | Meta Quest 3、Unity SDK、WebSocket Bridge |

------

## 核心创新

**四层认知-执行闭环（核心创新）：** MR 反馈层的输出作为操作者认知系统的输入，影响其注意力状态，进而通过 BCI 形成下一轮控制信号——将系统从"开环触发"升级为"闭环协同"。

**EEG 阈值触发的工程化决策：** 有意选择连续专注度阈值触发（≥70/100 持续 2 秒）而非离散 EEG 分类，从架构层面规避个体差异导致的分类器泛化失败，保证跨用户稳定性。键盘保留为备用触发方式。

**模块化末端自动识别：** 末端执行器通过电阻 ID 电路自动识别类型（夹爪/吸盘），Agent 层无需手动配置即可切换抓取策略。

**分层可调试工程架构：** 从驱动层即建立 Web 调试面板与独立测试脚本，每层模块可独立验证，降低单人开发的集成风险。

------

## 硬件平台

| 模块       | 型号 / 参数                                                  | 当前状态                        |
| ---------- | ------------------------------------------------------------ | ------------------------------- |
| 主控计算机 | RDK X5（地瓜机器人），Ubuntu + ROS2                          | ✅ 已到位                        |
| 底盘驱动   | I2C 4 路电机板，Bus 5，地址 0x26，轮距 160mm，轮径 65mm，减速比 30 | ✅ 已调通                        |
| IMU        | BNO055，I2C Bus 5，地址 0x29，四元数 + 角速度 + 加速度       | ✅ 已调通                        |
| 激光雷达   | RPLIDAR S1，串口 /dev/ttyS1，波特率 256000                   | ✅ 串口验证通过，ROS2 驱动待封装 |
| 摄像头     | USB 摄像头，/dev/video0，640×480，MJPEG                      | ✅ 已调通                        |
| 机械臂     | 待确认型号                                                   | ⏳ 待接入                        |
| 末端执行器 | 夹爪 / 吸盘（快换接口 + 电阻 ID 识别）                       | ⏳ 规划中                        |
| MR 眼镜    | Meta Quest 3（视频透传 MR，OpenXR / Unity XR Toolkit）       | ⏳ 待采购                        |
| EEG 设备   | NeuroSky MindWave / Emotiv Insight                           | ⏳ 后期接入                      |

------

## 软件技术栈

| 类别         | 技术 / 框架                                   | 状态          |
| ------------ | --------------------------------------------- | ------------- |
| 底层驱动     | smbus2 / adafruit-bno055                      | 已在用        |
| Web 调试     | FastAPI + uvicorn + SPA 前端                  | 已在用        |
| 视觉库       | OpenCV                                        | 已引入        |
| 机器人中间件 | ROS2 Humble（Topic / Action / Service / TF2） | 待配置        |
| 导航建图     | SLAM Toolbox + Nav2（A* + DWA）               | 待接入        |
| 操作臂控制   | MoveIt2 / 自定义 IK（依型号确定）             | 待定          |
| 目标检测     | YOLO-tiny / MobileNetV3                       | 待实现        |
| MR 开发      | Unity + Meta Quest 3 SDK + WebSocket Bridge   | 待接入        |
| BCI SDK      | NeuroSky / Emotiv Python SDK                  | 待接入        |
| 开发语言     | Python 3.10 + C++17 + C#（Unity）             | Python 已在用 |

------

## 当前进度

### 已完成模块

| 模块         | 路径                                                       | 说明                                                      |
| ------------ | ---------------------------------------------------------- | --------------------------------------------------------- |
| 底盘驱动     | `src/support/driver/chassis_driver.py`             | 差速运动学、I2C 通信、编码器反馈、速度修正                |
| IMU 驱动     | `src/support/driver/imu_driver.py`                 | BNO055 四元数 + 角速度 + 加速度                           |
| 摄像头驱动   | `src/support/driver/camera_driver.py`              | USB 摄像头 JPEG 流                                        |
| 激光雷达串口 | `tests/support/driver/lidar/lidar_connect.py`      | RPLIDAR S1 串口连接测试通过                               |
| 配置加载     | `src/support/config_loader.py`                     | YAML 配置加载                                             |
| 日志系统     | `src/support/logger/log.py`                        | RotatingFileHandler + 控制台双输出                        |
| Web 调试面板 | `web/api/main.py` + `web/public/`          | FastAPI 后端 + SPA 前端（底盘控制 / IMU / 雷达 / 摄像头） |
| 底盘测试脚本 | `tests/support/driver/chassis/`                    | 单电机、旋转、平移测试                                    |
| 分层架构     | `src/{support,execution,functional,decision,application}/` | 五层目录结构 + 接口文件                            |

### 待实现模块

| 模块               | 路径                                                  | 对应里程碑 |
| ------------------ | ----------------------------------------------------- | ---------- |
| URDF 建模          | `src/support/simulation/`                     | M0         |
| 激光雷达 ROS2 驱动 | `src/functional/slam_module/`                 | M0         |
| SLAM 建图          | `src/functional/slam_module/`                 | M1         |
| 路径规划           | `src/decision/path_planning/`                 | M1         |
| 机械臂控制         | `src/execution/arm_control/`                  | M2         |
| 视觉感知           | `src/functional/visual_perception/`           | M3         |
| 行为树             | `src/decision/behavior_tree/`                 | M4         |
| 任务调度           | `src/application/task_planner/`               | M4         |
| BCI 接入           | `src/application/bci_mr_interaction/scripts/bci_interface.py` | M5 |
| MR 反馈层          | `src/application/bci_mr_interaction/scripts/mr_interface.py`  | M6 |

------

## 工程路线图

12 个月周期，MVP 渐进式推进，7 个里程碑（M0–M6）。

| 里程碑                      | 时间节点   | 验收标准                                             | 优先级 |
| --------------------------- | ---------- | ---------------------------------------------------- | ------ |
| **M0** URDF + ROS2 底盘节点 | 第 2 周末  | URDF 在 RViz 正常显示，/odom 与 /scan 话题正常发布   | P0     |
| **M1** SLAM + 自主导航      | 第 6 周末  | 室内自主建图，Nav2 点到点导航成功，避障有效          | P0     |
| **M2** 机械臂基础控制       | 第 11 周末 | 机械臂完成预设动作，手眼标定完成，末端模块可自动识别 | P0     |
| **M3** 视觉抓取             | 第 16 周末 | 静态目标识别并抓取，成功率 ≥ 70%                     | P0     |
| **M4** 搬运全流程 Demo      | 第 24 周末 | 完整搬运流程（手动触发），成功率 ≥ 80%，耗时 < 3 min | P0     |
| **M5** 四层闭环联调         | 第 36 周末 | BCI 触发 + MR 实时反馈，端到端成功率 ≥ 70%           | P1     |
| **M6** 最终演示就绪         | 第 48 周末 | 系统稳定演示，Demo 视频完成，文档整理完毕            | P1     |
| ✅ 底盘驱动                  | 已完成     | ChassisDriver 完整实现，Web 面板可控                 | P0     |
| ✅ 传感器驱动                | 已完成     | IMU / 摄像头已调通，雷达串口验证通过                 | P0     |

> M4（搬运 Demo，手动触发）本身已是具备完整展示价值的成果。M5 四层闭环 Demo 是项目最大亮点与差异化所在。

------

## 通信接口

### 已实现接口（FastAPI REST，调试用）

| 接口                     | 方向          | 说明                                             |
| ------------------------ | ------------- | ------------------------------------------------ |
| `POST /api/control`      | 外部 → 底盘   | move_forward / backward / rotate_cw / ccw / stop |
| `GET /api/battery`       | 底盘 → 前端   | 电池电压（V）                                    |
| `GET /api/chassis/speed` | 底盘 → 前端   | 左右轮实时速度（m/s）                            |
| `GET /api/imu`           | IMU → 前端    | 四元数、角速度、加速度                           |
| `GET /api/lidar`         | 雷达 → 前端   | 激光扫描数据（当前为 Mock）                      |
| `GET /api/camera/stream` | 摄像头 → 前端 | MJPEG 视频流                                     |

### 规划接口（ROS2，正式集成）

| Topic                  | 方向              | 类型        | 说明                         |
| ---------------------- | ----------------- | ----------- | ---------------------------- |
| `/bci/attention_state` | BCI → Agent       | Float32     | 专注度 0–100，10Hz           |
| `/bci/task_trigger`    | BCI → Agent       | String      | START / PAUSE / ABORT        |
| `/cmd_vel`             | Agent → 底盘      | Twist       | 线速度 + 角速度              |
| `/odom`                | 底盘 → Agent / MR | Odometry    | 里程计位姿                   |
| `/scan`                | 雷达 → Nav2       | LaserScan   | 激光扫描数据                 |
| `/vision/target_pose`  | 视觉 → Agent      | PoseStamped | 目标物位姿                   |
| `/arm/joint_states`    | 臂 → Agent        | JointState  | 关节角度反馈                 |
| `/mr/robot_state`      | Agent → MR        | WebSocket   | 机器人位姿 + 任务状态 + 路径 |

------

## 快速开始

### 克隆仓库

```bash
git clone https://github.com/CRScienceTechnology/jic_competiion.git
cd jic_competiion
```

### 安装 Python 依赖

```bash
pip3 install -r requirements.txt
```

### 硬件验证（已完成模块）

```bash
# 底盘单电机测试
python3 tests/support/driver/chassis/left_motor.py

# 底盘旋转测试
python3 tests/support/driver/chassis/chassis_rotate.py

# 底盘平移测试
python3 tests/support/driver/chassis/chassis_translate.py

# 激光雷达串口连接测试
python3 tests/support/driver/lidar/lidar_connect.py

# 启动 Web 调试面板（底盘控制 / IMU / 雷达 / 摄像头）
cd web && uvicorn api.main:app --host 0.0.0.0 --port 8000
```

> ROS2 节点封装、SLAM 建图、Nav2 导航等功能尚在开发中，对应的 `ros2 launch` 命令将在各里程碑完成后补充。

------

## 仓库结构

```
jic_competiion/
└── 
        ├── src/
        │   ├── support/           # 支撑层：驱动、配置、日志、仿真
        │   │   ├── driver/        #   chassis_driver / imu_driver / camera_driver
        │   │   ├── config_loader.py
        │   │   ├── logger/
        │   │   └── simulation/    #   URDF（待完成）
        │   ├── execution/         # 执行层：底盘运动、机械臂控制
        │   │   └── arm_control/
        │   ├── functional/        # 功能层：SLAM、视觉感知、避障
        │   │   ├── slam_module/
        │   │   └── visual_perception/
        │   ├── decision/          # 决策层：路径规划、行为树
        │   │   ├── path_planning/
        │   │   └── behavior_tree/
        │   └── application/       # 应用层：任务调度、BCI/MR 交互
        │       ├── task_planner/
        │       └── bci_mr_interaction/
        ├── config/                # YAML 配置文件（底盘参数、IMU 参数等）
        ├── tests/                 # 硬件测试脚本
        │   └── support/driver/
        │       ├── chassis/
        │       ├── lidar/
        │       └── camera/
        ├── web/                   # Web 调试面板（FastAPI + SPA）
        │   ├── api/
        │   └── public/
└── README.md
```

------

## 许可证

本项目采用 [MIT License](LICENSE) 许可证。