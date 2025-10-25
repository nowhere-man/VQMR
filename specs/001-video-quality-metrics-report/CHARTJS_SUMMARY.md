# Chart.js 可视化方案总结

**研究完成日期**: 2025-10-25
**适用项目**: VQMR (Video Quality Metrics Report)

---

## 📚 文档清单

### 1. 主要研究文档

| 文档 | 路径 | 用途 | 大小 |
|------|------|------|------|
| **深度研究** | `chartjs-research.md` | 完整技术分析、最佳实践、陷阱 | 62 KB |
| **快速上手** | `chartjs-quickstart.md` | 5分钟入门、速查表 | 10 KB |
| **示例代码** | `examples/` | 可运行的完整示例 | - |

### 2. 示例代码

| 文件 | 路径 | 说明 |
|------|------|------|
| 后端示例 | `examples/backend_example.py` | FastAPI + Jinja2 数据传递 |
| 前端模板 | `examples/report_template.html` | 完整 HTML 模板（含 Tailwind） |
| 图表脚本 | `examples/charts.js` | Chart.js 渲染逻辑 |
| 示例数据 | `examples/sample_metrics.json` | 10 帧指标数据 |
| 使用说明 | `examples/README.md` | 运行与调试指南 |

---

## 🎯 核心方案

### 技术选型

✅ **Chart.js 4.x** (推荐)
- 轻量级 (~60KB gzip)
- 原生响应式支持
- 与 Tailwind CSS 无缝集成
- 性能优化友好（decimation 插件）

### 数据传递架构

```
FastAPI (Python) 
    ↓
    JSON 序列化 (json.dumps)
    ↓
Jinja2 模板 ({{ data | tojson }})
    ↓
JavaScript 对象 (原生)
    ↓
Chart.js 渲染
```

**关键代码**：

```python
# 后端
return templates.TemplateResponse(
    "report.html",
    {"metrics_json": json.dumps(metrics)}
)
```

```html
<!-- 模板 -->
<script>
    const chartData = {{ metrics_json | tojson }};
</script>
```

### 图表类型

1. **逐帧质量曲线** (折线图)
   - VMAF/PSNR/SSIM 三条曲线
   - 3 个独立 Y 轴（不同量纲）

2. **多参数对比** (叠加折线图)
   - 不同码率/CRF 值对比
   - 5 种配色区分

3. **性能柱状图** (柱状图)
   - 编码时间/速度/码率
   - 多 Y 轴对比

---

## ⚡ 性能优化（关键）

### 必须配置（处理数千帧）

```javascript
options: {
    animation: false,        // 禁用动画
    parsing: false,          // 禁用自动解析
    plugins: {
        decimation: {
            enabled: true,
            algorithm: 'lttb', // 推荐算法
            samples: 500       // 最多显示 500 点
        }
    }
},
datasets: [{
    pointRadius: 0,          // 隐藏点
    tension: 0               // 直线连接
}]
```

### 后端预处理（推荐）

```python
def prepare_chart_data(metrics: dict) -> dict:
    frames = metrics["frames"]
    
    # 抽取数据（超过 1000 帧）
    if len(frames) > 1000:
        step = len(frames) // 500
        frames = frames[::step]
    
    return {
        "labels": [f["frame_number"] for f in frames],
        "vmaf": [f["vmaf"] for f in frames],
        # ...
    }
```

---

## 🎨 样式与响应式

### Tailwind 集成

```html
<!-- CDN 引入 -->
<script src="https://cdn.tailwindcss.com"></script>

<!-- 容器结构 -->
<div class="bg-white rounded-lg shadow-md p-6">
    <h2 class="text-xl font-semibold mb-4">质量指标</h2>
    <div class="relative h-96">
        <canvas id="chart"></canvas>
    </div>
</div>
```

### 响应式配置

```javascript
options: {
    responsive: true,
    maintainAspectRatio: false  // 必须！
}
```

**关键**：容器必须有 `position: relative` 和明确高度

---

## 🛠️ 交互功能

### 1. 工具提示

```javascript
tooltip: {
    callbacks: {
        title: (ctx) => `帧号: ${ctx[0].label} (${(ctx[0].label/30).toFixed(2)}s)`,
        label: (ctx) => {
            const label = ctx.dataset.label;
            const value = ctx.parsed.y;
            return label.includes('SSIM') 
                ? `${label}: ${value.toFixed(4)}`
                : `${label}: ${value.toFixed(2)}`;
        }
    }
}
```

