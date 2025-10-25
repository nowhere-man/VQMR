# Chart.js 集成示例代码

本目录包含 VQMR 项目 Chart.js 集成的完整示例代码。

## 目录结构

```
examples/
├── backend_example.py          # FastAPI 后端示例
├── report_template.html        # Jinja2 模板示例
├── charts.js                   # 前端图表渲染脚本
├── sample_metrics.json         # 示例数据
└── README.md                   # 本文件
```

## 使用方法

### 1. 查看示例数据格式

```bash
cat sample_metrics.json
```

### 2. 运行后端示例

```bash
# 安装依赖
pip install fastapi uvicorn jinja2 python-multipart

# 运行服务
uvicorn backend_example:app --reload --port 8000
```

### 3. 访问报告页面

打开浏览器访问：
```
http://localhost:8000/jobs/example/report
```

## 核心代码片段

### 后端数据传递（FastAPI）

```python
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
import json

templates = Jinja2Templates(directory="templates")

@router.get("/jobs/{job_id}/report")
async def get_report(request: Request, job_id: str):
    with open(f"jobs/{job_id}/metrics.json") as f:
        metrics = json.load(f)

    return templates.TemplateResponse(
        "report.html",
        {
            "request": request,
            "metrics_json": json.dumps(metrics)  # 序列化为 JSON
        }
    )
```

### 模板数据注入（Jinja2）

```html
<script>
    // 使用 tojson 过滤器安全传递数据
    const metricsData = {{ metrics_json | tojson }};
</script>
<script src="/static/js/charts.js"></script>
```

### 前端图表渲染（JavaScript）

```javascript
const ctx = document.getElementById('qualityChart').getContext('2d');

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
        maintainAspectRatio: false,
        animation: false
    }
});
```

## 关键要点

### ✅ 必须做

1. **使用 `tojson` 过滤器**：防止 XSS 攻击
   ```html
   {{ data | tojson }}  <!-- ✅ 正确 -->
   {{ data }}           <!-- ❌ 错误 -->
   ```

2. **设置响应式容器**：避免 Canvas 模糊
   ```html
   <div class="relative h-96">
       <canvas id="chart"></canvas>
   </div>
   ```

3. **性能优化**：大数据量禁用动画和点
   ```javascript
   options: {
       animation: false,
       plugins: { decimation: { enabled: true } }
   }
   datasets: [{ pointRadius: 0 }]
   ```

### ❌ 不要做

1. **不要在 Canvas 上设置尺寸属性**
   ```html
   <canvas width="800" height="400">  <!-- ❌ -->
   ```

2. **不要使用 `| safe` 过滤器**（除非确定数据安全）
   ```html
   {{ user_input | safe }}  <!-- ❌ 危险 -->
   ```

3. **不要重复创建图表实例**（导致内存泄漏）
   ```javascript
   // ❌ 错误
   setInterval(() => {
       new Chart(ctx, config);
   }, 1000);

   // ✅ 正确
   chart.update();
   ```

## 故障排查

### 图表未显示

```javascript
// 1. 检查数据是否加载
console.log('数据:', metricsData);

// 2. 检查 Canvas 元素
const canvas = document.getElementById('qualityChart');
console.log('Canvas:', canvas);

// 3. 检查容器尺寸
console.log('容器高度:', canvas.parentElement.offsetHeight);
```

### 数据显示错误

```javascript
// 验证数据结构
console.log('帧数:', metricsData.frames.length);
console.log('第一帧:', metricsData.frames[0]);

// 检查数据类型
console.log('VMAF 类型:', typeof metricsData.frames[0].vmaf);
```

## 完整示例

查看本目录中的完整示例文件：
- `/Users/liushaojie/Documents/Repos/VQMR/specs/001-video-quality-metrics-report/examples/backend_example.py`
- `/Users/liushaojie/Documents/Repos/VQMR/specs/001-video-quality-metrics-report/examples/report_template.html`
- `/Users/liushaojie/Documents/Repos/VQMR/specs/001-video-quality-metrics-report/examples/charts.js`

## 参考文档

- [Chart.js 深度研究](../chartjs-research.md) - 完整技术分析
- [Chart.js 快速上手](../chartjs-quickstart.md) - 5 分钟入门
- [Chart.js 官方文档](https://www.chartjs.org/docs/latest/)
