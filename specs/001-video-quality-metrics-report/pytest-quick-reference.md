# Pytest 快速参考指南

> VQMR 项目测试速查表

---

## 常用命令

```bash
# 基础测试运行
pytest                              # 运行所有测试
pytest -v                           # 详细输出
pytest -s                           # 显示 print 输出
pytest --tb=short                   # 简短回溯
pytest -x                           # 首次失败时停止

# 按标记运行
pytest -m contract                  # 仅契约测试
pytest -m integration               # 仅集成测试
pytest -m unit                      # 仅单元测试
pytest -m "not slow"                # 排除慢速测试
pytest -m "contract or unit"        # 组合标记

# 按路径/名称运行
pytest backend/tests/contract/                                    # 目录
pytest backend/tests/contract/test_health_api.py                 # 文件
pytest backend/tests/contract/test_health_api.py::test_health    # 特定测试
pytest -k "submission"                                           # 名称匹配

# 覆盖率
pytest --cov=backend/src                           # 基础覆盖率
pytest --cov=backend/src --cov-report=html         # HTML 报告
pytest --cov=backend/src --cov-report=term-missing # 显示缺失行
pytest --cov-fail-under=80                         # 低于 80% 失败

# 调试与重试
pytest --pdb                        # 失败时进入调试器
pytest --lf                         # 仅运行上次失败的测试
pytest --ff                         # 先运行上次失败的测试
pytest --durations=10               # 显示最慢的 10 个测试

# 并行执行 (需要 pytest-xdist)
pytest -n auto                      # 自动检测 CPU 数
pytest -n 4                         # 使用 4 个进程
```

---

## 项目结构

```
backend/tests/
├── conftest.py              # 根 fixtures
├── contract/                # API 契约测试 (100% 覆盖)
│   ├── test_health_api.py
│   ├── test_job_submission_api.py
│   └── test_report_api.py
├── integration/             # 端到端测试 (80%+ 覆盖)
│   ├── test_e2e_single_task.py
│   └── test_e2e_multi_params.py
├── unit/                    # 单元测试 (80%+ 覆盖)
│   ├── test_ffmpeg_service.py
│   └── test_metrics_service.py
├── fixtures/                # 模块化 fixtures
│   ├── app_fixtures.py
│   ├── ffmpeg_fixtures.py
│   └── video_fixtures.py
└── assets/                  # 测试资源
    ├── videos/
    └── ffmpeg_logs/
```

---

## Fixture 示例

### 基础 Fixture

```python
@pytest.fixture(scope="function")
def client(app):
    """FastAPI TestClient"""
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture(scope="function")
def tmp_jobs_dir(tmp_path):
    """临时任务目录"""
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()
    return jobs_dir
```

### Mock Fixture

```python
@pytest.fixture
def mock_ffmpeg_service(monkeypatch):
    """Mock FFmpegService"""
    mock = Mock()
    mock.encode_video.return_value = Mock(
        success=True,
        encoding_time=10.5,
        output_file=Path("/fake/output.mp4")
    )
    return mock
```

### 工厂 Fixture

```python
@pytest.fixture
def job_factory():
    """任务数据工厂"""
    def _create(job_id=None, status="queued", **kwargs):
        return {
            "job_id": job_id or uuid.uuid4(),
            "status": status,
            **kwargs
        }
    return _create

# 使用
def test_example(job_factory):
    job1 = job_factory()
    job2 = job_factory(status="completed")
```

---

## 测试模板

### 契约测试模板

```python
"""API 端点契约测试"""
import pytest
from fastapi.testclient import TestClient

@pytest.mark.contract
class TestAPIContract:

    def test_valid_request_returns_200(self, client: TestClient):
        """测试有效请求返回 200"""
        response = client.get("/api/v1/endpoint")

        assert response.status_code == 200

    def test_response_schema(self, client: TestClient):
        """测试响应符合 schema"""
        response = client.get("/api/v1/endpoint")
        data = response.json()

        assert "required_field" in data
        assert isinstance(data["required_field"], str)

    def test_invalid_input_returns_400(self, client: TestClient):
        """测试无效输入返回 400"""
        response = client.post("/api/v1/endpoint", json={"invalid": "data"})

        assert response.status_code == 400
        assert "detail" in response.json()
```

### 集成测试模板

```python
"""端到端集成测试"""
import pytest
import time
from pathlib import Path

@pytest.mark.integration
@pytest.mark.slow
class TestE2EWorkflow:

    def test_complete_workflow(
        self,
        client,
        test_video_path,
        tmp_jobs_dir
    ):
        """测试完整工作流"""
        # Step 1: 提交任务
        payload = {
            "video_path": str(test_video_path),
            "bitrate": 1000
        }
        submit_response = client.post("/api/v1/jobs", json=payload)
        assert submit_response.status_code == 201

        job_id = submit_response.json()["job_id"]

        # Step 2: 等待完成
        max_wait = 30
        start = time.time()

        while time.time() - start < max_wait:
            status_response = client.get(f"/api/v1/jobs/{job_id}/status")
            if status_response.json()["status"] == "completed":
                break
            time.sleep(1)

        # Step 3: 验证结果
        report_response = client.get(f"/jobs/{job_id}/report")
        assert report_response.status_code == 200

        # Step 4: 验证文件
        job_dir = tmp_jobs_dir / job_id
        assert (job_dir / "output.mp4").exists()
```

---

## 常用 Pytest 标记

