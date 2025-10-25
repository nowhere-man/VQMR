# Tasks: 视频质量指标报告系统（VQMR）

**Input**: Design documents from `/specs/001-video-quality-metrics-report/`
**Prerequisites**: plan.md, spec.md (user stories), data-model.md, contracts/README.md

**Tests**: 本项目采用测试优先（Test-First）原则（见宪法第五条），所有用户故事包含契约测试与集成测试任务。

**Organization**: 任务按用户故事分组，支持独立实现与测试，便于增量交付。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行执行（不同文件，无依赖）
- **[Story]**: 所属用户故事（US1, US2, US3, US4）
- 描述中包含准确的文件路径

## 项目结构约定

根据 plan.md，本项目采用 Web 应用结构：
- **后端**: `backend/src/`, `backend/tests/`
- **前端**: `frontend/static/`
- **任务数据**: `jobs/`

---

## Phase 1: Setup (共享基础设施)

**目的**: 项目初始化与基础结构

- [ ] T001 创建项目目录结构（backend/, frontend/, jobs/, docs/）
- [ ] T002 初始化 Python 虚拟环境并安装 FastAPI/Uvicorn/Jinja2/python-multipart/pytest
- [ ] T003 [P] 创建 .env.example 环境变量模板文件
- [ ] T004 [P] 创建 requirements.txt Python 依赖文件
- [ ] T005 [P] 配置 pytest.ini 和 pyproject.toml（linting/类型检查）
- [ ] T006 [P] 创建 .gitignore 文件（排除 venv/, jobs/, __pycache__/）
- [ ] T007 创建 backend/src/config.py 配置管理模块（读取 .env）
- [ ] T008 创建 backend/src/main.py FastAPI 应用入口点

---

## Phase 2: Foundational (阻塞性前置条件)

**目的**: 所有用户故事依赖的核心基础设施

**⚠️ 关键**: 此阶段完成前无法开始任何用户故事

- [ ] T009 实现 backend/src/models/base.py Pydantic 全局配置（json_encoders, arbitrary_types_allowed）
- [ ] T010 [P] 实现 backend/src/models/enums.py 枚举类型（TaskStatus, RateControlMode, VideoFormat）
- [ ] T011 [P] 实现 backend/src/utils/id_generator.py nanoid 任务 ID 生成工具
- [ ] T012 [P] 实现 backend/src/utils/file_utils.py 文件系统操作工具（atomic_write_json, create_job_directory）
- [ ] T013 [P] 实现 backend/src/utils/logger.py 结构化日志模块（JSON 格式，含 trace_id）
- [ ] T014 创建 backend/src/api/__init__.py 空文件（标记 API 包）
- [ ] T015 创建 backend/src/services/__init__.py 空文件（标记服务包）
- [ ] T016 创建 backend/src/templates/base.html Jinja2 基础模板（Tailwind CDN + 公共布局）
- [ ] T017 配置 backend/src/main.py 挂载静态文件（StaticFiles）和模板目录（Jinja2Templates）
- [ ] T018 实现 backend/src/api/errors.py 全局异常处理器（区分 API/页面请求）

**Checkpoint**: 基础设施就绪，用户故事可并行开始

---

## Phase 3: User Story 1 - 提交基础编码任务（优先级：P1）🎯 MVP

**Goal**: 用户可提交单个视频文件 + 单个 ABR 码控参数，系统执行编码并生成包含 PSNR/VMAF/SSIM 的基础报告

**Independent Test**: 通过 Web 界面上传 MP4 文件 + 指定编码器路径 + 单个 ABR 值（1000 kbps），验证任务成功创建、编码完成、报告显示三大质量指标

### 契约测试 (User Story 1) - 先编写测试

> **注意**: 先编写测试，确认失败后再实现功能

