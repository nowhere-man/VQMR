# Chart.js 可视化视频质量指标最佳实践研究

**研究日期**: 2025-10-25
**研究人员**: Claude
**目标**: 为 VQMR 项目提供 Chart.js 集成方案，可视化 PSNR/VMAF/SSIM 等视频质量指标

---

## 目录

1. [技术选型](#技术选型)
2. [Chart.js 版本与 CDN 引入](#chartjs-版本与-cdn-引入)
3. [数据传递架构（后端 → 前端）](#数据传递架构后端--前端)
4. [图表类型与配置](#图表类型与配置)
5. [交互功能实现](#交互功能实现)
6. [样式定制与响应式设计](#样式定制与响应式设计)
7. [性能优化策略](#性能优化策略)
8. [完整代码示例](#完整代码示例)
9. [常见陷阱与最佳实践](#常见陷阱与最佳实践)

---

## 技术选型

### Chart.js vs 其他图表库

| 特性 | Chart.js | D3.js | Plotly.js | ECharts |
|------|----------|-------|-----------|---------|
| **学习曲线** | 低 | 高 | 中 | 中 |
| **包体积** | ~60KB (gzip) | ~240KB | ~1MB | ~800KB |
| **性能（大数据）** | 中等（需优化）| 高 | 高 | 高 |
| **响应式支持** | 原生支持 | 需手动实现 | 原生支持 | 原生支持 |
| **CDN 可用性** | ✅ | ✅ | ✅ | ✅ |
| **Tailwind 兼容** | ✅ | ✅ | ⚠️ | ⚠️ |

**推荐理由**：
- ✅ 轻量级（符合"最少依赖"原则）
- ✅ 学习成本低，文档完善
- ✅ 原生响应式支持，与 Tailwind CSS 无冲突
- ✅ 社区活跃，插件生态完善
- ⚠️ 大数据性能需优化（但符合 VQMR 使用场景：数千帧）

---

## Chart.js 版本与 CDN 引入

### 推荐版本

**Chart.js 4.x** (截至 2025 年最新稳定版)
- 完全重写的 TypeScript 代码库
- 更好的 Tree-shaking 支持
- 改进的性能与响应式机制

### CDN 引入方式

#### 方案 1：���用 jsDelivr（推荐）

```html
<!-- Chart.js 核心库 -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
```

**优点**：
- 全球 CDN 加速
- 自动选择最近节点
- 支持版本锁定（避免意外升级）

#### 方案 2：使用 unpkg

```html
<script src="https://unpkg.com/chart.js@4.4.0/dist/chart.umd.min.js"></script>
```

#### 方案 3：本地托管（生产环境推荐）

```bash
# 下载到静态资源目录
wget https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js \
     -O frontend/static/js/chart.min.js
```

```html
<script src="/static/js/chart.min.js"></script>
```

**最佳实践**：
- 开发环境使用 CDN（快速原型）
- 生产环境本地托管（避免 CDN 故障导致服务不可用）

---

## 数据传递架构（后端 → 前端）

### 架构图

```
┌────────────────��────────────────────────────────────────┐
│                    FastAPI 后端                         │
│                                                         │
│  ┌──────────────┐      ┌──────────────┐               │
│  │ MetricsService│─────▶│ TaskService  │               │
│  └──────────────┘      └──────────────┘               │
│         │                      │                        │
│         ▼                      ▼                        │
│  ┌─────────────────────────────────────┐               │
│  │  /jobs/{job_id}/psnr.json           │               │
│  │  返回: {"frames": [...], ...}       │               │
│  └─────────────────────────────────────┘               │
│         │                      │                        │
│         ▼                      ▼                        │
│  ┌─────────────────────────────────────┐               │
│  │  Jinja2 Template Rendering          │               │
│  │  report.html.jinja2                 │               │
│  └─────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────���──────┐
│              渲染后的 HTML (浏览器)                      │
│                                                         │
│  <script>                                               │
│    const metricsData = {{ metrics_json | tojson }};    │
│    // metricsData 现在是原生 JavaScript 对象           │
│  </script>                                              │
│                                                         │
│  <script src="/static/js/charts.js"></script>          │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│            charts.js (前端逻辑)                         │
│                                                         │
│  function renderPSNRChart(data) {                       │
│    new Chart(ctx, {                                     │
│      data: {                                            │
│        labels: data.frames.map(f => f.frame_number),   │
│        datasets: [{                                     │
│          label: 'PSNR (dB)',                            │
│          data: data.frames.map(f => f.psnr_y)          │
│        }]                                               │
│      }                                                  │
│    });                                                  │
│  }                                                      │
└─────────────────────────────────────────────────────────┘
```

### 后端数据结构（FastAPI）

```python
# backend/src/models/metrics.py
from pydantic import BaseModel
from typing import List, Optional

class FrameMetrics(BaseModel):
    frame_number: int
    psnr_y: float  # Y 通道 PSNR
    psnr_u: Optional[float] = None
    psnr_v: Optional[float] = None
    ssim: float
    vmaf: float
    encoding_time_ms: Optional[float] = None  # 逐帧编码时间

class VideoMetrics(BaseModel):
    job_id: str
    video_name: str
    encoder: str
    bitrate_kbps: int
    crf: Optional[int] = None
    frames: List[FrameMetrics]
    summary: dict  # 聚合统计（平均值、P95 等）

# backend/src/api/routes.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import json

router = APIRouter()

@router.get("/jobs/{job_id}/metrics.json")
async def get_metrics_json(job_id: str):
    """返回 JSON 格式的指标数据（供 AJAX 调用）"""
    metrics_file = f"jobs/{job_id}/metrics.json"
    if not os.path.exists(metrics_file):
        raise HTTPException(status_code=404, detail="Metrics not found")

    with open(metrics_file) as f:
        data = json.load(f)
    return JSONResponse(content=data)
```

### 方案 1：内联 JSON（推荐用于初始渲染）

**优点**：
- 无需额外 HTTP 请求
- 页面加载即可渲染图表
- 适合 SSR（服务端渲染）场景

**实现代码**：

```python
# backend/src/api/routes.py
from fastapi import Request
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="backend/src/templates")

@router.get("/jobs/{job_id}/report")
async def get_report(request: Request, job_id: str):
    # 读取指标数据
    metrics = load_metrics_from_file(job_id)

    return templates.TemplateResponse(
        "report.html.jinja2",
        {
            "request": request,
            "job_id": job_id,
            "metrics": metrics,  # Pydantic 模型
            "metrics_json": metrics.model_dump_json()  # 序列化为 JSON 字符串
        }
    )
```

```jinja2
{# backend/src/templates/report.html.jinja2 #}
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>质量指标报告 - {{ job_id }}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head>
<body>
    <canvas id="psnrChart"></canvas>

    <script>
        // Jinja2 的 tojson 过滤器自动转义 JSON（防止 XSS）
        const metricsData = {{ metrics_json | tojson }};

        // 现在 metricsData 是原生 JavaScript 对象
        console.log('帧数:', metricsData.frames.length);
    </script>

    <script src="/static/js/charts.js"></script>
</body>
</html>
```

**安全注意事项**：
- ✅ `tojson` 过滤器自动转义特殊字符（防止 XSS 攻击）
- ⚠️ 避免使用 `| safe`（除非确定数据已消毒）

### 方案 2：AJAX 异步加载（推荐用于大数据/懒加载）

**优点**：
- 减少初始页面大小
- 支持按需加载（例如切换不同指标时才加载）
- 适合数据量大的场景

**实现代码**：

```html
<canvas id="psnrChart"></canvas>

<script>
async function loadMetrics(jobId) {
    const response = await fetch(`/jobs/${jobId}/metrics.json`);
    if (!response.ok) {
        throw new Error('Failed to load metrics');
    }
    return await response.json();
}

// 页面加载后异步获取数据
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const jobId = '{{ job_id }}';  // 从 Jinja2 传递
        const metricsData = await loadMetrics(jobId);
        renderPSNRChart(metricsData);
    } catch (error) {
        console.error('加载指标失败:', error);
        showErrorMessage('无法加载质量指标数据');
    }
});
</script>
```

### 数据格式示例

```json
{
  "job_id": "abc123",
  "video_name": "test_video.mp4",
  "encoder": "libx264",
  "bitrate_kbps": 2000,
  "crf": null,
  "frames": [
    {
      "frame_number": 0,
      "psnr_y": 45.32,
      "psnr_u": 48.21,
      "psnr_v": 47.89,
      "ssim": 0.9856,
      "vmaf": 92.45,
      "encoding_time_ms": 12.5
    },
    {
      "frame_number": 1,
      "psnr_y": 44.89,
      "psnr_u": 47.95,
      "psnr_v": 47.56,
      "ssim": 0.9842,
      "vmaf": 91.87,
      "encoding_time_ms": 11.8
    }
    // ... 更多帧
  ],
  "summary": {
    "avg_psnr_y": 43.25,
    "avg_ssim": 0.9801,
    "avg_vmaf": 89.34,
    "min_vmaf": 78.12,
    "p95_vmaf": 95.67,
    "total_encoding_time_s": 45.2,
    "avg_fps": 30.5
  }
}
```

---

## 图表类型与配置

### 1. 逐帧质量指标曲线（折线图）

**用途**：展示 PSNR/VMAF/SSIM 随时间（帧号）的变化趋势

#### 基础配置

```javascript
// frontend/static/js/charts.js

function renderQualityMetricsChart(canvasId, metricsData) {
    const ctx = document.getElementById(canvasId).getContext('2d');

    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: metricsData.frames.map(f => f.frame_number),
            datasets: [
                {
                    label: 'VMAF',
                    data: metricsData.frames.map(f => f.vmaf),
                    borderColor: 'rgb(59, 130, 246)',  // Tailwind blue-500
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,  // 隐藏点（大数据性能优化）
                    tension: 0,  // 直线连接（不使用贝塞尔曲线）
                    yAxisID: 'y'
                },
                {
                    label: 'PSNR (dB)',
                    data: metricsData.frames.map(f => f.psnr_y),
                    borderColor: 'rgb(16, 185, 129)',  // Tailwind green-500
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0,
                    yAxisID: 'y1'  // 使用独立 Y 轴（PSNR 量纲不同）
                },
                {
                    label: 'SSIM',
                    data: metricsData.frames.map(f => f.ssim),
                    borderColor: 'rgb(245, 158, 11)',  // Tailwind amber-500
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0,
                    yAxisID: 'y2'  // 使用独立 Y 轴（SSIM 0-1 范围）
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,  // 允许自定义高度
            interaction: {
                mode: 'index',  // 悬停时显示所有数据集
                intersect: false
            },
            plugins: {
                title: {
                    display: true,
                    text: '视频质量指标逐帧分析',
                    font: { size: 16, weight: 'bold' }
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            return `帧号: ${context[0].label}`;
                        },
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                if (label.includes('SSIM')) {
                                    label += context.parsed.y.toFixed(4);
                                } else {
                                    label += context.parsed.y.toFixed(2);
                                }
                            }
                            return label;
                        }
                    }
                },
                legend: {
                    display: true,
                    position: 'top',
                    onClick: (e, legendItem, legend) => {
                        // 自定义图例点击行为（显示/隐藏数据集）
                        const index = legendItem.datasetIndex;
                        const chart = legend.chart;
                        const meta = chart.getDatasetMeta(index);

                        meta.hidden = meta.hidden === null ? !chart.data.datasets[index].hidden : null;
                        chart.update();
                    }
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    title: {
                        display: true,
                        text: '帧号'
                    },
                    ticks: {
                        stepSize: 30  // 每 30 帧显示一个刻度（约 1 秒 @ 30fps）
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'VMAF',
                        color: 'rgb(59, 130, 246)'
                    },
                    ticks: {
                        color: 'rgb(59, 130, 246)'
                    },
                    min: 0,
                    max: 100
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'PSNR (dB)',
                        color: 'rgb(16, 185, 129)'
                    },
                    ticks: {
                        color: 'rgb(16, 185, 129)'
                    },
                    grid: {
                        drawOnChartArea: false  // 避免网格线重叠
                    }
                },
                y2: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'SSIM',
                        color: 'rgb(245, 158, 11)'
                    },
                    ticks: {
                        color: 'rgb(245, 158, 11)'
                    },
                    min: 0,
                    max: 1,
                    grid: {
                        drawOnChartArea: false
                    }
                }
            },
            // 性能优化配置
            parsing: false,  // 禁用自动解析（数据已预处理）
            normalized: true,  // 数据已规范化
            animation: false  // 禁用动画（大数据集）
        }
    });

    return chart;
}
```

### 2. 多参数对比（多条折线叠加）

**用途**：对比不同码率（ABR）或 CRF 值下的质量指标

```javascript
function renderComparisonChart(canvasId, comparisonData) {
    const ctx = document.getElementById(canvasId).getContext('2d');

    // comparisonData 结构示例：
    // [
    //   { label: 'ABR 500kbps', frames: [...] },
    //   { label: 'ABR 1000kbps', frames: [...] },
    //   { label: 'ABR 2000kbps', frames: [...] }
    // ]

    const colors = [
        'rgb(239, 68, 68)',    // red-500
        'rgb(59, 130, 246)',   // blue-500
        'rgb(16, 185, 129)',   // green-500
        'rgb(245, 158, 11)',   // amber-500
        'rgb(139, 92, 246)'    // violet-500
    ];

    const datasets = comparisonData.map((item, index) => ({
        label: item.label,
        data: item.frames.map(f => ({ x: f.frame_number, y: f.vmaf })),
        borderColor: colors[index % colors.length],
        backgroundColor: colors[index % colors.length].replace('rgb', 'rgba').replace(')', ', 0.1)'),
        borderWidth: 2,
        pointRadius: 0,
        tension: 0
    }));

    const chart = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'VMAF 对比（不同码率）'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        title: (context) => `帧号: ${context[0].parsed.x}`,
                        label: (context) => {
                            return `${context.dataset.label}: ${context.parsed.y.toFixed(2)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    title: { display: true, text: '帧号' }
                },
                y: {
                    title: { display: true, text: 'VMAF' },
                    min: 0,
                    max: 100
                }
            },
            parsing: false,
            animation: false
        }
    });

    return chart;
}
```

### 3. 性能指标柱状图

**用途**：对比不同编码参数下的码率、编码时间、速度

```javascript
function renderPerformanceChart(canvasId, performanceData) {
    const ctx = document.getElementById(canvasId).getContext('2d');

    // performanceData 结构示例：
    // [
    //   { label: 'ABR 500kbps', bitrate: 498, encode_time: 45.2, fps: 30.5 },
    //   { label: 'ABR 1000kbps', bitrate: 1002, encode_time: 52.1, fps: 26.4 }
    // ]

    const chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: performanceData.map(d => d.label),
            datasets: [
                {
                    label: '实际码率 (kbps)',
                    data: performanceData.map(d => d.bitrate),
                    backgroundColor: 'rgba(59, 130, 246, 0.8)',
                    yAxisID: 'y'
                },
                {
                    label: '编码时间 (秒)',
                    data: performanceData.map(d => d.encode_time),
                    backgroundColor: 'rgba(16, 185, 129, 0.8)',
                    yAxisID: 'y1'
                },
                {
                    label: '编码速度 (fps)',
                    data: performanceData.map(d => d.fps),
                    backgroundColor: 'rgba(245, 158, 11, 0.8)',
                    yAxisID: 'y2'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: '编码性能对比'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            label += context.parsed.y.toFixed(2);
                            return label;
                        }
                    }
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: { display: true, text: '码率 (kbps)' }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: { display: true, text: '编码时间 (秒)' },
                    grid: { drawOnChartArea: false }
                },
                y2: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: { display: true, text: '编码速度 (fps)' },
                    grid: { drawOnChartArea: false }
                }
            }
        }
    });

    return chart;
}
```

---

## 交互功能实现

### 1. 图例点击切换显示/隐藏

Chart.js 默认支持图例点击切换，但可以自定义：

```javascript
options: {
    plugins: {
        legend: {
            display: true,
            position: 'top',
            onClick: (e, legendItem, legend) => {
                const index = legendItem.datasetIndex;
                const chart = legend.chart;
                const meta = chart.getDatasetMeta(index);

                // 切换可见性
                meta.hidden = meta.hidden === null
                    ? !chart.data.datasets[index].hidden
                    : null;

                chart.update();
            },
            labels: {
                usePointStyle: true,  // 使用圆点样式（更美观）
                padding: 15,
                font: { size: 12 }
            }
        }
    }
}
```

**高级功能：仅显示单个数据集**（点击时隐藏其他所有数据集）

```javascript
onClick: (e, legendItem, legend) => {
    const chart = legend.chart;
    const index = legendItem.datasetIndex;

    if (e.ctrlKey || e.metaKey) {
        // Ctrl/Cmd + 点击：仅显示此数据集
        chart.data.datasets.forEach((dataset, i) => {
            const meta = chart.getDatasetMeta(i);
            meta.hidden = i !== index;
        });
    } else {
        // 普通点击：切换当前数据集
        const meta = chart.getDatasetMeta(index);
        meta.hidden = meta.hidden === null
            ? !chart.data.datasets[index].hidden
            : null;
    }

    chart.update();
}
```

### 2. 工具提示（Tooltip）增强

#### 显示帧号与多指标值

```javascript
options: {
    plugins: {
        tooltip: {
            enabled: true,
            mode: 'index',  // 显示所有数据集在同一 X 坐标的值
            intersect: false,  // 不需要精确悬停在点上
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: '#fff',
            bodyColor: '#fff',
            borderColor: 'rgba(255, 255, 255, 0.3)',
            borderWidth: 1,
            padding: 12,
            callbacks: {
                title: function(context) {
                    const frameNumber = context[0].label;
                    const timeSeconds = (frameNumber / 30).toFixed(2);  // 假设 30fps
                    return `帧号: ${frameNumber} (${timeSeconds}s)`;
                },
                label: function(context) {
                    let label = context.dataset.label || '';
                    if (label) {
                        label += ': ';
                    }

                    const value = context.parsed.y;

                    // 根据指标类型格式化
                    if (label.includes('SSIM')) {
                        label += value.toFixed(4);
                    } else if (label.includes('PSNR')) {
                        label += value.toFixed(2) + ' dB';
                    } else if (label.includes('VMAF')) {
                        label += value.toFixed(2);
                    } else {
                        label += value.toFixed(2);
                    }

                    return label;
                },
                afterBody: function(context) {
                    // 额外信息（可选）
                    const frameNumber = context[0].label;
                    const frameData = metricsData.frames.find(f => f.frame_number == frameNumber);

                    if (frameData && frameData.encoding_time_ms) {
                        return `编码耗时: ${frameData.encoding_time_ms.toFixed(1)} ms`;
                    }
                    return '';
                }
            }
        }
    }
}
```

#### 自定义 HTML 工具提示（高级）

```javascript
// 创建自定义 HTML 工具提示
const getOrCreateTooltip = (chart) => {
    let tooltipEl = chart.canvas.parentNode.querySelector('div.chartjs-tooltip');

    if (!tooltipEl) {
        tooltipEl = document.createElement('div');
        tooltipEl.className = 'chartjs-tooltip';
        tooltipEl.style.background = 'rgba(0, 0, 0, 0.8)';
        tooltipEl.style.borderRadius = '6px';
        tooltipEl.style.color = 'white';
        tooltipEl.style.opacity = 1;
        tooltipEl.style.pointerEvents = 'none';
        tooltipEl.style.position = 'absolute';
        tooltipEl.style.transform = 'translate(-50%, 0)';
        tooltipEl.style.transition = 'all .1s ease';
        tooltipEl.style.padding = '12px';
        tooltipEl.style.fontSize = '14px';

        const table = document.createElement('table');
        table.style.margin = '0px';

        tooltipEl.appendChild(table);
        chart.canvas.parentNode.appendChild(tooltipEl);
    }

    return tooltipEl;
};

