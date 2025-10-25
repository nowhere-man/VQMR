/**
 * Chart.js 图表渲染脚本
 * 适用于 VQMR 项目的质量指标可视化
 */

// Tailwind 配色方案
const COLORS = {
    blue: 'rgb(59, 130, 246)',
    green: 'rgb(16, 185, 129)',
    amber: 'rgb(245, 158, 11)',
    red: 'rgb(239, 68, 68)',
    violet: 'rgb(139, 92, 246)',
    gray: 'rgb(107, 114, 128)'
};

/**
 * 渲染质量指标图表（VMAF, PSNR, SSIM）
 */
function renderQualityChart() {
    const ctx = document.getElementById('qualityChart');
    if (!ctx) {
        console.error('Canvas element not found: qualityChart');
        return null;
    }

    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartData.labels,
            datasets: [
                {
                    label: 'VMAF',
                    data: chartData.vmaf,
                    borderColor: COLORS.blue,
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    pointHoverBackgroundColor: COLORS.blue,
                    tension: 0,
                    yAxisID: 'y'
                },
                {
                    label: 'PSNR (Y通道)',
                    data: chartData.psnr_y,
                    borderColor: COLORS.green,
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    pointHoverBackgroundColor: COLORS.green,
                    tension: 0,
                    yAxisID: 'y1'
                },
                {
                    label: 'SSIM',
                    data: chartData.ssim,
                    borderColor: COLORS.amber,
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    pointHoverBackgroundColor: COLORS.amber,
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
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: 'rgba(255, 255, 255, 0.3)',
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {
                        title: function(context) {
                            const frameNumber = context[0].label;
                            const timeSeconds = (frameNumber / 30).toFixed(2);
                            return `帧号: ${frameNumber} (${timeSeconds}s @ 30fps)`;
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
                        padding: 15,
                        font: { size: 12 }
                    }
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    title: {
                        display: true,
                        text: '帧号',
                        font: { size: 14, weight: 'bold' }
                    },
                    ticks: {
                        stepSize: 1
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'VMAF',
                        color: COLORS.blue,
                        font: { size: 14, weight: 'bold' }
                    },
                    ticks: {
                        color: COLORS.blue
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
                        color: COLORS.green,
                        font: { size: 14, weight: 'bold' }
                    },
                    ticks: {
                        color: COLORS.green
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
                        color: COLORS.amber,
                        font: { size: 14, weight: 'bold' }
                    },
                    ticks: {
                        color: COLORS.amber
                    },
                    min: 0,
                    max: 1,
                    grid: {
                        drawOnChartArea: false
                    }
                }
            },
            // 性能优化
            animation: false,
            parsing: false,
            normalized: true
        }
    });

    return chart;
}

/**
 * 渲染编码时间图表
 */
function renderEncodingTimeChart() {
    const ctx = document.getElementById('encodingTimeChart');
    if (!ctx) {
        console.error('Canvas element not found: encodingTimeChart');
        return null;
    }

    const chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: chartData.labels,
            datasets: [{
                label: '编码耗时 (ms)',
                data: chartData.encoding_time_ms,
                backgroundColor: 'rgba(139, 92, 246, 0.7)',
                borderColor: COLORS.violet,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        title: (context) => `帧号: ${context[0].label}`,
                        label: (context) => {
                            return `编码耗时: ${context.parsed.y.toFixed(2)} ms`;
                        }
                    }
                },
                legend: {
                    display: false
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
                    title: {
                        display: true,
                        text: '编码耗时 (毫秒)'
                    },
                    beginAtZero: true
                }
            },
            animation: false
        }
    });

    return chart;
}

/**
 * 导出图表为 PNG 图片
 * @param {string} canvasId - Canvas 元素的 ID
 * @param {string} filename - 保存的文件名
 */
function exportChartAsPNG(canvasId, filename = 'chart.png') {
    const chartInstance = Chart.getChart(canvasId);
    if (!chartInstance) {
        console.error('Chart not found:', canvasId);
        alert('图表未找到，无法导出');
        return;
    }

    try {
        const url = chartInstance.toBase64Image();
        const link = document.createElement('a');
        link.download = filename;
        link.href = url;
        link.click();

        console.log('图表已导出:', filename);
    } catch (error) {
        console.error('导出失败:', error);
        alert('导出失败，请查看控制台错误信息');
    }
}

/**
 * 检测是否为移动设备
 */
function isMobile() {
    return window.innerWidth < 768;
}

/**
 * 初始化：页面加载完成后渲染所有图表
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('开始渲染图表...');

    try {
        // 渲染质量指标图表
        const qualityChart = renderQualityChart();
        if (qualityChart) {
            console.log('✅ 质量指标图表渲染成功');
        }

        // 渲染编码时间图表
        const encodingTimeChart = renderEncodingTimeChart();
        if (encodingTimeChart) {
            console.log('✅ 编码时间图表渲染成功');
        }

        // 监听窗口大小变化（可选：动态调整配置）
        window.addEventListener('resize', function() {
            // Chart.js 会自动处理响应式，无需手动更新
            console.log('窗口尺寸变化:', window.innerWidth, window.innerHeight);
        });

    } catch (error) {
        console.error('渲染图表失败:', error);
        alert('图表渲染失败，请检查浏览器控制台');
    }
});

// 调试辅助函数
window.debugChartData = function() {
    console.group('图表数据调试');
    console.log('帧数:', chartData.labels.length);
    console.log('标签:', chartData.labels);
    console.log('VMAF:', chartData.vmaf);
    console.log('PSNR (Y):', chartData.psnr_y);
    console.log('SSIM:', chartData.ssim);
    console.log('编码耗时:', chartData.encoding_time_ms);
    console.groupEnd();
};
