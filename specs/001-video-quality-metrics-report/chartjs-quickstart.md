# Chart.js 快速上手指南

**适用场景**: VQMR 视频质量指标可视化
**目标读者**: 项目开发者（Python/JavaScript）

---

## 1. 最小化实现（5 分钟）

### HTML 模板

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>质量指标报告</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head>
<body class="bg-gray-50 p-8">
    <div class="max-w-4xl mx-auto bg-white rounded-lg shadow p-6">
        <h1 class="text-2xl font-bold mb-4">VMAF 质量曲线</h1>
        <div class="relative h-96">
            <canvas id="vmafChart"></canvas>
        </div>
    </div>

    <script>
        // 从后端传递数据
        const metricsData = {{ metrics_json | tojson }};

        // 渲染图表
        const ctx = document.getElementById('vmafChart').getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: metricsData.frames.map(f => f.frame_number),
                datasets: [{
                    label: 'VMAF',
                    data: metricsData.frames.map(f => f.vmaf),
                    borderColor: 'rgb(59, 130, 246)',
                    borderWidth: 2,
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    </script>
</body>
</html>
```

### 后端路由（FastAPI）

```python
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
import json

router = APIRouter()
templates = Jinja2Templates(directory="backend/src/templates")

@router.get("/jobs/{job_id}/report")
async def get_report(request: Request, job_id: str):
    with open(f"jobs/{job_id}/metrics.json") as f:
        metrics = json.load(f)

    return templates.TemplateResponse(
        "report.html.jinja2",
        {
            "request": request,
            "metrics_json": json.dumps(metrics)
        }
    )
```

---

## 2. 多指标叠加（3 个 Y 轴）

```javascript
new Chart(ctx, {
    type: 'line',
    data: {
        labels: frames.map(f => f.frame_number),
        datasets: [
            {
                label: 'VMAF',
                data: frames.map(f => f.vmaf),
                borderColor: 'rgb(59, 130, 246)',
                yAxisID: 'y'
            },
            {
                label: 'PSNR (dB)',
                data: frames.map(f => f.psnr_y),
                borderColor: 'rgb(16, 185, 129)',
                yAxisID: 'y1'
            },
            {
                label: 'SSIM',
                data: frames.map(f => f.ssim),
                borderColor: 'rgb(245, 158, 11)',
                yAxisID: 'y2'
            }
        ]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            y: {
                position: 'left',
                title: { display: true, text: 'VMAF' },
                min: 0,
                max: 100
            },
            y1: {
                position: 'right',
                title: { display: true, text: 'PSNR (dB)' },
                grid: { drawOnChartArea: false }
            },
            y2: {
                position: 'right',
                title: { display: true, text: 'SSIM' },
                min: 0,
                max: 1,
                grid: { drawOnChartArea: false }
            }
        }
    }
});
```

---

## 3. 性能优化（处理数千帧）

### 必须配置

```javascript
options: {
    animation: false,  // 禁用动画
    parsing: false,    // 禁用自动解析
    plugins: {
        decimation: {
            enabled: true,
            algorithm: 'lttb',
            samples: 500
        }
    }
}

datasets: [{
    pointRadius: 0,    // 隐藏点
    tension: 0         // 直线连接
}]
```

### 后端预处理（推荐）

```python
def prepare_chart_data(metrics: dict) -> dict:
    frames = metrics["frames"]

    # 抽取数据（超过 1000 帧时）
    if len(frames) > 1000:
        step = len(frames) // 500
        frames = frames[::step]

    return {
        "labels": [f["frame_number"] for f in frames],
        "vmaf": [f["vmaf"] for f in frames],
        "psnr_y": [f["psnr_y"] for f in frames],
        "ssim": [f["ssim"] for f in frames]
    }
```

---

## 4. 交互功能

### 工具提示增强

```javascript
options: {
    plugins: {
        tooltip: {
            callbacks: {
                title: (context) => {
                    const frame = context[0].label;
                    const time = (frame / 30).toFixed(2);
                    return `帧号: ${frame} (${time}s)`;
                },
                label: (context) => {
                    const label = context.dataset.label;
                    const value = context.parsed.y;

                    if (label.includes('SSIM')) {
                        return `${label}: ${value.toFixed(4)}`;
                    } else if (label.includes('PSNR')) {
                        return `${label}: ${value.toFixed(2)} dB`;
                    } else {
                        return `${label}: ${value.toFixed(2)}`;
                    }
                }
            }
        }
    }
}
```

### PNG 导出

```html
<button onclick="exportChart()">下载为 PNG</button>

<script>
function exportChart() {
    const chart = Chart.getChart('vmafChart');
    const url = chart.toBase64Image();
    const link = document.createElement('a');
    link.download = 'quality_metrics.png';
    link.href = url;
    link.click();
}
</script>
```

---

## 5. 响应式布局

### 关键配置

```javascript
options: {
    responsive: true,
    maintainAspectRatio: false  // 必须！
}
```

### HTML 容器

```html
<!-- ✅ 正确：使用容器控制尺寸 -->
<div class="relative w-full h-96">
    <canvas id="chart"></canvas>
</div>

<!-- ❌ 错误：直接在 Canvas 设置尺寸 -->
<canvas id="chart" width="800" height="400"></canvas>
```

### 移动端适配

```javascript
function isMobile() {
    return window.innerWidth < 768;
}

options: {
    plugins: {
        legend: {
            position: isMobile() ? 'bottom' : 'top',
            labels: {
                font: { size: isMobile() ? 10 : 12 }
            }
        }
    }
}
```

---

## 6. Tailwind 配色方案

```javascript
const colors = {
    blue: 'rgb(59, 130, 246)',    // VMAF
    green: 'rgb(16, 185, 129)',   // PSNR
    amber: 'rgb(245, 158, 11)',   // SSIM
    red: 'rgb(239, 68, 68)',      // 低码率
    violet: 'rgb(139, 92, 246)'   // 高码率
};

datasets: [{
    borderColor: colors.blue,
    backgroundColor: colors.blue.replace('rgb', 'rgba').replace(')', ', 0.1)')
}]
```

---

## 7. 常见陷阱速查

| 问题 | 错误代码 | 正确代码 |
|------|---------|---------|
| Canvas 模糊 | `<canvas width="800">` | `<div class="h-96"><canvas>` |
| XSS 隐患 | `{{ data \| safe }}` | `{{ data \| tojson }}` |
| 性能差 | `pointRadius: 5` | `pointRadius: 0, animation: false` |
| 内存泄漏 | `new Chart(ctx, ...)` 重复调用 | `chart.update()` 或先 `destroy()` |
| 数据未显示 | `data: {{ python_list }}` | `data: {{ json_string \| tojson }}` |

---

## 8. 调试检查清单

```javascript
// 1. 验证数据加载
console.log('数据帧数:', metricsData.frames.length);
console.log('第一帧:', metricsData.frames[0]);

// 2. 检查 Canvas 是否存在
const canvas = document.getElementById('vmafChart');
console.log('Canvas 元素:', canvas);

// 3. 获取图表实例
const chart = Chart.getChart('vmafChart');
console.log('图表实例:', chart);

// 4. 检查容器尺寸
const container = canvas.parentElement;
console.log('容器尺寸:', container.offsetWidth, container.offsetHeight);
```

---

## 9. 完整配置模板

```javascript
// frontend/static/js/charts.js

function renderQualityChart(canvasId, data) {
    const ctx = document.getElementById(canvasId).getContext('2d');

    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'VMAF',
                    data: data.vmaf,
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    tension: 0,
                    yAxisID: 'y'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            parsing: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                title: {
                    display: true,
                    text: '视频质量指标',
                    font: { size: 16, weight: 'bold' }
                },
                tooltip: {
                    callbacks: {
                        title: (ctx) => `帧号: ${ctx[0].label}`,
                        label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(2)}`
                    }
                },
                legend: {
                    display: true,
                    position: 'top'
                },
                decimation: {
                    enabled: true,
                    algorithm: 'lttb',
                    samples: 500
                }
            },
            scales: {
                x: {
                    title: { display: true, text: '帧号' }
                },
                y: {
                    title: { display: true, text: 'VMAF' },
                    min: 0,
                    max: 100
                }
            }
        }
    });
}

// 使用
document.addEventListener('DOMContentLoaded', () => {
    renderQualityChart('vmafChart', chartData);
});
```

---

## 10. 资源链接

- **官方文档**: https://www.chartjs.org/docs/latest/
- **配置示例**: https://www.chartjs.org/docs/latest/samples/
- **性能优化**: https://www.chartjs.org/docs/latest/general/performance.html
- **GitHub 仓库**: https://github.com/chartjs/Chart.js

---

## 下一步

1. ✅ 复制"最小化实现"代码到项目
2. ✅ 验证后端数据传递（检查浏览器控制台 `metricsData`）
3. ✅ 启用性能优化（数据 > 1000 帧时）
4. ✅ 添加导出 PNG 功能
5. ✅ 集成 Tailwind 样式