const externalTooltipHandler = (context) => {
    const {chart, tooltip} = context;
    const tooltipEl = getOrCreateTooltip(chart);

    if (tooltip.opacity === 0) {
        tooltipEl.style.opacity = 0;
        return;
    }

    // 设置内容
    if (tooltip.body) {
        const titleLines = tooltip.title || [];
        const bodyLines = tooltip.body.map(b => b.lines);

        let innerHtml = '<thead>';
        titleLines.forEach(title => {
            innerHtml += '<tr><th style="padding: 4px 8px; font-weight: bold;">' + title + '</th></tr>';
        });
        innerHtml += '</thead><tbody>';

        bodyLines.forEach((body, i) => {
            const colors = tooltip.labelColors[i];
            let style = 'background:' + colors.backgroundColor;
            style += '; border-color:' + colors.borderColor;
            style += '; border-width: 2px';
            style += '; display: inline-block';
            style += '; width: 10px; height: 10px; margin-right: 8px';
            const span = '<span style="' + style + '"></span>';
            innerHtml += '<tr><td style="padding: 4px 8px;">' + span + body + '</td></tr>';
        });
        innerHtml += '</tbody>';

        const tableRoot = tooltipEl.querySelector('table');
        tableRoot.innerHTML = innerHtml;
    }

    const {offsetLeft: positionX, offsetTop: positionY} = chart.canvas;

    tooltipEl.style.opacity = 1;
    tooltipEl.style.left = positionX + tooltip.caretX + 'px';
    tooltipEl.style.top = positionY + tooltip.caretY + 'px';
};