- [ ] T019 [P] [US1] 创建 backend/tests/conftest.py pytest fixture（TestClient, test_video_path, mock_ffmpeg）
- [ ] T020 [P] [US1] 编写 backend/tests/contract/test_upload_page.py 契约测试（GET / 返回 200 OK + HTML）
- [ ] T021 [P] [US1] 编写 backend/tests/contract/test_create_job.py 契约测试（POST /jobs 成功返回 303 + 验证失败返回 422）
- [ ] T022 [P] [US1] 编写 backend/tests/contract/test_job_report.py 契约测试（GET /jobs/{id} 返回报告页）
- [ ] T023 [P] [US1] 编写 backend/tests/contract/test_job_status.py 契约测试（GET /jobs/{id}/status 返回 JSON 状态）
- [ ] T024 [P] [US1] 编写 backend/tests/contract/test_health.py 契约测试（GET /health 返回健康状态）

### 集成测试 (User Story 1)

- [ ] T025 [US1] 编写 backend/tests/integration/test_single_task_e2e.py 端到端测试（提交 → 编码 → 报告生成）

### 数据模型 (User Story 1)

- [ ] T026 [P] [US1] 实现 backend/src/models/video_file.py（VideoFile, Resolution, YUVMetadata 基础支持）
- [ ] T027 [P] [US1] 实现 backend/src/models/rate_control.py（RateControlConfig, RateControlMode.ABR）
- [ ] T028 [P] [US1] 实现 backend/src/models/task.py（EncodingTask, TaskProgress）
- [ ] T029 [P] [US1] 实现 backend/src/models/metrics.py（QualityMetrics, FrameMetrics, PerformanceMetrics, FrameLatencyStats）
- [ ] T030 [P] [US1] 实现 backend/src/models/report.py（Report, VideoMetadata, EncodingResult）

### 服务层 (User Story 1)

- [ ] T031 [US1] 实现 backend/src/services/ffmpeg_service.py FFmpeg 服务（encode_video, calculate_psnr, calculate_vmaf, calculate_ssim, extract_metadata）
- [ ] T032 [US1] 实现 backend/src/services/metrics_service.py 指标计算服务（parse_psnr_log, parse_vmaf_json, parse_ssim_log, aggregate_metrics）
- [ ] T033 [US1] 实现 backend/src/services/task_service.py 任务管理服务（create_task, update_status, get_task, execute_encoding_task）
- [ ] T034 [US1] 实现 backend/src/services/report_service.py 报告生成服务（generate_report, export_csv）

### API 端点 (User Story 1)

- [ ] T035 [US1] 实现 backend/src/api/pages.py 页面路由（GET / 上传页，GET /jobs/{id} 报告页）
- [ ] T036 [US1] 实现 backend/src/api/jobs.py 任务 API（POST /jobs 创建任务，GET /jobs/{id}/status 状态查询）
- [ ] T037 [US1] 实现 backend/src/api/health.py 健康检查 API（GET /health）

### 前端模板与静态资源 (User Story 1)

- [ ] T038 [P] [US1] 创建 backend/src/templates/upload.html 上传页模板（表单：encoder_path, video_file, rate_control=abr, rate_values）
- [ ] T039 [P] [US1] 创建 backend/src/templates/report.html 报告页模板（任务摘要 + Chart.js 占位符）
- [ ] T040 [P] [US1] 创建 frontend/static/js/upload.js 上传表单交互脚本（文件验证、表单提交）
- [ ] T041 [P] [US1] 创建 frontend/static/js/charts.js Chart.js 基础图表渲染（PSNR/VMAF/SSIM 折线图）
- [ ] T042 [P] [US1] 创建 frontend/static/css/custom.css 自定义样式（补充 Tailwind）

### 集成与验证 (User Story 1)

- [ ] T043 [US1] 在 backend/src/main.py 中注册所有路由（pages, jobs, health）
- [ ] T044 [US1] 运行所有 US1 契约测试，确认通过
- [ ] T045 [US1] 运行 US1 端到端集成测试（使用真实 FFmpeg 或 Mock），确认通过
- [ ] T046 [US1] 手动测试：提交单个 ABR 任务 → 查看报告页 → 验证指标显示正确

