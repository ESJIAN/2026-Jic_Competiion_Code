# 项目目录结构说明

本文档描述了项目的当前文件结构及其设计意图。本项目采用分层架构设计，将代码职责清晰地划分为应用层、决策层、功能层、执行层和支持层。

## 目录概览

```
.
├── src/                # 核心源代码
│   ├── application/    # 应用层：最高层任务逻辑与交互
│   ├── decision/       # 决策层：路径规划、行为树等决策逻辑
│   ├── functional/     # 功能层：SLAM、感知、避障等核心算法模块
│   ├── execution/      # 执行层：硬件驱动与底层控制（底盘、机械臂等）
│   └── support/        # 支持层：通用工具、日志、配置加载、模拟器等
├── web/                # Web 交互界面
│   ├── api/            # 后端 API (FastAPI/Flask)
│   └── src/            # 前端源码
├── config/             # 配置文件 (YAML)
├── docs/               # 项目文档
├── launch/             # ROS 2 启动文件
├── tests/              # 单元测试与集成测试
├── scripts/            # 辅助脚本 (环境初始化等)
├── assets/             # 静态资源 (图片、视频等)
└── logs/               # 运行时日志
```

## 详细说明

### 1. `src/` (核心源码)

采用分层架构，依赖关系应遵循：应用层 -> 决策层 -> 功能层 -> 执行层 -> 支持层。

*   **`application/` (应用层)**
    *   `task_planner/`: 任务规划器，负责分解高层指令。
    *   `bci_mr_interaction/`: 脑机接口与混合现实交互逻辑。
    *   负责协调各个子系统完成最终任务。

*   **`decision/` (决策层)**
    *   `behavior_tree/`: 行为树逻辑，定义机器人的行为模式。
    *   `path_planning/`: 路径规划算法。

*   **`functional/` (功能层)**
    *   `slam_module/`: 建图与定位模块。
    *   `visual_perception/`: 视觉感知（目标检测、识别）。
    *   `obstacle_avoidance/`: 避障算法。

*   **`execution/` (执行层)**
    *   `chassis_control/`: 底盘运动控制与驱动。
    *   `arm_control/`: 机械臂控制。
    *   `camera_control/`: 相机驱动与图像采集。
    *   `lidar_control/`: 激光雷达驱动。
    *   `end_effector/`: 末端执行器（夹爪/吸盘）控制。

*   **`support/` (支持层)**
    *   `sdk/`: 第三方 SDK 库 (如 OrbbecSDK_ROS2)。
    *   `driver/`: 自写通用硬件驱动封装。
    *   `log/`: 日志系统封装。
    *   `ros2_utils/`: ROS 2 相关工具函数。
    *   `simulation/`: 仿真相关代码。
    *   `config_loader.py`: 配置加载工具。

### 2. `config/` (配置)
存放所有运行时配置文件，通常为 YAML 格式。
*   `system_params.yaml`: 系统级参数。
*   `chasis_params.yaml`: 底盘 PID、轮径等参数。
*   `perception_params.yaml`: 感知算法参数。
*   `ros2_settings.yaml`: ROS 2 节点配置。

### 3. `web/` (Web 界面)
提供基于 Web 的可视化监控与控制界面。
*   `api/`: Python 后端，负责与 ROS 系统通信。
*   `src/`: 前端代码。

### 4. `tests/` (测试)
*   按模块划分的测试用例（`chassis`, `lidar`, `camera` 等）。
*   建议使用 `pytest` 进行测试。

### 5. `docs/` (文档)
*   `dev_instruction/`: 开发指南（包括本文档、硬件配置、常用命令）。
*   `device_manuals/`: 硬件设备手册。
*   `dev_diary/`: 开发日记。
*   `dev_logs/`: 技术日志与逻辑说明。
*   `detail_plan/`: 详细设计文档。

## 开发建议

1.  **模块化原则**：新增功能时，请根据职责将其放入 `src` 下合适的层级目录中。
2.  **配置分离**：避免在代码中硬编码参数，应将其提取到 `config/` 下的 YAML 文件中。
3.  **文档更新**：如果修改了目录结构或添加了重要模块，请同步更新本文档。
4.  **硬件文档**：硬件相关的改动请同步更新 `docs/dev_instruction/hardware_config.md`。