### 2. PNG 导出

```javascript
function exportChart() {
    const chart = Chart.getChart('chartId');
    const url = chart.toBase64Image();
    const link = document.createElement('a');
    link.download = 'chart.png';
    link.href = url;
    link.click();
}
```

### 3. 图例切换

```javascript
legend: {
    onClick: (e, legendItem, legend) => {
        const index = legendItem.datasetIndex;
        const meta = legend.chart.getDatasetMeta(index);
        meta.hidden = !meta.hidden;
        legend.chart.update();
    }
}
```

---

## ⚠️ 常见陷阱

| 问题 | 错误示例 | 正确做法 |
|------|---------|---------|
| Canvas 模糊 | `<canvas width="800">` | 使用容器 + `maintainAspectRatio: false` |
| XSS 隐患 | `{{ data \| safe }}` | `{{ data \| tojson }}` |
| 性能差 | `pointRadius: 5, animation: true` | `pointRadius: 0, animation: false` |
| 内存泄漏 | 重复 `new Chart()` | `chart.update()` 或先 `destroy()` |
| 数据未传递 | `{{ python_obj }}` | `json.dumps()` + `\| tojson` |

---

## 🚀 快速开始（5 分钟）

### 1. 复制示例代码

```bash
cd /Users/liushaojie/Documents/Repos/VQMR/specs/001-video-quality-metrics-report/examples
```

### 2. 安装依赖

```bash
pip install fastapi uvicorn jinja2
```

### 3. 运行示例

```bash
python backend_example.py
```

### 4. 访问报告

```
http://localhost:8000/jobs/example_job_001/report
```

---

## 📊 配色方案（Tailwind）

```javascript
const COLORS = {
    blue: 'rgb(59, 130, 246)',    // VMAF
    green: 'rgb(16, 185, 129)',   // PSNR
    amber: 'rgb(245, 158, 11)',   // SSIM
    red: 'rgb(239, 68, 68)',      // 低码率
    violet: 'rgb(139, 92, 246)'   // 高码率
};
```

---

## ✅ 最佳实践检查清单

### 开发阶段
- [ ] 使用 CDN 快速原型
- [ ] 在控制台验证 `chartData` 对象
- [ ] 先实现基础功能，后优化

### 数据安全
- [ ] 使用 `tojson` 过滤器
- [ ] 验证数据完整性
- [ ] 后端预处理大数据

### 性能优化
- [ ] 数据 > 1000 点时启用 decimation
- [ ] 设置 `pointRadius: 0`
- [ ] 设置 `animation: false`
- [ ] 使用 `parsing: false`

### 响应式设计
- [ ] 设置 `maintainAspectRatio: false`
- [ ] 容器使用 `relative` + 固定高度
- [ ] 移动端调整图例位置

### 生产部署
- [ ] 本地托管 Chart.js
- [ ] 启用 gzip/Brotli 压缩
- [ ] 设置 CDN 缓存头

---

## 📖 参考资源

### 官方文档
- [Chart.js 官方文档](https://www.chartjs.org/docs/latest/)
- [性能优化指南](https://www.chartjs.org/docs/latest/general/performance.html)
- [响应式配置](https://www.chartjs.org/docs/latest/configuration/responsive.html)

### 项目文档
- [深度研究](./chartjs-research.md) - 62 KB 完整分析
- [快速上手](./chartjs-quickstart.md) - 10 KB 速查
- [示例代码](./examples/README.md) - 可运行示例

---

## 🎓 学习路径

1. **入门**：阅读 `chartjs-quickstart.md`（10 分钟）
2. **实践**：运行 `examples/backend_example.py`（5 分钟）
3. **深入**：阅读 `chartjs-research.md`（30 分钟）
4. **集成**：复制示例代码到项目中
5. **优化**：根据实际数据量调整配置

---

## 💡 下一步行动

1. ✅ 将 Chart.js 配置纳入 Phase 1 设计
2. ✅ 创建 `frontend/static/js/charts.js` 模板
3. ✅ 在报告模板中集成图表容器
4. ✅ 编写集成测试验证渲染功能
5. ✅ 性能测试（1000+ 帧数据）

---

**研究完成** | 总耗时: 2 小时 | 文档总量: ~85 KB