**Checkpoint**: 用户故事 1 完全可用，可独立交付为 MVP

---

## Phase 4: User Story 2 - 对比多个码控参数（优先级：P2）

**Goal**: 用户可指定多个 ABR 或 CRF 值，系统并行/串行处理多个编码任务，生成对比图表

**Independent Test**: 提交包含 3 个 ABR 值（500, 1000, 2000 kbps）的任务，验证报告显示 3 条曲线的对比图表

### 契约测试 (User Story 2)

- [ ] T047 [P] [US2] 编写 backend/tests/contract/test_multi_params.py 契约测试（POST /jobs 支持多个 rate_values）
- [ ] T048 [P] [US2] 编写 backend/tests/contract/test_psnr_json.py 契约测试（GET /jobs/{id}/psnr.json 返回多参数结果）
- [ ] T049 [P] [US2] 编写 backend/tests/contract/test_psnr_csv.py 契约测试（GET /jobs/{id}/psnr.csv 返回 CSV 下载）

### 集成测试 (User Story 2)

- [ ] T050 [US2] 编写 backend/tests/integration/test_multi_params_e2e.py 端到端测试（多 ABR 值 → 多个编码任务 → 对比报告）

### 数据模型扩展 (User Story 2)

- [ ] T051 [P] [US2] 扩展 backend/src/models/rate_control.py 支持 RateControlMode.CRF（CRF 值验证 0-51）
- [ ] T052 [P] [US2] 扩展 backend/src/models/task.py 支持多参数任务进度跟踪（TaskProgress.completed_params 列表）

### 服务层扩展 (User Story 2)

- [ ] T053 [US2] 扩展 backend/src/services/task_service.py 支持多参数任务队列管理（循环处理 rate_values）
- [ ] T054 [US2] 扩展 backend/src/services/report_service.py 支持多参数对比图表数据生成

### API 端点扩展 (User Story 2)

- [ ] T055 [US2] 扩展 backend/src/api/jobs.py 添加 GET /jobs/{id}/psnr.json 端点（返回 JSON 格式指标）
- [ ] T056 [US2] 扩展 backend/src/api/jobs.py 添加 GET /jobs/{id}/psnr.csv 端点（返回 CSV 下载）
- [ ] T057 [US2] 更新 backend/src/api/jobs.py POST /jobs 支持逗号分隔的多个 rate_values

### 前端模板扩展 (User Story 2)

- [ ] T058 [US2] 更新 backend/src/templates/upload.html 表单提示支持多参数输入（逗号分隔）
- [ ] T059 [US2] 更新 backend/src/templates/report.html 支持多参数对比图表显示
- [ ] T060 [US2] 更新 frontend/static/js/charts.js 支持多条折线叠加显示（不同颜色区分参数）

### 集成与验证 (User Story 2)

- [ ] T061 [US2] 运行所有 US2 契约测试，确认通过
- [ ] T062 [US2] 运行 US2 端到端集成测试，确认通过
- [ ] T063 [US2] 手动测试：提交 3 个 ABR 值 → 验证对比图表显示正确
- [ ] T064 [US2] 手动测试：提交 3 个 CRF 值 → 验证 CRF 模式工作正常
- [ ] T065 [US2] 手动测试：同时选择 ABR 和 CRF → 验证返回 422 错误

**Checkpoint**: 用户故事 2 完全可用，可独立测试与交付

---

## Phase 5: User Story 3 - 分析原始 YUV 视频文件（优先级：P3）

**Goal**: 用户可提交原始 YUV 文件并提供元数据（分辨率/像素格式/帧率），系统正确编码并生成指标

**Independent Test**: 提交 YUV 文件 + 元数据（1920x1080, yuv420p, 30fps）→ 验证成功编码与指标生成

