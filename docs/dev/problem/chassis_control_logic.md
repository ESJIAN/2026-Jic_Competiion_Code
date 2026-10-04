# 底盘电机转向配置与控制逻辑分析

## 问题描述
在调试底盘自转 (`rotate`) 功能时，观察到以下现象：
1. 修改 `config/chasis_params.yaml` 中的 `left_dir` / `right_dir` 配置，会直接影响两个电机最终转向是“同向”还是“反向”。
2. 修改控制指令中角速度 `angular_z` 的正负（即左转或右转），只会让两个电机同时反向，但不会改变它们之间的“同向/反向”关系。

## 核心原理分析

底盘运动控制的最终输出是由**转速大小**、**配置修正系数**和**逻辑方向**三个因子共同决定的。

公式如下：

$$
\text{最终输出} = \underbrace{\text{RPM}}_{\text{转速大小}} \times \underbrace{\text{Config\_Dir}}_{\text{配置修正}} \times \underbrace{\text{Logic\_Dir}}_{\text{逻辑方向}}
$$

### 1. 因子定义
*   **RPM**: 电机转速的绝对值，永远为正。
*   **Config_Dir**: 来自配置文件 `chasis_params.yaml` 的物理极性修正（`left_dir`, `right_dir`），通常为 `1` 或 `-1`。用于适配电机安装方向。
*   **Logic_Dir**: 代码逻辑中定义的运动模式方向。
    *   **直线运动**: 左右轮逻辑均为 `+1`。
    *   **自转运动**: 左轮 `-1`，右轮 `+1`（或相反），逻辑上必须**相反**。

### 2. 现象解释

#### 为什么改配置 (`Config_Dir`) 会影响“同向/异向”关系？
在自转逻辑中，代码强制要求 `Logic_Dir` 是一正一负（例如左 `-1`，右 `+1`）。
此时最终输出符号的关系完全取决于 `Config_Dir`：

*   **如果配置为同号 (例如均为 1)**：
    *   左轮输出 $\propto 1 \times (-1) = -1$
    *   右轮输出 $\propto 1 \times (+1) = +1$
    *   **结果**：最终输出**异号**（一正一负）。

*   **如果配置为异号 (例如左 -1, 右 1)**：
    *   左轮输出 $\propto (-1) \times (-1) = +1$
    *   右轮输出 $\propto 1 \times (+1) = +1$
    *   **结果**：最终输出**同号**（均为正）。

因此，配置文件的符号一致性直接锁定了两轮最终输出的相对关系。

#### 为什么改转速方向 (`angular_z` 正负) 不影响关系？
改变 `angular_z` 的正负（如从左转变为右转），相当于把 `Logic_Dir` 整体取反：
*   **左转**: 左 `-1`，右 `+1` —— 逻辑相反。
*   **右转**: 左 `+1`，右 `-1` —— 逻辑依然相反。

无论怎么转，代码逻辑层面的“对立关系”没有变。因此，如果配置导致它们是“同号”的，那么左转时它们同正，右转时它们同负，始终保持“同号”。

## 结论
*   **配置文件 (`chasis_params.yaml`)**：决定了**“物理层”**如何解释信号。如果电机安装是对称镜像的，通常需要配置为一正一负，才能让两个轮子在收到“正”信号时都让车头朝前。
*   **控制函数 (`rotate`)**：决定了**“意图”**。自转的意图就是“左右互搏”。

在调试时，应优先通过**直线运动测试**确定 `Config_Dir` 的正确性（确保给正指令时车头向前），确认无误后，自转逻辑自然会符合预期。

## SOP

为了防止这个错误在线，总结如下 SOP ：

1. 明确对于安装在不同位置上的电机其正反转叫法是基于自身参考系的，而不是基于从哪往哪看

2. 明确一般我们设定顺时针为负，逆时针为正，无论是质点旋转还是刚体旋转都以此为默认规则 

3. 明确控制板是否对电机镜像对称安装进行了处理：
   a. 如果是，`chasis_params.yaml` 中 `left_dir` 与 `right_dir` 应配置为同号。
   b. 如果不是，`chasis_params.yaml` 中 `left_dir` 与 `right_dir` 应配置为一正一负。

4. 先用 AI 按照下方 SOP 形成一个定性代码，实现目的中的前进、倒退、旋转

> 思考：用映射+输入输出的思想和布尔代数工具是最快理解这个问题的，因为它直接映射了物理层的配置与控制层的意图。


# 底盘驱动代码 SOP 流程

在编写底盘代码时，一般 SOP 流程如下：

1. 需求冻结与接口契约  
   a. 将产品经理提供的《底盘运动需求表》转为 `chassis_req.md`，冻结线速度/角速度范围、轮距、减速比、编码器 PPR、最大加速度、急停距离。  
   b. 用 YAML-Schema 校验器锁定 `config/chasis_params.yaml` 字段，禁止新增未定义 key；CI 阶段 `jsonschema`（或 `pydantic-yaml`）校验不通过即拒绝合并。  