// 在图表配置中使用
options: {
    plugins: {
        tooltip: {
            enabled: false,  // 禁用默认工具提示
            external: externalTooltipHandler
        }
    }
}
```

### 3. 导出 PNG 功能

```html
<!-- 添加导出按钮 -->
<div class="flex justify-end mb-4">
    <button
        id="exportBtn"
        class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition"
        onclick="exportChartAsPNG('psnrChart', 'quality_metrics.png')">
        下载为 PNG
    </button>
</div>

<canvas id="psnrChart"></canvas>
```

```javascript
// frontend/static/js/charts.js

/**
 * 导出 Chart.js 图��为 PNG 图片
 * @param {string} canvasId - Canvas 元素的 ID
 * @param {string} filename - 保存的文件名
 */
function exportChartAsPNG(canvasId, filename = 'chart.png') {
    const canvas = document.getElementById(canvasId);

    if (!canvas) {
        console.error('Canvas not found:', canvasId);
        return;
    }

    // 方法 1：使用 Chart.js 内置方法（推荐）
    const chartInstance = Chart.getChart(canvasId);
    if (chartInstance) {
        const url = chartInstance.toBase64Image();
        downloadImage(url, filename);
    } else {
        // 方法 2：直接使用 Canvas API
        canvas.toBlob(function(blob) {
            const url = URL.createObjectURL(blob);
            downloadImage(url, filename);
            URL.revokeObjectURL(url);  // 释放内存
        });
    }
}