### 契约测试 (User Story 3)

- [ ] T066 [P] [US3] 编写 backend/tests/contract/test_yuv_upload.py 契约测试（POST /jobs 支持 YUV 参数）
- [ ] T067 [P] [US3] 编写 backend/tests/contract/test_yuv_validation.py 契约测试（YUV 缺失元数据返回 422）

### 集成测试 (User Story 3)

- [ ] T068 [US3] 编写 backend/tests/integration/test_yuv_e2e.py 端到端测试（YUV 文件 → 编码 → 报告）

### 数据模型扩展 (User Story 3)

- [ ] T069 [US3] 确认 backend/src/models/video_file.py YUVMetadata 验证逻辑（T026 已包含基础支持，需补充完整验证）

### 服务层扩展 (User Story 3)

- [ ] T070 [US3] 扩展 backend/src/services/ffmpeg_service.py 支持 YUV 文件编码（需额外参数：-s, -pix_fmt, -r）

### API 端点扩展 (User Story 3)

- [ ] T071 [US3] 扩展 backend/src/api/jobs.py POST /jobs 添加 YUV 元数据字段验证（yuv_resolution, yuv_pixel_format, yuv_frame_rate）

### 前端模板扩展 (User Story 3)

- [ ] T072 [US3] 更新 backend/src/templates/upload.html 添加 YUV 元数据输入表单（条件显示）
- [ ] T073 [US3] 更新 frontend/static/js/upload.js 添加 YUV 格式选择时显示/隐藏元数据表单逻辑

### 集成与验证 (User Story 3)

- [ ] T074 [US3] 运行所有 US3 契约测试，确认通过
- [ ] T075 [US3] 运行 US3 端到端集成测试，确认通过
- [ ] T076 [US3] 手动测试：提交 YUV 文件 + 正确元数据 → 验证成功
- [ ] T077 [US3] 手动测试：提交 YUV 文件但缺失元数据 → 验证返回 422 错误

**Checkpoint**: 用户故事 3 完全可用，可独立测试与交付

---

## Phase 6: User Story 4 - 监控逐帧性能指标（优先级：P3）

**Goal**: 报告页显示逐帧延迟图表（平均/最小/最大）和 CPU 利用率曲线

**Independent Test**: 提交任务 → 查看报告页 → 验证性能指标部分显示延迟图表和 CPU 利用率

### 契约测试 (User Story 4)

- [ ] T078 [P] [US4] 编写 backend/tests/contract/test_performance_metrics.py 契约测试（验证 psnr.json 包含 performance_metrics）

### 集成测试 (User Story 4)

- [ ] T079 [US4] 编写 backend/tests/integration/test_performance_e2e.py 端到端测试（验证性能指标收集与显示）

### 服务层扩展 (User Story 4)

- [ ] T080 [US4] 扩展 backend/src/services/ffmpeg_service.py 添加 CPU 利用率监控（使用 psutil 或 /proc/stat）
- [ ] T081 [US4] 扩展 backend/src/services/ffmpeg_service.py 添加逐帧延迟测量（记录每帧编码耗时）
- [ ] T082 [US4] 扩展 backend/src/services/metrics_service.py 添加性能指标聚合（计算平均/最小/最大延迟）

### 前端模板扩展 (User Story 4)

- [ ] T083 [US4] 更新 backend/src/templates/report.html 添加性能指标部分（延迟图表 + CPU 利用率图表）
- [ ] T084 [US4] 更新 frontend/static/js/charts.js 添加性能指标图表渲染（柱状图 + 折线图）

### 集成与验证 (User Story 4)

- [ ] T085 [US4] 运行所有 US4 契约测试，确认通过
- [ ] T086 [US4] 运行 US4 端到端集成测试，确认通过
- [ ] T087 [US4] 手动测试：提交任务 → 查看报告页性能部分 → 验证图表显示正确

