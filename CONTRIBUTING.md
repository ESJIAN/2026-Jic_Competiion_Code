Contributing

感谢你为本项目贡献代码！本文件提供本地开发、代码规范和 PR 流程的快速指南。

> **环境问题必须留档**：开发环境初始化/环境故障问题（包括但不限于「命令找不到」
> 「版本不符」「依赖缺失」「非交互 shell 不可见」）**必须**记录到
> [`docs/dev/instruction/dev_env_init.md`](docs/dev/instruction/dev_env_init.md)，
> 可复现的修复须同时沉淀为 `scripts/*_env_init.bash` 幂等脚本。
> 详见该文档 [§5 维护约定](docs/dev/instruction/dev_env_init.md#5-维护约定初始化问题必须记录)。

快速开始

1. 环境
   - 环境基线、初始化脚本与历史故障见
     [`docs/dev/instruction/dev_env_init.md`](docs/dev/instruction/dev_env_init.md)。
   - Node.js 工具链（`node` / `npm` / `npx`，目标 v24.13.0）：

     ```bash
     bash scripts/node_env_init.bash --check   # 诊断
     bash scripts/node_env_init.bash           # 安装 / 修复（幂等）
     ```

   - 推荐使用虚拟环境：

     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     pip install --upgrade pip
     pip install -r requirements.txt
     pip install -r requirements-dev.txt
     ```

2. 代码风格
   - 使用 `flake8` 进行风格检查。
   - 使用 `mypy` 做静态类型检查（可选，但推荐）。

3. 测试
   - 单元测试使用 `pytest`。本仓库中的 `tests/` 包含示例和如何 mock 硬件的测试。
   - 运行测试：

     ```bash
     pytest
     ```

4. 提交 PR
   - 新功能分支命名：`feature/<描述>`。
   - 修复命名：`bugfix/<描述>`。
   - 提交前请确保：
     - 本地运行了相关单元测试
     - 运行了 linter（`flake8`）
     - 若改动了环境/依赖/初始化脚本，同步更新
      `docs/dev/instruction/dev_env_init.md`
     - 在 PR 描述中写明改动目的与测试方法

5. CI
   - 项目使用 GitHub Actions（示例）在 PR/Push 时自动运行 lint 与 tests。

谢谢你！