/**
 * 下载图片的辅助函数
 * @param {string} url - Data URL 或 Blob URL
 * @param {string} filename - 保存的文件名
 */
function downloadImage(url, filename) {
    const link = document.createElement('a');
    link.download = filename;
    link.href = url;
    link.click();
}

// 高级功能：导出高分辨率图片（2x/3x DPI）
function exportHighResChart(canvasId, filename = 'chart.png', scale = 2) {
    const chartInstance = Chart.getChart(canvasId);
    if (!chartInstance) return;

    const originalCanvas = chartInstance.canvas;
    const originalWidth = originalCanvas.width;
    const originalHeight = originalCanvas.height;

    // 创建临时高分辨率 Canvas
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = originalWidth * scale;
    tempCanvas.height = originalHeight * scale;

    const tempCtx = tempCanvas.getContext('2d');
    tempCtx.scale(scale, scale);

    // 重绘图表到高分辨率 Canvas
    tempCtx.drawImage(originalCanvas, 0, 0);

    // 导出
    tempCanvas.toBlob(function(blob) {
        const url = URL.createObjectURL(blob);
        downloadImage(url, filename);
        URL.revokeObjectURL(url);
    });
}
```

**浏览器兼容性处理**（IE/Edge）：

```javascript
function exportChartAsPNG_IE_Compatible(canvasId, filename) {
    const canvas = document.getElementById(canvasId);

    if (window.navigator.msSaveBlob) {
        // IE/Edge 专用方法
        canvas.toBlob(function(blob) {
            window.navigator.msSaveBlob(blob, filename);
        });
    } else {
        // 现代浏览器
        canvas.toBlob(function(blob) {
            const url = URL.createObjectURL(blob);
            downloadImage(url, filename);
            URL.revokeObjectURL(url);
        });
    }
}
```

---

## 样式定制与响应式设计

### 1. 与 Tailwind CSS 集成

#### HTML 结构

```html
<!-- report.html.jinja2 -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>质量指标报告 - {{ job_id }}</title>

    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>

    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head>