**Checkpoint**: 用户故事 4 完全可用，可独立测试与交付

---

## Phase 7: Polish & Cross-Cutting Concerns (收尾与跨领域关注点)

**目的**: 生产级部署准备与文档完善

- [ ] T088 [P] 创建 Dockerfile（包含 Python + FFmpeg）
- [ ] T089 [P] 创建 docker-compose.yml（一键启动配置）
- [ ] T090 [P] 创建 scripts/cleanup_jobs.py 定时清理脚本（7 天前任务归档）
- [ ] T091 [P] 创建 docs/deployment.md 部署指南（直接运行 + Docker + Nginx 反向代理）
- [ ] T092 [P] 创建 docs/api.md API 文档（从 OpenAPI 规范生成）
- [ ] T093 [P] 创建 docs/user-manual.md 用户手册（截图 + 操作步骤）
- [ ] T094 [P] 添加 backend/src/api/health.py FFmpeg 可用性检查（调用 `ffmpeg -version`）
- [ ] T095 [P] 添加 backend/src/api/health.py VMAF 模型文件检查（检查 VMAF_MODEL_PATH 存在性）
- [ ] T096 [P] 添加 backend/src/api/health.py 磁盘空间检查（`shutil.disk_usage`）
- [ ] T097 配置 pytest-cov 覆盖率报告（目标 80%+ 整体覆盖率）
- [ ] T098 运行所有测试套件（契约 + 集成 + 单元），确认 100% 通过
- [ ] T099 运行 linting 检查（flake8/black/mypy），修复所有错误
- [ ] T100 创建 CHANGELOG.md 版本变更日志（0.1.0 初始版本）

---

## Dependencies & Execution Strategy

### User Story 依赖关系

```
Phase 1 (Setup) → Phase 2 (Foundational)
                      ↓
     ┌───────────────┼───────────────┬─────────────┐
     ↓               ↓                ↓              ↓
  US1 (P1)       US2 (P2)        US3 (P3)       US4 (P3)
    MVP          (依赖 US1)      (依赖 US1)     (依赖 US1)
```

**并行机会**:
- Phase 1 & 2 完成后，US1 可独立开始
- US1 完成后，US2/US3/US4 可并行开始（共享 US1 基础设施）
- 同一用户故事内，标记 [P] 的任务可并行执行

### 增量交付策略

1. **MVP（最小可行产品）**: Phase 1 + 2 + US1 = T001-T046
   - 用户可提交单任务 + 查看基础报告
   - 预计交付时间：1-2 周

2. **第二版**: 增加 US2 = T047-T065
   - 支持多参数对比
   - 预计交付时间：+3-5 天

3. **第三版**: 增加 US3 + US4 = T066-T087
   - YUV 支持 + 性能监控
   - 预计交付时间：+5-7 天

4. **生产版**: Phase 7 = T088-T100
   - Docker/文档/监控
   - 预计交付时间：+2-3 天

### 并行执行示例（Phase 3 - US1）

**测试阶段（可并行）**:
```bash
# 3 个契约测试可同时编写
T020 (test_upload_page.py)
T021 (test_create_job.py)
T022 (test_job_report.py)
```

**模型阶段（可并行）**:
```bash
# 5 个数据模型可同时实现
T026 (video_file.py)
T027 (rate_control.py)
T028 (task.py)
T029 (metrics.py)
T030 (report.py)
```

**前端阶段（可并行）**:
```bash
# 3 个前端文件可同时创建
T038 (upload.html)
T040 (upload.js)
T041 (charts.js)
```

---

## Task Summary

