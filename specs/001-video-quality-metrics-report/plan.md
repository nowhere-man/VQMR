# Implementation Plan: 视频质量指标报告系统

**Branch**: `001-video-quality-metrics-report` | **Date**: 2025-10-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-video-quality-metrics-report/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

VQMR（Video Quality Metrics Report）是一个部署在服务器上的 Web 应用，允许用户通过浏览器提交视频编码任务，并生成包含 PSNR、VMAF、SSIM 等质量指标的可视化报告。系统支持单文件模式（固定预设转码后对比）和双文件模式（直接对比参考视频与待测视频），为视频工程师提供编码质量评估与参数优化能力。

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: FastAPI, Uvicorn, Jinja2, python-multipart, FFmpeg (系统依赖)
**Storage**: 文件系统（任务目录按 job_id 分桶，存储视频文件、日志、JSON/CSV 报告）
**Testing**: pytest（契约测试 + 集成测试）
**Target Platform**: Linux/macOS/Windows 服务器，支持 Docker 容器化部署
**Project Type**: Web 应用（后端 + 服务端渲染前端）
**Performance Goals**: 标准 1080p 10 秒视频在 5 分钟内完成指标计算；支持至少 10 个并发编码任务
**Constraints**:
- 单文件模式固定预设转码（H.264 2Mbps 或 CRF=23）
- 双文件模式要求分辨率、时长、帧率一致（可选自动对齐但默认不启用）
- 报告生成在编码完成后 30 秒内完成
- 指标计算误差需在行业标准工具 5% 以内
**Scale/Scope**:
- 支持 MP4、FLV 容器格式，支持原始 YUV 文件（需提供元数据）
- 支持 ABR 和 CRF 码控模式，允许多参数对比（至少 5 个）
- 提供帧级曲线图表（Chart.js）和 CSV 导出

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 一、总体原则
- ✅ **清晰一致**：采用 FastAPI（类型提示）+ Jinja2 模板引擎，保持代码与接口风格统一
- ✅ **规范驱动**：所有开发活动以 spec.md 为唯一事实来源
- ✅ **透明可追溯**：每个 API 端点、任务状态与指标计算均可追溯到功能需求
- ✅ **迭代式交付**：按用户故事优先级（P1→P2→P3）增量交付
- ✅ **审查优先**：代码提交前通过自测与 Code Review

### 二、设计与实现原则
- ✅ **最小可用**：P1 仅实现单编码器 + 单码控参数 + 基础指标报告
- ✅ **最少依赖**：仅使用 FastAPI/Uvicorn/Jinja2，无需 Redis/Celery 等消息队列
- ✅ **禁止过度设计**：避免引入 SPA 框架（React/Vue），采用 Tailwind CDN + 原生 JS
- ✅ **可删除性**：任务按 job_id 独立目录存储，7 天后可自动清理

### 三、语言与文档规范
- ✅ 所有文档、注释、提交信息使用简体中文
- ✅ 技术术语保留英文（PSNR、VMAF、SSIM、ABR、CRF）并提供中文释义
- ✅ 文档目录遵循规范：/specs（规格）、/docs（设计/API/部署）、/reports（生成报告）

### 四、代码规范
- ✅ Python 遵循 PEP8，命名采用 snake_case
- ✅ 环境变量通过 `.env` 管理，禁止硬编码路径
- ✅ 日志结构化（JSON），包含时间戳、模块、级别、trace_id
- ✅ 所有异常捕获并返回明确错误信息

### 五、测试与质量保证
- ✅ **测试优先**：先编写契约测试（API 接口）与集成测试（用户场景）
- ✅ **用户故事独立性**：P1/P2/P3 各自可独立测试与交付
- ✅ **质量门禁**：提交前通过所有测试、linting 检查、宪法合规验证

### 六、版本管理与变更控制
- ✅ 遵循语义化版本（初始版本 0.1.0）
- ✅ 破坏性变更提供迁移指南并递增 MAJOR 版本
- ✅ 每次发布更新 CHANGELOG.md

### 评估结果（Phase 0 - 初步评估）
**状态**: ✅ 通过
**说明**: 当前计划完全符合宪法所有原则，无需在复杂度跟踪中记录违规。

---

### 重新评估（Phase 1 - 设计完成后）

**日期**: 2025-10-25
**评估者**: Phase 1 设计验证