<body class="bg-gray-50 min-h-screen">
    <div class="container mx-auto px-4 py-8 max-w-7xl">
        <!-- 头部 -->
        <header class="mb-8">
            <h1 class="text-3xl font-bold text-gray-900">视频质量指标报告</h1>
            <p class="text-gray-600 mt-2">任务 ID: {{ job_id }}</p>
        </header>

        <!-- 图表容器 -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- 质量指标曲线 -->
            <div class="bg-white rounded-lg shadow-md p-6">
                <div class="flex justify-between items-center mb-4">
                    <h2 class="text-xl font-semibold text-gray-800">质量指标曲线</h2>
                    <button
                        onclick="exportChartAsPNG('qualityChart', 'quality_metrics.png')"
                        class="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 transition">
                        导出 PNG
                    </button>
                </div>
                <!-- 响应式容器 -->
                <div class="relative h-80 lg:h-96">
                    <canvas id="qualityChart"></canvas>
                </div>
            </div>

            <!-- 性能对比图 -->
            <div class="bg-white rounded-lg shadow-md p-6">
                <div class="flex justify-between items-center mb-4">
                    <h2 class="text-xl font-semibold text-gray-800">编码性能对比</h2>
                    <button
                        onclick="exportChartAsPNG('performanceChart', 'performance.png')"
                        class="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 transition">
                        导出 PNG
                    </button>
                </div>
                <div class="relative h-80 lg:h-96">
                    <canvas id="performanceChart"></canvas>
                </div>
            </div>
        </div>

        <!-- 全宽对比图 -->
        <div class="bg-white rounded-lg shadow-md p-6 mt-6">
            <h2 class="text-xl font-semibold text-gray-800 mb-4">多参数 VMAF 对比</h2>
            <div class="relative h-96">
                <canvas id="comparisonChart"></canvas>
            </div>
        </div>
    </div>

    <script>
        const metricsData = {{ metrics_json | tojson }};
    </script>
    <script src="/static/js/charts.js"></script>
</body>
</html>
```

### 2. 响应式布局配置

#### Chart.js 响应式设置

```javascript
options: {
    responsive: true,
    maintainAspectRatio: false,  // 关键！允许容器控制高度

    // 响应式回调（可选）
    onResize: function(chart, size) {
        console.log('图表尺寸变化:', size.width, size.height);

        // 根据屏幕宽度调整配置
        if (size.width < 640) {
            // 移动端：隐藏部分元素
            chart.options.plugins.legend.display = false;
            chart.options.scales.x.ticks.maxTicksLimit = 5;
        } else {
            // 桌面端：显示所有元素
            chart.options.plugins.legend.display = true;
            chart.options.scales.x.ticks.maxTicksLimit = 10;
        }

        chart.update('none');  // 不触发动画
    }
}
```

#### CSS 容器最佳实践

```html
<!-- 错误示例：Canvas 直接设置尺寸（会导致模糊） -->
<canvas id="chart" width="800" height="400"></canvas>

<!-- ✅ 正确示例：使用容器控制尺寸 -->
<div class="relative w-full h-80">
    <canvas id="chart"></canvas>
</div>
```

**关键 CSS 规则**：

```css
/* 图表容器必须有明确的高度 */
.chart-container {
    position: relative;
    width: 100%;
    height: 20rem;  /* 或使用 Tailwind 的 h-80 */
}

/* 移动端适配 */
@media (max-width: 640px) {
    .chart-container {
        height: 16rem;  /* 移动端稍矮 */
    }
}
```

### 3. 配色方案

#### Tailwind 风格配色

```javascript
const tailwindColors = {
    primary: {
        light: 'rgba(59, 130, 246, 0.1)',   // blue-500 背景
        main: 'rgb(59, 130, 246)',          // blue-500
        dark: 'rgb(29, 78, 216)'            // blue-700
    },
    success: {
        light: 'rgba(16, 185, 129, 0.1)',   // green-500 背景
        main: 'rgb(16, 185, 129)',          // green-500
        dark: 'rgb(5, 150, 105)'            // green-700
    },
    warning: {
        light: 'rgba(245, 158, 11, 0.1)',   // amber-500 背景
        main: 'rgb(245, 158, 11)',          // amber-500
        dark: 'rgb(217, 119, 6)'            // amber-700
    },
    danger: {
        light: 'rgba(239, 68, 68, 0.1)',    // red-500 背景
        main: 'rgb(239, 68, 68)',           // red-500
        dark: 'rgb(220, 38, 38)'            // red-700
    },
    violet: {
        light: 'rgba(139, 92, 246, 0.1)',   // violet-500 背景
        main: 'rgb(139, 92, 246)',          // violet-500
        dark: 'rgb(109, 40, 217)'           // violet-700
    }
};

// 用于多参数对比的颜色序列
const comparisonColors = [
    tailwindColors.danger.main,    // 红色：低码率
    tailwindColors.warning.main,   // 橙色：中码率
    tailwindColors.success.main,   // 绿色：高码率
    tailwindColors.primary.main,   // 蓝色：额外参数 1
    tailwindColors.violet.main     // 紫色：额外参数 2
];
```

#### 可访问性（色盲友好）

```javascript
const colorBlindSafeColors = [
    '#0173B2',  // 蓝色
    '#DE8F05',  // 橙色
    '#029E73',  // 青绿色
    '#CC78BC',  // 紫色
    '#CA9161',  // 褐色
    '#FBAFE4',  // 粉色
    '#949494',  // 灰色
    '#ECE133'   // 黄色
];
```

### 4. 移动端优化

```javascript
function isMobile() {
    return window.innerWidth < 768;  // Tailwind md 断点
}

function getResponsiveChartOptions() {
    const baseOptions = { /* ... */ };

    if (isMobile()) {
        return {
            ...baseOptions,
            plugins: {
                ...baseOptions.plugins,
                legend: {
                    display: true,
                    position: 'bottom',  // 移动端图例放底部
                    labels: {
                        boxWidth: 12,
                        font: { size: 10 },
                        padding: 8
                    }
                },
                title: {
                    font: { size: 14 }
                }
            },
            scales: {
                ...baseOptions.scales,
                x: {
                    ...baseOptions.scales.x,
                    ticks: {
                        maxTicksLimit: 5,  // 减少刻度数量
                        font: { size: 10 }
                    }
                },
                y: {
                    ...baseOptions.scales.y,
                    ticks: {
                        font: { size: 10 }
                    }
                }
            }
        };
    }

    return baseOptions;
}

// 使用示例
const chart = new Chart(ctx, {
    type: 'line',
    data: chartData,
    options: getResponsiveChartOptions()
});