```python
@pytest.mark.contract          # 契约测试
@pytest.mark.integration       # 集成测试
@pytest.mark.unit              # 单元测试
@pytest.mark.slow              # 慢速测试 (>5s)
@pytest.mark.ffmpeg            # 需要 FFmpeg
@pytest.mark.real_video        # 需要真实视频文件

@pytest.mark.skip              # 跳过测试
@pytest.mark.skipif(condition) # 条件跳过
@pytest.mark.xfail             # 预期失败

@pytest.mark.parametrize(      # 参数化测试
    "input,expected",
    [
        (1, 2),
        (2, 4),
        (3, 6),
    ]
)
def test_double(input, expected):
    assert input * 2 == expected
```

---

## 断言技巧

```python
# 基础断言
assert value == expected
assert value != unexpected
assert value in collection
assert value is True
assert value is not None

# 异常断言
with pytest.raises(ValueError):
    function_that_raises()

with pytest.raises(ValueError, match="error message"):
    function_that_raises()

# 警告断言
with pytest.warns(UserWarning):
    function_that_warns()

# 近似断言 (浮点数)
assert actual == pytest.approx(expected, rel=0.05)  # 5% 容差
assert 3.14159 == pytest.approx(3.14, abs=0.01)    # 绝对误差

# 自定义断言消息
assert condition, "Custom failure message"
```

---

## Mock 技巧

```python
from unittest.mock import Mock, patch, MagicMock

# Mock 对象
mock_obj = Mock()
mock_obj.method.return_value = "result"
mock_obj.method()  # 返回 "result"

# Mock 属性
mock_obj.attribute = "value"

# 验证调用
mock_obj.method.assert_called_once()
mock_obj.method.assert_called_with(arg1, arg2)
mock_obj.method.assert_not_called()

# Patch
with patch('module.function') as mock_func:
    mock_func.return_value = "mocked"
    result = function_under_test()

# Patch 装饰器
@patch('module.function')
def test_example(mock_func):
    mock_func.return_value = "mocked"
    # test code

# Monkeypatch (pytest)
def test_example(monkeypatch):
    monkeypatch.setattr('module.function', lambda: "mocked")
    monkeypatch.setenv('ENV_VAR', 'value')
```

---

## 异步测试

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """测试异步函数"""
    result = await async_function()
    assert result == expected

@pytest.fixture
async def async_client():
    """异步 fixture"""
    async with AsyncClient() as client:
        yield client

@pytest.mark.asyncio
async def test_with_async_fixture(async_client):
    """使用异步 fixture"""
    response = await async_client.get("/endpoint")
    assert response.status_code == 200
```

---

## 常见问题解决

### 1. 测试文件未被发现

```bash
# 确保文件名符合模式
test_*.py 或 *_test.py

# 确保在正确目录
pytest --collect-only  # 查看发现的测试
```

### 2. Fixture 未找到

```python
# 确保 conftest.py 在正确位置
tests/
├── conftest.py          # 根 fixtures
└── contract/
    ├── conftest.py      # 子目录 fixtures
    └── test_*.py

# 或使用 pytest_plugins
pytest_plugins = ["tests.fixtures.app_fixtures"]
```

### 3. 导入错误

```python
# 在 conftest.py 添加路径
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
```

### 4. 异步测试失败

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

### 5. 覆盖率不准确

```bash
# 清除旧的覆盖率数据
rm -rf .coverage coverage_html_report/

# 重新运行
pytest --cov=backend/src --cov-report=html
```

---

## CI/CD 快速配置

### GitHub Actions 最小配置

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        pip install -e ".[dev]"

    - name: Run tests
      run: |
        pytest --cov=backend/src --cov-fail-under=80
```

### Docker 快速测试

```bash
# 构建测试镜像
docker build -f Dockerfile.test -t vqmr-test .

# 运行所有测试
docker run --rm vqmr-test

# 运行特定测试
docker run --rm vqmr-test pytest -m contract -v
```

---

## 性能优化

```bash
# 并行运行 (安装 pytest-xdist)
pip install pytest-xdist
pytest -n auto

# 仅运行失败的测试
pytest --lf

# 先运行失败的测试
pytest --ff

# 禁用覆盖率加速
pytest --no-cov

# 使用最小输出
pytest -q

# 分组运行
pytest -m "contract" --maxfail=1  # 首次失败停止
```

---

## 推荐工具

| 工具 | 用途 | 安装 |
|-----|------|------|
| pytest-cov | 覆盖率报告 | `pip install pytest-cov` |
| pytest-asyncio | 异步测试 | `pip install pytest-asyncio` |
| pytest-mock | Mock 增强 | `pip install pytest-mock` |
| pytest-xdist | 并行执行 | `pip install pytest-xdist` |
| pytest-timeout | 超时控制 | `pip install pytest-timeout` |
| pytest-subprocess | 子进程 mock | `pip install pytest-subprocess` |
| faker | 测试数据生成 | `pip install faker` |
| httpx | 异步 HTTP | `pip install httpx` |

---

## 资源链接

- **Pytest 官方文档**: https://docs.pytest.org/
- **FastAPI 测试文档**: https://fastapi.tiangolo.com/tutorial/testing/
- **pytest-cov 文档**: https://pytest-cov.readthedocs.io/
- **pytest-asyncio 文档**: https://pytest-asyncio.readthedocs.io/
- **完整指南**: `pytest-testing-best-practices.md`

---

**最后更新**: 2025-10-25