2. 静态代码准入  
   a. 引入 `ruff` + `mypy` 规则集 `mobility_robot.toml`，强制检查：  
      – 禁止裸 `ctypes` 直接调用电机寄存器  
      – 所有电机 HAL 调用必须封装在 `typing.Protocol` 抽象层，并通过 `MotorInterface` 依赖注入  
      – 浮点比较使用 `math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)`  
   b. 编译器/解释器开关：  
      `PYTHONOPTIMIZE=0 -W error::SyntaxWarning -W error::RuntimeWarning -X dev -m mypy --strict`；任何警告 = 构建失败。  

3. 单元测试金字塔  
   a. 底层：`pytest-cov` 覆盖 `kinematics.py`, `pid.py`, `limiter.py` 模块，要求行覆盖 ≥ 95%，分支覆盖 ≥ 90%。  
   b. 中层：使用 `pytest-mock` 打桩 `MotorInterface`，在 0 延时环境下验证“正转/反转/堵转”状态机。  
   c. 顶层：在 `gazebo_ros` 空世界跑 100 Hz 闭环，记录 `/wheel_odometry` 与 ground-truth 的 RMSE < 0.01 m、0.02 rad。  

4. 实时与并发  
   a. 控制循环线程绑定 `SCHED_FIFO` 优先级 95，隔离 2 个 CPU core（通过 `psutil` + `cpuset` 屏蔽内核调度）。  
   b. 所有共享数据统一使用 `asyncio.Lock`（或 `threading.Lock`）并配合 `pytest-deadlock` 静态分析，防止死锁。  
   c. 内存池预分配：电机命令缓冲区在启动阶段一次性 `[0] * 16384`，运行期禁止动态扩容。  

5. 参数版本与灰度  
   a. 参数文件纳入 git-lfs，文件名带校验和，如 `chasis_params_v1.3.7_3f92ea.yaml`。  
   b. 启动时通过 `hashlib.sha256` 对比本地与云端 SHA256，不一致则降级到上一次安全版本并报警。  

6. FMEA 注入测试  
   a. 模拟电机掉线：随机 `Path("/sys/class/pwm/motorX/enable").write_text("0")`，软件需在 50 ms 内检测到 `MISSING_FEEDBACK` 并进入缓停。  
   b. 模拟编码器反向：注入负脉冲，观测 `ESTOP` 是否在一周期内触发。  
   c. 记录失败日志到 `/var/log/mobility/fault_<timestamp>.bin`，供后续 SIEM 系统解析。  

7. 审计与追溯  
   a. 每次电机指令发布同步写 `TRACE` 通道：  
      `tracepoint(mobility, setpoint, ts_us, left_rpm, right_rpm, left_dir, right_dir)`；  
     使用 `perfetto`（或 `lttng-py`）收集，后期可用 `babeltrace` 与 Python 脚本回放。  
   b. 所有 PR 必须经过两人 Code-Owner + 一人 Safety-Owner 签字，并在 Jira 关联“安全需求 ID”。  

8. 发布与回滚  
   a. 生成 OTA 包：包含 `chassis_node.py`、`params.yaml`、udev rules、systemd service；使用 `swupdate` 双镜像策略。  
   b. 升级前先跑 30 s 健康脚本，若 `/proc/robot_safety_flag != 0` 则放弃升级。  
   c. 保留上一次镜像与参数快照，支持一键 `rollback.sh` 并在 20 s 内恢复运行。




# 底盘驱动测试 SOP 流程

在测试底盘工作时，一般SOP流程如下：

1. 备份原始配置  
   cp config/chasis_params.yaml config/chasis_params.yaml.bak

2. 进入最小调试模式  
   roslaunch your_bot bringup.launch debug:=true safety_override:=true

3. 直线运动基准测试  
   # 仅发布线速度，角速度置 0  
   rostopic pub /cmd_vel geometry_msgs/Twist '{linear: {x: 0.2}, angular: {z: 0}}' -r 10  
   # 观察车头是否向前移动  
   # 若后退 → 将对应 side 的 dir 乘以 -1 后写入 yaml，回到步骤 2

4. 原地零半径验证  
   # 关闭 safety_override，重新 launch  
   rostopic pub /cmd_vel geometry_msgs/Twist '{linear: {x: 0}, angular: {z: 0.5}}' -r 10  
   # 预期：两轮反向且车身逆时针旋转  
   # 若出现“同向打滑” → 说明步骤 3 中左右 dir 同号，需把其中一侧再取反，回到步骤 2

5. 闭环验证  
   # 启动完整导航栈，发布 360° 旋转 goal  
   # 用 rostopic echo /wheel_odometry 检查 yaw 是否单调变化，无震荡

6. 参数固化  
   # 确认无误后锁定 yaml  
   chmod 444 config/chasis_params.yaml  
   # 提交 git 并打 tag: git tag chassis-dir-verified


# AI 辅助总结

让 AI 帮写代码前，一定要求其按照工业级的代码规范、最佳实践、SOP去写。


# 底层抽象总结

1. 输入底层代码的数据物理单位与底层代码输出给上层代码的单位尽可能统一，
   例如：底层代码接收的速度指令单位为 rpm，输出的速度反馈单位也为 rpm。

2. 驱动有现成的就用现成的，不要自己写驱动，要仅仅围绕你的核心目的为快速的成型成套系统