// 监听屏幕尺寸变化
window.addEventListener('resize', () => {
    chart.options = getResponsiveChartOptions();
    chart.update('none');
});
```

---

## 性能优化策略

### 1. 大数据量渲染优化（数千帧）

#### 启用数据抽取（Decimation）

```javascript
options: {
    plugins: {
        decimation: {
            enabled: true,
            algorithm: 'lttb',  // 可选: 'lttb', 'min-max'
            samples: 500,  // 最多显示 500 个点（原始数据可能有数千个）
            threshold: 1000  // 当数据超过 1000 个点时启用抽取
        }
    }
}
```

**抽取算法对比**：

| 算法 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| `min-max` | 波动大的数据（VMAF 帧间波动） | 保留峰值和谷值，不丢失极端值 | 可能过度保留噪声 |
| `lttb` (Largest Triangle Three Buckets) | 平滑趋势数据（平均 PSNR） | 视觉效果最佳，保留趋势形状 | 计算开销稍高 |

#### 禁用动画

```javascript
options: {
    animation: false,  // 完全禁用动画

    // 或仅禁用初始动画
    animation: {
        onComplete: () => {
            // 动画完成后的回调
        },
        duration: 0  // 动画时长设为 0
    }
}
```

#### 禁用点渲染

```javascript
datasets: [{
    label: 'VMAF',
    data: [...],
    pointRadius: 0,  // 隐藏所有点
    pointHoverRadius: 4,  // 悬停时显示
    hitRadius: 10  // 增大点击响应区域
}]
```

#### 禁用贝塞尔曲线

```javascript
datasets: [{
    label: 'VMAF',
    data: [...],
    tension: 0,  // 直线连接（默认），不使用贝塞尔曲线
    cubicInterpolationMode: 'default'  // 或 'monotone'
}]
```

### 2. 数据预处理优化

#### 后端预计算（推荐）

```python
# backend/src/services/metrics_service.py

def prepare_chart_data(metrics: VideoMetrics) -> dict:
    """预处理数据为 Chart.js 所需格式，减少前端计算"""

    # 抽取数据（服务端抽取比客户端更高效）
    if len(metrics.frames) > 1000:
        frames = decimate_frames(metrics.frames, target_count=500)
    else:
        frames = metrics.frames

    return {
        "labels": [f.frame_number for f in frames],
        "datasets": {
            "vmaf": [f.vmaf for f in frames],
            "psnr_y": [f.psnr_y for f in frames],
            "ssim": [f.ssim for f in frames]
        }
    }

def decimate_frames(frames: List[FrameMetrics], target_count: int) -> List[FrameMetrics]:
    """使用 LTTB 算法抽取帧数据"""
    from lttbc import lttb  # pip install lttbc

    # 转换为 [(x, y), ...] 格式
    data = [(f.frame_number, f.vmaf) for f in frames]
    decimated = lttb(data, target_count)

    # 根据抽取后的帧号筛选原始数据
    selected_frame_numbers = set(x for x, y in decimated)
    return [f for f in frames if f.frame_number in selected_frame_numbers]
```

#### 前端数据格式优化

```javascript
// ❌ 低效：每次访问都需要计算
const labels = metricsData.frames.map(f => f.frame_number);
const vmafData = metricsData.frames.map(f => f.vmaf);

// ✅ 高效：使用预处理的数组
const chartData = {
    labels: metricsData.labels,  // 后端已准备好
    datasets: [{
        label: 'VMAF',
        data: metricsData.datasets.vmaf  // 后端已准备好
    }]
};
```

### 3. 懒加载/分页策略

#### 按需加载不同指标

```javascript
let currentMetric = 'vmaf';
let chartInstance = null;

async function switchMetric(metricName) {
    if (currentMetric === metricName) return;

    // 显示加载状态
    showLoading();

    try {
        // 仅加载需要的指标数据
        const response = await fetch(`/jobs/${jobId}/${metricName}.json`);
        const data = await response.json();

        // 更新图表
        if (chartInstance) {
            chartInstance.data.datasets[0].data = data.values;
            chartInstance.update('none');  // 不触发动画
        } else {
            chartInstance = renderChart(data);
        }

        currentMetric = metricName;
    } catch (error) {
        console.error('加载失败:', error);
        showError('无法加载指标数据');
    } finally {
        hideLoading();
    }
}

// HTML
// <button onclick="switchMetric('vmaf')">VMAF</button>
// <button onclick="switchMetric('psnr')">PSNR</button>
// <button onclick="switchMetric('ssim')">SSIM</button>
```

#### 时间范围分页

```javascript
let currentPage = 0;
const framesPerPage = 300;  // 每页显示 300 帧（约 10 秒 @ 30fps）

function loadPage(pageNumber) {
    const startFrame = pageNumber * framesPerPage;
    const endFrame = startFrame + framesPerPage;

    const pageData = {
        labels: allData.frames.slice(startFrame, endFrame).map(f => f.frame_number),
        datasets: [{
            label: 'VMAF',
            data: allData.frames.slice(startFrame, endFrame).map(f => f.vmaf)
        }]
    };

    chartInstance.data = pageData;
    chartInstance.update();

    // 更新分页控件
    document.getElementById('pageInfo').textContent =
        `帧 ${startFrame} - ${endFrame} / 共 ${allData.frames.length}`;
}
```

### 4. 渲染优化技巧

#### 使用 `parsing: false` 和 `normalized: true`

```javascript
// 确保数据格式与 Chart.js 期望一致
const optimizedData = metricsData.frames.map(f => ({
    x: f.frame_number,
    y: f.vmaf
}));

const chart = new Chart(ctx, {
    type: 'line',
    data: {
        datasets: [{
            label: 'VMAF',
            data: optimizedData,
            parsing: false,  // 禁用自动解析（数据已是 {x, y} 格式）
            normalized: true  // 数据已排序且唯一
        }]
    }
});
```

#### 更新策略优化

```javascript
// ❌ 低效：完全重绘
chart.destroy();
chart = new Chart(ctx, newConfig);

// ✅ 高效：仅更新数据
chart.data.datasets[0].data = newData;
chart.update('none');  // 使用 'none' 模式跳过动画

// ✅ 高效：仅更新坐标轴（缩放场景）
chart.options.scales.x.min = newMin;
chart.options.scales.x.max = newMax;
chart.update('none');
```

#### 使用 Web Worker（高级）

```javascript
// worker.js
self.onmessage = function(e) {
    const { frames, metric } = e.data;

    // 在后台线程中处理数据
    const processedData = frames.map(f => ({
        x: f.frame_number,
        y: f[metric]
    }));

    self.postMessage(processedData);
};

// main.js
const worker = new Worker('/static/js/worker.js');

worker.onmessage = function(e) {
    const processedData = e.data;
    chart.data.datasets[0].data = processedData;
    chart.update();
};

worker.postMessage({ frames: metricsData.frames, metric: 'vmaf' });
```

---

## 完整代码示例

### 后端代码（FastAPI + Jinja2）

```python
# backend/src/api/routes.py
from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
import json
import os

router = APIRouter()
templates = Jinja2Templates(directory="backend/src/templates")