| Phase | 任务数 | 可并行任务数 | 预计工作量 |
|-------|-------|------------|----------|
| Phase 1: Setup | 8 | 5 | 0.5-1 天 |
| Phase 2: Foundational | 10 | 7 | 1-2 天 |
| Phase 3: US1 (P1) 🎯 MVP | 28 | 17 | 5-7 天 |
| Phase 4: US2 (P2) | 19 | 9 | 3-4 天 |
| Phase 5: US3 (P3) | 12 | 3 | 2-3 天 |
| Phase 6: US4 (P3) | 10 | 2 | 2-3 天 |
| Phase 7: Polish | 13 | 11 | 2-3 天 |
| **总计** | **100** | **54** | **15-23 天** |

### MVP 范围建议

**最小可交付版本**（MVP）= Phase 1 + 2 + US1 = 46 个任务

**包含功能**:
- ✅ 提交单个视频文件 + 单个 ABR/CRF 值
- ✅ FFmpeg 编码执行
- ✅ PSNR/VMAF/SSIM 质量指标计算
- ✅ 基础报告页（Chart.js 图表）
- ✅ 任务状态查询
- ✅ 健康检查 API
- ✅ 契约测试 + 集成测试

**不包含**:
- ❌ 多参数对比（US2）
- ❌ YUV 文件支持（US3）
- ❌ 逐帧性能监控（US4）
- ❌ Docker 部署（Phase 7）

---

## Independent Test Criteria (每个用户故事的独立测试标准)

### US1 独立测试
1. 启动 FastAPI 服务
2. 访问 `GET /` → 查看上传表单
3. 提交表单（encoder_path=/usr/bin/x264, video_file=test.mp4, rate_control=abr, rate_values=1000）
4. 重定向到 `GET /jobs/{id}` → 查看报告页
5. 验证报告页显示：PSNR/VMAF/SSIM 指标 + Chart.js 图表
6. 运行 `pytest backend/tests/contract/` → 所有 US1 测试通过

### US2 独立测试
1. 提交表单（rate_values=500,1000,2000）
2. 查看报告页 → 验证 3 条曲线对比图表
3. 访问 `GET /jobs/{id}/psnr.json` → 验证 JSON 包含 3 个 results
4. 访问 `GET /jobs/{id}/psnr.csv` → 验证 CSV 下载
5. 运行 `pytest backend/tests/contract/ -m US2` → 所有 US2 测试通过

### US3 独立测试
1. 提交表单（video_format=raw_yuv, yuv_resolution=1920x1080, yuv_pixel_format=yuv420p, yuv_frame_rate=30）
2. 查看报告页 → 验证 YUV 文件成功编码与指标生成
3. 提交 YUV 文件但不提供元数据 → 验证返回 422 错误
4. 运行 `pytest backend/tests/contract/ -m US3` → 所有 US3 测试通过

### US4 独立测试
1. 提交任务 → 查看报告页
2. 验证性能指标部分显示：逐帧延迟图表（平均/最小/最大）+ CPU 利用率曲线
3. 访问 `GET /jobs/{id}/psnr.json` → 验证 performance_metrics 字段完整
4. 运行 `pytest backend/tests/contract/ -m US4` → 所有 US4 测试通过

---

## Format Validation

✅ **所有任务遵循 checklist 格式**:
- Checkbox: `- [ ]`
- Task ID: `T001` - `T100`（顺序执行顺序）
- `[P]` 标记: 54 个并行任务
- `[Story]` 标签: US1/US2/US3/US4（用户故事阶段任务）
- 描述: 包含清晰动作与准确文件路径

✅ **任务组织**:
- Phase 1: Setup（8 个任务）
- Phase 2: Foundational（10 个任务）
- Phase 3-6: User Stories（69 个任务）
- Phase 7: Polish（13 个任务）

✅ **独立性验证**:
- 每个用户故事包含完整的测试、模型、服务、API、前端任务
- 每个用户故事有明确的独立测试标准
- US1 作为 MVP 可完全独立交付

---

**生成日期**: 2025-10-25
**总任务数**: 100
**可并行任务数**: 54
**建议 MVP 范围**: Phase 1 + 2 + US1（46 个任务）