#### 一、总体原则
- ✅ **清晰一致**: 数据模型使用 Pydantic 强类型约束，API 契约使用 OpenAPI 3.0 规范
- ✅ **规范驱动**: 所有设计产物（data-model.md, contracts/）与 spec.md 保持一致
- ✅ **透明可追溯**: 每个 API 端点和数据模型均可追溯到功能需求（FR-xxx）
- ✅ **迭代式交付**: 设计支持按用户故事优先级增量交付（P1→P2→P3）
- ✅ **审查优先**: Phase 1 设计产物已完成，待代码实现前审查

#### 二、设计与实现原则
- ✅ **最小可用**: 数据模型仅包含必需字段，无冗余设计
- ✅ **最少依赖**: API 契约仅使用标准 HTTP/REST，无额外协议（GraphQL/gRPC）
- ✅ **禁止过度设计**:
  - 数据模型避免引入 ORM（直接使用 Pydantic）
  - API 契约避免引入 HATEOAS 等复杂模式
  - 文件系统任务管理避免引入数据库
- ✅ **可删除性**: 每个任务独立目录，可单独删除而不影响其他任务

#### 三、语言与文档规范
- ✅ 所有设计文档（data-model.md, contracts/README.md, quickstart.md）使用简体中文
- ✅ 技术术语保留英文（PSNR, VMAF, SSIM, Pydantic, OpenAPI）并提供中文释义
- ✅ 文档目录遵循规范：/specs/001-video-quality-metrics-report/（规格、计划、研究、设计、契约）

#### 四、代码规范
- ✅ Python 数据模型遵循 PEP8，字段命名采用 snake_case
- ✅ 环境变量配置已定义（.env.example, quickstart.md）
- ✅ 日志结构化需求已纳入数据模型（FrameLatencyStats, PerformanceMetrics）
- ✅ 异常处理已定义（API 契约中的错误响应格式）

#### 五、测试与质量保证
- ✅ **测试优先**: API 契约中已定义完整契约测试用例
- ✅ **用户故事独立性**: P1/P2/P3 可通过不同 API 端点组合独立测试
- ✅ **质量门禁**: OpenAPI 规范可自动生成契约测试

#### 六、版本管理与变更控制
- ✅ 遵循语义化版本（OpenAPI info.version: 0.1.0）
- ✅ API 契约已定义版本化路径（/v1 可选）

#### 最终评估
**状态**: ✅ 通过
**变更**: 无
**说明**: Phase 1 设计完全符合宪法所有原则。数据模型、API 契约和快速启动指南均满足：
1. 最小可用（仅实现必需功能）
2. 最少依赖（无额外框架或协议）
3. 禁止过度设计（避免 ORM、HATEOAS、GraphQL 等复杂模式）
4. 可删除性（任务目录独立）

**无需在复杂度跟踪中记录违规**。

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Web 应用结构（后端 + 服务端渲染前端）
backend/
├── src/
│   ├── models/           # 数据模型（EncodingTask, VideoFile, Metrics, Report）
│   ├── services/         # 业务逻辑（FFmpegService, MetricsService, TaskService）
│   ├── api/              # FastAPI 路由与端点（/jobs, /health, /{id}/psnr.json）
│   └── templates/        # Jinja2 模板（上传页、报告页）
└── tests/
    ├── contract/         # API 契约测试
    ├── integration/      # 端到端用户场景测试
    └── unit/             # 单元测试（可选）

frontend/
├── static/
│   ├── css/              # 自定义样式（补充 Tailwind CDN）
│   └── js/               # 原生 JS（表单交互、Chart.js 图表）
└── templates/            # 符号链接到 backend/src/templates（便于开发）

jobs/                     # 任务数据目录（按 job_id 分桶）
├── {job_id}/
│   ├── input.mp4         # 原始视频
│   ├── output.mp4        # 编码输出
│   ├── psnr.log          # FFmpeg 原始日志
│   ├── psnr.json         # 解析后的 JSON 结果
│   ├── psnr.csv          # 可下载的 CSV
│   └── metadata.json     # 任务元数据与状态

docs/                     # 设计文档与部署指南
├── api.md                # API 接口文档
├── deployment.md         # 部署指南（直接运行/Docker）
└── user-manual.md        # 用户手册

.env.example              # 环境变量模板
requirements.txt          # Python 依赖
Dockerfile                # Docker 镜像定义（可选）
docker-compose.yml        # 一键启动配置（可选）
```

**Structure Decision**: 采用 Web 应用结构（Option 2），因为需要前后端分离但不引入 SPA 复杂度。`backend/` 包含 FastAPI 应用与 Jinja2 模板，`frontend/static/` 包含静态资源（Tailwind CDN + Chart.js CDN + 少量原生 JS），`jobs/` 目录存储任务数据（文件系统持久化）。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