@router.get("/jobs/{job_id}/report")
async def get_report(request: Request, job_id: str):
    """渲染质量指标报告页面"""

    # 加载指标数据
    metrics_file = f"jobs/{job_id}/metrics.json"
    if not os.path.exists(metrics_file):
        raise HTTPException(status_code=404, detail="Metrics not found")

    with open(metrics_file) as f:
        metrics = json.load(f)

    # 预处理数据（抽取、格式化）
    chart_data = prepare_chart_data(metrics)

    return templates.TemplateResponse(
        "report.html.jinja2",
        {
            "request": request,
            "job_id": job_id,
            "video_name": metrics.get("video_name"),
            "metrics_summary": metrics.get("summary"),
            "chart_data_json": json.dumps(chart_data)  # 序列化为 JSON 字符串
        }
    )

@router.get("/jobs/{job_id}/metrics.json")
async def get_metrics_json(job_id: str):
    """返回原始 JSON 数据（供 AJAX 调用）"""
    metrics_file = f"jobs/{job_id}/metrics.json"
    if not os.path.exists(metrics_file):
        raise HTTPException(status_code=404, detail="Metrics not found")

    with open(metrics_file) as f:
        data = json.load(f)

    return JSONResponse(content=data)

def prepare_chart_data(metrics: dict) -> dict:
    """预处理数据为 Chart.js 所需格式"""
    frames = metrics.get("frames", [])

    # 数据抽取（如果帧数过多）
    if len(frames) > 1000:
        # 简单抽取：每 N 帧取一个
        step = len(frames) // 500
        frames = frames[::step]

    return {
        "labels": [f["frame_number"] for f in frames],
        "vmaf": [f["vmaf"] for f in frames],
        "psnr_y": [f["psnr_y"] for f in frames],
        "ssim": [f["ssim"] for f in frames]
    }
```

### 前端代码（HTML + JavaScript）

```html
<!-- backend/src/templates/report.html.jinja2 -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>质量指标报告 - {{ job_id }}</title>

    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>

    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head>
<body class="bg-gray-50 min-h-screen">
    <div class="container mx-auto px-4 py-8 max-w-7xl">
        <!-- 头部 -->
        <header class="mb-8">
            <h1 class="text-3xl font-bold text-gray-900">视频质量指标报告</h1>
            <div class="mt-2 text-gray-600">
                <p>任务 ID: <span class="font-mono">{{ job_id }}</span></p>
                <p>视频文件: {{ video_name }}</p>
            </div>
        </header>

        <!-- 统计摘要 -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <div class="bg-white rounded-lg shadow p-6">
                <h3 class="text-sm font-medium text-gray-500">平均 VMAF</h3>
                <p class="mt-2 text-3xl font-semibold text-blue-600">
                    {{ "%.2f"|format(metrics_summary.avg_vmaf) }}
                </p>
            </div>
            <div class="bg-white rounded-lg shadow p-6">
                <h3 class="text-sm font-medium text-gray-500">平均 PSNR (Y)</h3>
                <p class="mt-2 text-3xl font-semibold text-green-600">
                    {{ "%.2f"|format(metrics_summary.avg_psnr_y) }} dB
                </p>
            </div>
            <div class="bg-white rounded-lg shadow p-6">
                <h3 class="text-sm font-medium text-gray-500">平均 SSIM</h3>
                <p class="mt-2 text-3xl font-semibold text-amber-600">
                    {{ "%.4f"|format(metrics_summary.avg_ssim) }}
                </p>
            </div>
        </div>

        <!-- 质量指标曲线 -->
        <div class="bg-white rounded-lg shadow-md p-6 mb-6">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-xl font-semibold text-gray-800">质量指标逐帧分析</h2>
                <button
                    onclick="exportChartAsPNG('qualityChart', 'quality_metrics.png')"
                    class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition">
                    导出为 PNG
                </button>
            </div>
            <div class="relative h-96">
                <canvas id="qualityChart"></canvas>
            </div>
        </div>
    </div>

    <script>
        // 从后端传递数据到前端
        const chartData = {{ chart_data_json | tojson }};
        const jobId = {{ job_id | tojson }};

        console.log('加载数据:', chartData.labels.length, '帧');
    </script>

    <script src="/static/js/charts.js"></script>
</body>
</html>
```

```javascript
// frontend/static/js/charts.js

/**
 * 渲染质量指标图表
 */
function renderQualityChart() {
    const ctx = document.getElementById('qualityChart').getContext('2d');

    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartData.labels,
            datasets: [
                {
                    label: 'VMAF',
                    data: chartData.vmaf,
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    tension: 0,
                    yAxisID: 'y'
                },
                {
                    label: 'PSNR (Y通道)',
                    data: chartData.psnr_y,
                    borderColor: 'rgb(16, 185, 129)',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    tension: 0,
                    yAxisID: 'y1'
                },
                {
                    label: 'SSIM',
                    data: chartData.ssim,
                    borderColor: 'rgb(245, 158, 11)',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    tension: 0,
                    yAxisID: 'y2'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                title: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            const frameNumber = context[0].label;
                            const timeSeconds = (frameNumber / 30).toFixed(2);
                            return `帧号: ${frameNumber} (${timeSeconds}s)`;
                        },
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            const value = context.parsed.y;

                            if (label.includes('SSIM')) {
                                label += value.toFixed(4);
                            } else if (label.includes('PSNR')) {
                                label += value.toFixed(2) + ' dB';
                            } else {
                                label += value.toFixed(2);
                            }

                            return label;
                        }
                    }
                },
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: '帧号'
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'VMAF',
                        color: 'rgb(59, 130, 246)'
                    },
                    ticks: {
                        color: 'rgb(59, 130, 246)'
                    },
                    min: 0,
                    max: 100
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'PSNR (dB)',
                        color: 'rgb(16, 185, 129)'
                    },
                    ticks: {
                        color: 'rgb(16, 185, 129)'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                },
                y2: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'SSIM',
                        color: 'rgb(245, 158, 11)'
                    },
                    ticks: {
                        color: 'rgb(245, 158, 11)'
                    },
                    min: 0,
                    max: 1,
                    grid: {
                        drawOnChartArea: false
                    }
                }
            },
            // 性能优化
            parsing: false,
            normalized: true,
            animation: false
        }
    });

    return chart;
}

/**
 * 导出图表为 PNG
 */
function exportChartAsPNG(canvasId, filename) {
    const chartInstance = Chart.getChart(canvasId);
    if (!chartInstance) {
        console.error('Chart not found:', canvasId);
        return;
    }

    const url = chartInstance.toBase64Image();
    const link = document.createElement('a');
    link.download = filename;
    link.href = url;
    link.click();
}

// 页面加载完成后渲染图表
document.addEventListener('DOMContentLoaded', function() {
    renderQualityChart();
});
```

---

## 常见陷阱与最佳实践

### ❌ 常见陷阱

#### 1. 响应式失效（Canvas 模糊）

**错误做法**：
```html
<!-- ❌ 直接在 Canvas 上设置尺寸属性 -->
<canvas id="chart" width="800" height="400"></canvas>
```

**正确做法**：
```html
<!-- ✅ 使用容器控制尺寸 -->
<div class="relative w-full h-80">
    <canvas id="chart"></canvas>
</div>
```

```javascript
options: {
    responsive: true,
    maintainAspectRatio: false  // 必须设置
}
```

#### 2. Jinja2 数据传递错误

**错误做法**：
```html
<!-- ❌ 直接输出 Python 对象（会导致 JavaScript 解析错误） -->
<script>
    const data = {{ metrics }};  // 错误！
</script>
```

**正确做法**：
```html
<!-- ✅ 使用 tojson 过滤器 -->
<script>
    const data = {{ metrics_json | tojson }};
</script>
```

#### 3. XSS 安全隐患

**错误做法**：
```html
<!-- ❌ 使用 safe 过滤器（绕过转义） -->
<script>
    const data = {{ user_input | safe }};  // 危险！
</script>
```

**正确做法**：
```html
<!-- ✅ 始终使用 tojson（自动转义） -->
<script>
    const data = {{ user_input | tojson }};
</script>
```

#### 4. 性能问题（大数据未优化）

**错误做法**：
```javascript
// ❌ 渲染所有 10000 个点
datasets: [{
    data: allFrames.map(f => f.vmaf),  // 10000 个点
    pointRadius: 5  // 每个点都渲染
}]
```

**正确做法**：
```javascript
// ✅ 启用数据抽取 + 隐藏点
options: {
    plugins: {
        decimation: {
            enabled: true,
            algorithm: 'lttb',
            samples: 500
        }
    }
},
datasets: [{
    data: allFrames.map(f => f.vmaf),
    pointRadius: 0,  // 隐藏点
    tension: 0  // 禁用贝塞尔曲线
}]
```

#### 5. 内存泄漏

**错误做法**：
```javascript
// ❌ 重复创建图表而不销毁
function updateChart() {
    new Chart(ctx, config);  // 每次都创建新实例
}
```

**正确做法**：
```javascript
// ✅ 复用或先销毁
let chartInstance = null;

function updateChart() {
    if (chartInstance) {
        chartInstance.destroy();
    }
    chartInstance = new Chart(ctx, config);
}

// 或仅更新数据
function updateChartData(newData) {
    chartInstance.data.datasets[0].data = newData;
    chartInstance.update('none');
}
```

---

### ✅ 最佳实践清单

#### 开发阶段

- [ ] 使用 CDN 快速原型（开发环境）
- [ ] 在浏览器控制台验证 `chartData` 对象结构
- [ ] 使用 Chart.js DevTools（浏览器扩展）调试配置
- [ ] 先实现基础功能，后优化性能

#### 数据传递

- [ ] 后端使用 `tojson` 过滤器转义 JSON
- [ ] 前端验证数据完整性��检查 `null`/`undefined`）
- [ ] 大数据量在后端预处理（抽取、格式化）
- [ ] 敏感数据不要暴露到前端 JavaScript

#### 性能优化

- [ ] 数据超过 1000 个点时启用 decimation
- [ ] 设置 `pointRadius: 0` 隐藏点
- [ ] 设置 `tension: 0` 禁用贝塞尔曲线
- [ ] 设置 `animation: false` 禁用动画
- [ ] 使用 `parsing: false` 和 `normalized: true`

#### 响应式设计

- [ ] 设置 `maintainAspectRatio: false`
- [ ] 容器使用 `position: relative` 和明确高度
- [ ] 移动端调整图例位置（`position: 'bottom'`）
- [ ] 监听 `onResize` 回调调整配置

#### 可访问性

- [ ] 使用色盲友好配色方案
- [ ] 提供数据表格作为备选（`<table>`）
- [ ] 键盘导航支持（图例、工具提示）
- [ ] 提供文本描述（`<figcaption>`）

#### 生产部署

- [ ] 本地托管 Chart.js（避免 CDN 故障）
- [ ] 启用 gzip/Brotli 压缩
- [ ] 设置 CDN 缓存头（`Cache-Control: public, max-age=31536000`）
- [ ] 监控图表渲染性能（`performance.now()`）

---

## 参考资源

### 官方文档

- [Chart.js 官方文档](https://www.chartjs.org/docs/latest/)
- [Chart.js 性能优化](https://www.chartjs.org/docs/latest/general/performance.html)
- [Chart.js 响应式配置](https://www.chartjs.org/docs/latest/configuration/responsive.html)
- [Jinja2 模板文档](https://jinja.palletsprojects.com/)

### 社区资源

- [Chart.js GitHub](https://github.com/chartjs/Chart.js)
- [Chart.js Samples](https://www.chartjs.org/docs/latest/samples/)
- [Stack Overflow Chart.js 标签](https://stackoverflow.com/questions/tagged/chart.js)

### 工具

- [Chart.js 配置生成器](https://www.chartjs.org/docs/latest/getting-started/)
- [LTTB 算法库](https://github.com/sveinn-steinarsson/flot-downsample)
- [Color Brewer（配色方案）](https://colorbrewer2.org/)

---

## 总结

本研究文档为 VQMR 项目提供了完整的 Chart.js 集成方案，涵盖：

1. **技术选型**：Chart.js 轻量级、易用、响应式，适合 VQMR 场景
2. **数据传递**：后端 FastAPI + Jinja2 `tojson` 过滤器安全传递数据
3. **图表配置**：逐帧曲线、多参数对比、性能柱状图三种核心图表
4. **交互功能**：图例切换、增强工具提示、PNG 导出
5. **样式定制**：Tailwind CSS 集成、响应式布局、移动端优化
6. **性能优化**：数据抽取、禁用动画、后端预处理、懒加载

**关键优势**：
- ✅ 符合宪法"最少依赖"原则（仅 Chart.js + Tailwind CDN）
- ✅ 前后端分离但无需 SPA 框架（服务端渲染）
- ✅ 支持数千帧数据可视化（通过 decimation 优化）
- ✅ 响应式设计与 Tailwind CSS 无缝集成
- ✅ 安全数据传递（Jinja2 自动转义）

**下一步行动**：
1. 在 `/speckit.plan` Phase 1 中纳入此研究结论
2. 创建 Chart.js 配置模板（`frontend/static/js/charts.js`）
3. 在报告模板中集成图表容器（`backend/src/templates/report.html.jinja2`）
4. 编写集成测试验证图表渲染功能
