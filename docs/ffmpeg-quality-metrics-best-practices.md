# FFmpeg 视频质量指标计算最佳实践

**文档类型**: 技术研究文档
**创建日期**: 2025-10-25
**适用项目**: VQMR (Video Quality Metrics Report)
**FFmpeg 版本**: 5.0+ (推荐 6.0+)

---

## 目录

1. [PSNR 计算](#1-psnr-计算)
2. [VMAF 计算](#2-vmaf-计算)
3. [SSIM 计算](#3-ssim-计算)
4. [元数据提取](#4-元数据提取)
5. [错误处理](#5-错误处理)
6. [Python subprocess 调用](#6-python-subprocess-调用)
7. [最佳实践清单](#7-最佳实践清单)

---

## 1. PSNR 计算

### 1.1 FFmpeg lavfi psnr 滤镜用法

PSNR (Peak Signal-to-Noise Ratio，峰值信噪比) 是最常用的客观视频质量指标,用于测量编码损失。

#### 关键参数

- `stats_file`: 指定逐帧 PSNR 日志文件路径
- `stats_version`: 日志格式版本（1 或 2），默认为 1
- `stats_add_max`: 是否在日志中输出最大值（需要 stats_version >= 2）

### 1.2 单文件模式命令模板

**场景**: 对单个视频先转码（H.264 2Mbps 或 CRF=23），再与原始视频对比。

#### 步骤 1: 转码视频（ABR 模式 - 2Mbps）

```bash
ffmpeg -i input.mp4 \
  -c:v libx264 \
  -b:v 2000k \
  -maxrate 2000k \
  -bufsize 4000k \
  -preset medium \
  -pix_fmt yuv420p \
  -an \
  output_2mbps.mp4
```

#### 步骤 2: 转码视频（CRF 模式 - CRF=23）

```bash
ffmpeg -i input.mp4 \
  -c:v libx264 \
  -crf 23 \
  -preset medium \
  -pix_fmt yuv420p \
  -an \
  output_crf23.mp4
```

#### 步骤 3: 计算 PSNR（对比原始视频与转码后视频）

```bash
ffmpeg -i output_2mbps.mp4 \
  -i input.mp4 \
  -lavfi "[0:v][1:v]psnr=stats_file=psnr.log" \
  -f null -
```

**参数说明**:
- `[0:v][1:v]`: 第一个输入（待测视频）与第二个输入（参考视频）对比
- `-f null -`: 不生成输出文件，仅计算指标
- `stats_file=psnr.log`: 将逐帧数据写入 `psnr.log`

### 1.3 双文件模式命令模板

**场景**: 直接对比参考视频（reference.mp4）与待测视频（distorted.mp4）。

```bash
ffmpeg -i distorted.mp4 \
  -i reference.mp4 \
  -lavfi "[0:v][1:v]psnr=stats_file=psnr.log:stats_version=2" \
  -f null -
```

**注意事项**:
- 两个视频的分辨率、帧率、时长必须一致
- 如果分辨率不一致，需要先使用 `scale` 滤镜对齐
- 使用 `stats_version=2` 可以获得带表头的日志格式

### 1.4 psnr.log 格式示例与解析

#### stats_version=1 格式（默认）

```
n:0 mse_avg:254.23 mse_y:310.45 mse_u:152.34 mse_v:145.12 psnr_avg:24.08 psnr_y:23.21 psnr_u:26.30 psnr_v:26.51
n:1 mse_avg:261.87 mse_y:318.92 mse_u:159.21 mse_v:147.48 psnr_avg:23.95 psnr_y:23.09 psnr_u:26.11 psnr_v:26.44
n:2 mse_avg:248.56 mse_y:302.11 mse_u:149.89 mse_v:142.68 psnr_avg:24.17 psnr_y:23.33 psnr_u:26.37 psnr_v:26.59
```

#### stats_version=2 格式（带表头）

```
psnr_log_version:2:psnr_log_header: n,mse_avg,mse_y,mse_u,mse_v,psnr_avg,psnr_y,psnr_u,psnr_v
n:0 mse_avg:254.23 mse_y:310.45 mse_u:152.34 mse_v:145.12 psnr_avg:24.08 psnr_y:23.21 psnr_u:26.30 psnr_v:26.51
n:1 mse_avg:261.87 mse_y:318.92 mse_u:159.21 mse_v:147.48 psnr_avg:23.95 psnr_y:23.09 psnr_u:26.11 psnr_v:26.44
```

#### 字段说明

| 字段 | 说明 |
|------|------|
| `n` | 帧编号（从 0 开始） |
| `mse_avg` | 平均均方误差（MSE） |
| `mse_y` | Y 分量（亮度）MSE |
| `mse_u` | U 分量（色度）MSE |
| `mse_v` | V 分量（色度）MSE |
| `psnr_avg` | 平均 PSNR (dB) |
| `psnr_y` | Y 分量 PSNR (dB) |
| `psnr_u` | U 分量 PSNR (dB) |
| `psnr_v` | V 分量 PSNR (dB) |

#### 控制台输出示例

```
[Parsed_psnr_0 @ 0x7f8e4c000000] PSNR y:32.345 u:39.530 v:39.383 average:33.687 min:28.123 max:42.567
```

### 1.5 Python 解析代码示例

```python
import re
from typing import Dict, List

def parse_psnr_log(log_path: str) -> List[Dict[str, float]]:
    """
    解析 PSNR 日志文件

    Args:
        log_path: psnr.log 文件路径

    Returns:
        包含逐帧 PSNR 数据的列表
    """
    frames = []

    with open(log_path, 'r') as f:
        for line in f:
            # 跳过表头行
            if line.startswith('psnr_log_version'):
                continue

            # 解析每帧数据
            frame_data = {}
            for match in re.finditer(r'(\w+):([\d.]+)', line):
                key, value = match.groups()
                frame_data[key] = int(value) if key == 'n' else float(value)

            if frame_data:
                frames.append(frame_data)

    return frames

def calculate_average_psnr(frames: List[Dict[str, float]]) -> Dict[str, float]:
    """
    计算平均 PSNR 值

    Args:
        frames: parse_psnr_log 返回的逐帧数据

    Returns:
        包含平均值的字典
    """
    if not frames:
        return {}

    total_frames = len(frames)
    avg_psnr = {
        'psnr_avg': sum(f['psnr_avg'] for f in frames) / total_frames,
        'psnr_y': sum(f['psnr_y'] for f in frames) / total_frames,
        'psnr_u': sum(f['psnr_u'] for f in frames) / total_frames,
        'psnr_v': sum(f['psnr_v'] for f in frames) / total_frames,
    }

    return avg_psnr

# 使用示例
frames = parse_psnr_log('psnr.log')
avg_psnr = calculate_average_psnr(frames)
print(f"Average PSNR: {avg_psnr['psnr_avg']:.2f} dB")
print(f"Y component: {avg_psnr['psnr_y']:.2f} dB")
print(f"U component: {avg_psnr['psnr_u']:.2f} dB")
print(f"V component: {avg_psnr['psnr_v']:.2f} dB")
```

---

## 2. VMAF 计算

### 2.1 FFmpeg libvmaf 滤镜用法

VMAF (Video Multimethod Assessment Fusion) 是 Netflix 开发的视频质量评估算法，更贴近人眼主观感知。

#### 关键参数

- `model`: 指定 VMAF 模型文件路径（新版本推荐，取代 `model_path`）
- `log_fmt`: 日志格式（`json` 或 `xml`）
- `log_path`: 日志文件路径
- `n_threads`: 线程数（0 为自动，推荐 4-8）
- `n_subsample`: 子采样间隔（每隔 n 帧计算一次，默认 1）

### 2.2 VMAF 模型文件路径

#### 标准安装位置（Linux/macOS）

```bash
# Ubuntu/Debian (APT 安装)
/usr/local/share/model/vmaf_v0.6.1.json
/usr/local/share/model/vmaf_4k_v0.6.1.json

# macOS (Homebrew 安装)
/usr/local/opt/libvmaf/share/model/vmaf_v0.6.1.json
/opt/homebrew/opt/libvmaf/share/model/vmaf_v0.6.1.json  # Apple Silicon

# FreeBSD
/usr/local/share/vmaf/model/vmaf_v0.6.1.json
```

#### Windows 路径

Windows 无标准安装路径，需手动下载模型文件：

```bash
# 示例路径
C:\ffmpeg\model\vmaf_v0.6.1.json

# 下载地址
https://github.com/Netflix/vmaf/tree/master/model
```

#### 模型选择建议

| 模型 | 适用场景 | 说明 |
|------|----------|------|
| `vmaf_v0.6.1.json` | 1080p 及以下 | 标准 VMAF 模型（推荐） |
| `vmaf_4k_v0.6.1.json` | 4K (2160p) | 4K 专用模型 |
| `vmaf_v0.6.1neg.json` | 低质量视频 | 针对负分（< 0）优化 |

### 2.3 单文件模式命令模板

```bash
# 步骤 1: 转码视频（与 PSNR 相同）
ffmpeg -i input.mp4 \
  -c:v libx264 -b:v 2000k \
  -preset medium -pix_fmt yuv420p -an \
  output_2mbps.mp4

# 步骤 2: 计算 VMAF
ffmpeg -i output_2mbps.mp4 \
  -i input.mp4 \
  -lavfi "[0:v][1:v]libvmaf=model='path=/usr/local/share/model/vmaf_v0.6.1.json':log_fmt=json:log_path=vmaf.json:n_threads=4" \
  -f null -
```

### 2.4 双文件模式命令模板

```bash
ffmpeg -i distorted.mp4 \
  -i reference.mp4 \
  -lavfi "[0:v][1:v]libvmaf=model='path=/usr/local/share/model/vmaf_v0.6.1.json':log_fmt=json:log_path=vmaf.json:n_threads=4" \
  -f null -
```

### 2.5 性能优化参数

#### 线程数优化

```bash
# 自动检测（推荐）
n_threads=0

# 手动设置（通常 4 线程即可，超过 8 线程无明显提升）
n_threads=4
```

#### 子采样（加速计算）

```bash
# 每隔 2 帧计算一次（减少 50% 计算量）
n_subsample=2

# 适用于长视频或快速预览
```

**注意**: 子采样会降低精度，生产环境建议使用 `n_subsample=1`。

### 2.6 JSON 输出格式示例

```json
{
  "version": "2.3.1",
  "frames": [
    {
      "frameNum": 0,
      "metrics": {
        "vmaf": 95.234567,
        "psnr": 42.123456,
        "ssim": 0.987654,
        "ms_ssim": 0.989123
      }
    },
    {
      "frameNum": 1,
      "metrics": {
        "vmaf": 94.876543,
        "psnr": 41.987654,
        "ssim": 0.986543,
        "ms_ssim": 0.988765
      }
    }
  ],
  "pooled_metrics": {
    "vmaf": {
      "min": 89.123456,
      "max": 98.765432,
      "mean": 94.567890,
      "harmonic_mean": 94.321098
    },
    "psnr": {
      "min": 38.456789,
      "max": 45.678901,
      "mean": 42.123456,
      "harmonic_mean": 41.987654
    }
  }
}
```

### 2.7 XML 输出格式示例

```xml
<?xml version="1.0" encoding="UTF-8"?>
<VMAF version="2.3.1">
  <frames>
    <frame frameNum="0" vmaf="95.234567" psnr="42.123456" ssim="0.987654" ms_ssim="0.989123"/>
    <frame frameNum="1" vmaf="94.876543" psnr="41.987654" ssim="0.986543" ms_ssim="0.988765"/>
  </frames>
  <pooled_metrics>
    <metric name="vmaf" min="89.123456" max="98.765432" mean="94.567890" harmonic_mean="94.321098"/>
  </pooled_metrics>
</VMAF>
```

### 2.8 Python 解析代码示例

```python
import json
from typing import Dict, List

def parse_vmaf_json(json_path: str) -> Dict:
    """
    解析 VMAF JSON 日志文件

    Args:
        json_path: vmaf.json 文件路径

    Returns:
        包含逐帧数据和汇总指标的字典
    """
    with open(json_path, 'r') as f:
        data = json.load(f)

    return {
        'version': data.get('version'),
        'frames': data.get('frames', []),
        'pooled_metrics': data.get('pooled_metrics', {})
    }

def extract_vmaf_scores(vmaf_data: Dict) -> List[float]:
    """
    提取逐帧 VMAF 分数

    Args:
        vmaf_data: parse_vmaf_json 返回的数据

    Returns:
        VMAF 分数列表
    """
    return [frame['metrics']['vmaf'] for frame in vmaf_data['frames']]

def get_vmaf_summary(vmaf_data: Dict) -> Dict[str, float]:
    """
    获取 VMAF 汇总统计

    Args:
        vmaf_data: parse_vmaf_json 返回的数据

    Returns:
        包含最小/最大/平均值的字典
    """
    pooled = vmaf_data['pooled_metrics']['vmaf']
    return {
        'min': pooled['min'],
        'max': pooled['max'],
        'mean': pooled['mean'],
        'harmonic_mean': pooled['harmonic_mean']
    }

# 使用示例
vmaf_data = parse_vmaf_json('vmaf.json')
summary = get_vmaf_summary(vmaf_data)
print(f"VMAF Mean: {summary['mean']:.2f}")
print(f"VMAF Min: {summary['min']:.2f}")
print(f"VMAF Max: {summary['max']:.2f}")
```

---

## 3. SSIM 计算

### 3.1 FFmpeg ssim 滤镜用法

SSIM (Structural Similarity Index，结构相似性指数) 测量图像结构信息的失真程度。

#### 关键参数

- `stats_file`: 指定逐帧 SSIM 日志文件路径（使用 `-` 输出到 stdout）

### 3.2 单文件模式命令模板

```bash
# 步骤 1: 转码视频（与 PSNR 相同）
ffmpeg -i input.mp4 \
  -c:v libx264 -b:v 2000k \
  -preset medium -pix_fmt yuv420p -an \
  output_2mbps.mp4

# 步骤 2: 计算 SSIM
ffmpeg -i output_2mbps.mp4 \
  -i input.mp4 \
  -lavfi "[0:v][1:v]ssim=stats_file=ssim.log" \
  -f null -
```

### 3.3 双文件模式命令模板

```bash
ffmpeg -i distorted.mp4 \
  -i reference.mp4 \
  -lavfi "[0:v][1:v]ssim=stats_file=ssim.log" \
  -f null -
```

### 3.4 ssim.log 格式示例与解析

```
n:0 Y:0.926845 U:0.876798 V:0.860658 All:0.907472 (11.357537)
n:1 Y:0.924567 U:0.875432 V:0.859123 All:0.906234 (11.289456)
n:2 Y:0.928901 U:0.877654 V:0.861789 All:0.908765 (11.421098)
```

#### 字段说明

| 字段 | 说明 | 取值范围 |
|------|------|----------|
| `n` | 帧编号 | 0, 1, 2, ... |
| `Y` | Y 分量（亮度）SSIM | 0.0 - 1.0 |
| `U` | U 分量（色度）SSIM | 0.0 - 1.0 |
| `V` | V 分量（色度）SSIM | 0.0 - 1.0 |
| `All` | 平均 SSIM | 0.0 - 1.0 |
| `(dB)` | SSIM 对应的 dB 值 | -inf - inf |

**SSIM 值解读**:
- **0.95 - 1.00**: 几乎无损
- **0.90 - 0.95**: 高质量
- **0.80 - 0.90**: 中等质量
- **< 0.80**: 低质量

#### 控制台输出示例

```
[Parsed_ssim_0 @ 0x7f8e4c000000] SSIM Y:0.926845 (11.357537) U:0.876798 (9.093807) V:0.860658 (8.559193) All:0.907472 (10.337287)
```

### 3.5 Python 解析代码示例

```python
import re
from typing import Dict, List

def parse_ssim_log(log_path: str) -> List[Dict[str, float]]:
    """
    解析 SSIM 日志文件

    Args:
        log_path: ssim.log 文件路径

    Returns:
        包含逐帧 SSIM 数据的列表
    """
    frames = []

    with open(log_path, 'r') as f:
        for line in f:
            # 解析格式: n:0 Y:0.926845 U:0.876798 V:0.860658 All:0.907472 (11.357537)
            match = re.match(
                r'n:(\d+)\s+Y:([\d.]+)\s+U:([\d.]+)\s+V:([\d.]+)\s+All:([\d.]+)\s+\(([\d.]+)\)',
                line
            )

            if match:
                frame_data = {
                    'n': int(match.group(1)),
                    'ssim_y': float(match.group(2)),
                    'ssim_u': float(match.group(3)),
                    'ssim_v': float(match.group(4)),
                    'ssim_all': float(match.group(5)),
                    'ssim_db': float(match.group(6))
                }
                frames.append(frame_data)

    return frames

def calculate_average_ssim(frames: List[Dict[str, float]]) -> Dict[str, float]:
    """
    计算平均 SSIM 值

    Args:
        frames: parse_ssim_log 返回的逐帧数据

    Returns:
        包含平均值的字典
    """
    if not frames:
        return {}

    total_frames = len(frames)
    avg_ssim = {
        'ssim_all': sum(f['ssim_all'] for f in frames) / total_frames,
        'ssim_y': sum(f['ssim_y'] for f in frames) / total_frames,
        'ssim_u': sum(f['ssim_u'] for f in frames) / total_frames,
        'ssim_v': sum(f['ssim_v'] for f in frames) / total_frames,
        'ssim_db': sum(f['ssim_db'] for f in frames) / total_frames,
    }

    return avg_ssim

# 使用示例
frames = parse_ssim_log('ssim.log')
avg_ssim = calculate_average_ssim(frames)
print(f"Average SSIM: {avg_ssim['ssim_all']:.6f}")
print(f"Average SSIM (dB): {avg_ssim['ssim_db']:.2f} dB")
```

---

## 4. 元数据提取

### 4.1 ffprobe 基础命令

#### 提取完整元数据（JSON 格式）

```bash
ffprobe -v quiet \
  -print_format json \
  -show_format \
  -show_streams \
  input.mp4 > metadata.json
```

#### 美化输出（易读）

```bash
ffprobe -v quiet \
  -print_format json \
  -show_format \
  -show_streams \
  -pretty \
  input.mp4
```

### 4.2 提取特定字段

#### 分辨率、帧率、编解码器、时长

```bash
ffprobe -v error \
  -select_streams v:0 \
  -show_entries stream=width,height,r_frame_rate,codec_name,duration \
  -of json \
  input.mp4
```

**输出示例**:

```json
{
    "streams": [
        {
            "codec_name": "h264",
            "width": 1920,
            "height": 1080,
            "r_frame_rate": "30/1",
            "duration": "120.500000"
        }
    ]
}
```

#### 仅输出数值（CSV 格式）

```bash
ffprobe -v error \
  -select_streams v:0 \
  -show_entries stream=width,height,r_frame_rate,codec_name,duration \
  -of csv=p=0:s=x \
  input.mp4
```

**输出示例**:

```
h264x1920x1080x30/1x120.500000
```

### 4.3 提取音频信息

```bash
ffprobe -v error \
  -select_streams a:0 \
  -show_entries stream=codec_name,sample_rate,channels,bit_rate \
  -of json \
  input.mp4
```

### 4.4 提取格式信息（容器级别）

```bash
ffprobe -v error \
  -show_entries format=filename,nb_streams,duration,size,bit_rate,format_name \
  -of json \
  input.mp4
```

### 4.5 Python 解析代码示例

```python
import subprocess
import json
from typing import Dict, Optional

def extract_video_metadata(video_path: str) -> Optional[Dict]:
    """
    使用 ffprobe 提取视频元数据

    Args:
        video_path: 视频文件路径

    Returns:
        包含视频元数据的字典，失败返回 None
    """
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        video_path
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"ffprobe failed: {e.stderr}")
        return None
    except subprocess.TimeoutExpired:
        print("ffprobe timeout")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        return None

def get_video_info(metadata: Dict) -> Dict:
    """
    从元数据中提取关键信息

    Args:
        metadata: extract_video_metadata 返回的数据

    Returns:
        包含关键信息的字典
    """
    # 查找第一个视频流
    video_stream = next(
        (s for s in metadata['streams'] if s['codec_type'] == 'video'),
        None
    )

    if not video_stream:
        raise ValueError("No video stream found")

    # 解析帧率（格式：30/1 或 30000/1001）
    frame_rate_str = video_stream.get('r_frame_rate', '0/1')
    num, den = map(int, frame_rate_str.split('/'))
    frame_rate = num / den if den != 0 else 0

    # 提取时长（优先从流中获取，其次从格式中获取）
    duration = float(video_stream.get('duration', 0))
    if duration == 0:
        duration = float(metadata.get('format', {}).get('duration', 0))

    return {
        'codec': video_stream.get('codec_name'),
        'width': video_stream.get('width'),
        'height': video_stream.get('height'),
        'frame_rate': round(frame_rate, 2),
        'duration': round(duration, 2),
        'pix_fmt': video_stream.get('pix_fmt'),
        'bit_rate': int(video_stream.get('bit_rate', 0)),
        'nb_frames': int(video_stream.get('nb_frames', 0))
    }

# 使用示例
metadata = extract_video_metadata('input.mp4')
if metadata:
    info = get_video_info(metadata)
    print(f"Resolution: {info['width']}x{info['height']}")
    print(f"Frame Rate: {info['frame_rate']} fps")
    print(f"Duration: {info['duration']} seconds")
    print(f"Codec: {info['codec']}")
```

---

## 5. 错误处理

### 5.1 分辨率/帧率不一致检测

#### 命令行检测

```bash
# 提取两个视频的分辨率和帧率
ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height,r_frame_rate \
  -of csv=p=0:s=x \
  video1.mp4

ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height,r_frame_rate \
  -of csv=p=0:s=x \
  video2.mp4
```

#### Python 检测示例

```python
def validate_videos_compatible(video1_path: str, video2_path: str) -> tuple[bool, str]:
    """
    验证两个视频是否可以对比（分辨率、帧率、时长一致）

    Args:
        video1_path: 第一个视频路径
        video2_path: 第二个视频路径

    Returns:
        (是否兼容, 错误消息)
    """
    meta1 = extract_video_metadata(video1_path)
    meta2 = extract_video_metadata(video2_path)

    if not meta1 or not meta2:
        return False, "Failed to extract metadata"

    info1 = get_video_info(meta1)
    info2 = get_video_info(meta2)

    # 检查分辨率
    if info1['width'] != info2['width'] or info1['height'] != info2['height']:
        return False, f"Resolution mismatch: {info1['width']}x{info1['height']} vs {info2['width']}x{info2['height']}"

    # 检查帧率（允许 0.1 fps 误差）
    if abs(info1['frame_rate'] - info2['frame_rate']) > 0.1:
        return False, f"Frame rate mismatch: {info1['frame_rate']} vs {info2['frame_rate']} fps"

    # 检查时长（允许 1 秒误差）
    if abs(info1['duration'] - info2['duration']) > 1.0:
        return False, f"Duration mismatch: {info1['duration']} vs {info2['duration']} seconds"

    return True, ""

# 使用示例
compatible, error = validate_videos_compatible('video1.mp4', 'video2.mp4')
if not compatible:
    print(f"Error: {error}")
else:
    print("Videos are compatible for comparison")
```

### 5.2 自动分辨率对齐（可选）

如果需要自动对齐分辨率不一致的视频：

```bash
# 将 video1 缩放到与 video2 相同的分辨率
ffmpeg -i video1.mp4 \
  -vf "scale=1920:1080:flags=bicubic" \
  -c:v libx264 -preset fast -crf 18 \
  video1_scaled.mp4
```

**注意**: 自动缩放会引入额外的质量损失，默认不推荐启用。

### 5.3 编码器崩溃捕获

#### Bash 脚本示例

```bash
#!/bin/bash

set -euo pipefail

INPUT="input.mp4"
OUTPUT="output.mp4"
LOG_FILE="encode.log"

# 运行编码并捕获返回码
ffmpeg -i "$INPUT" \
  -c:v libx264 -b:v 2000k \
  -preset medium -pix_fmt yuv420p -an \
  "$OUTPUT" \
  2>&1 | tee "$LOG_FILE"

RETURN_CODE=$?

if [ $RETURN_CODE -ne 0 ]; then
    echo "Encoding failed with return code: $RETURN_CODE"
    echo "Check log file: $LOG_FILE"
    exit $RETURN_CODE
fi

echo "Encoding succeeded"
```

#### Python subprocess 示例

```python
import subprocess
import sys

def run_ffmpeg_with_error_handling(cmd: list, log_path: str) -> tuple[bool, int, str]:
    """
    运行 FFmpeg 命令并处理错误

    Args:
        cmd: FFmpeg 命令列表
        log_path: 日志文件路径

    Returns:
        (成功与否, 返回码, 错误消息)
    """
    try:
        with open(log_path, 'w') as log_file:
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 合并 stderr 到 stdout
                text=True,
                timeout=3600,  # 1 小时超时
                check=False  # 不自动抛出异常
            )

            # 写入日志
            log_file.write(process.stdout)

            if process.returncode != 0:
                return False, process.returncode, process.stdout

            return True, 0, ""

    except subprocess.TimeoutExpired:
        return False, -1, "Timeout: FFmpeg process exceeded 1 hour"
    except Exception as e:
        return False, -2, f"Unexpected error: {str(e)}"

# 使用示例
cmd = [
    'ffmpeg', '-i', 'input.mp4',
    '-c:v', 'libx264', '-b:v', '2000k',
    '-preset', 'medium', '-pix_fmt', 'yuv420p', '-an',
    'output.mp4'
]

success, code, error = run_ffmpeg_with_error_handling(cmd, 'encode.log')
if not success:
    print(f"Encoding failed (code {code}): {error}")
    sys.exit(1)
```

### 5.4 常见错误码与处理

| 返回码 | 说明 | 处理建议 |
|--------|------|----------|
| 0 | 成功 | 无需处理 |
| 1 | 通用错误 | 检查日志文件定位问题 |
| -1 | 超时 | 增加 timeout 或优化编码参数 |
| 137 | 内存不足（OOM killed） | 降低分辨率或使用更快的 preset |
| 139 | 段错误（Segmentation fault） | FFmpeg 或编码器 bug，尝试更新版本 |

### 5.5 零字节输出检测

```python
import os

def validate_output_file(output_path: str, min_size_kb: int = 10) -> tuple[bool, str]:
    """
    验证输出文件是否有效

    Args:
        output_path: 输出文件路径
        min_size_kb: 最小文件大小（KB）

    Returns:
        (是否有效, 错误消息)
    """
    if not os.path.exists(output_path):
        return False, f"Output file not found: {output_path}"

    file_size = os.path.getsize(output_path)

    if file_size == 0:
        return False, "Output file is empty (0 bytes)"

    if file_size < min_size_kb * 1024:
        return False, f"Output file too small: {file_size} bytes (expected > {min_size_kb} KB)"

    return True, ""

# 使用示例
valid, error = validate_output_file('output.mp4', min_size_kb=100)
if not valid:
    print(f"Output validation failed: {error}")
```

---

## 6. Python subprocess 调用

### 6.1 基础 subprocess 模板

```python
import subprocess
from typing import Tuple

def run_ffmpeg_command(
    cmd: list,
    timeout: int = 3600,
    capture_output: bool = True
) -> Tuple[bool, str, str]:
    """
    运行 FFmpeg 命令的通用封装

    Args:
        cmd: FFmpeg 命令列表（如 ['ffmpeg', '-i', 'input.mp4', ...]）
        timeout: 超时时间（秒）
        capture_output: 是否捕获输出

    Returns:
        (成功与否, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE if capture_output else None,
            stderr=subprocess.PIPE if capture_output else None,
            text=True,  # 返回字符串而非字节
            timeout=timeout,
            check=False  # 手动检查返回码
        )

        success = result.returncode == 0
        return success, result.stdout or "", result.stderr or ""

    except subprocess.TimeoutExpired as e:
        return False, "", f"Timeout after {timeout} seconds"
    except Exception as e:
        return False, "", f"Exception: {str(e)}"
```

### 6.2 合并 stdout 和 stderr

FFmpeg 将进度信息输出到 stderr，需要合并流以捕获完整日志：

```python
def run_ffmpeg_combined_output(cmd: list, timeout: int = 3600) -> Tuple[bool, str]:
    """
    运行 FFmpeg 并合并 stdout/stderr

    Args:
        cmd: FFmpeg 命令列表
        timeout: 超时时间（秒）

    Returns:
        (成功与否, 合并后的输出)
    """
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # 合并到 stdout
            text=True,
            timeout=timeout,
            check=False
        )

        return result.returncode == 0, result.stdout

    except subprocess.TimeoutExpired:
        return False, f"Timeout after {timeout} seconds"
    except Exception as e:
        return False, f"Exception: {str(e)}"
```

### 6.3 实时进度监控

```python
import subprocess
import re

def run_ffmpeg_with_progress(cmd: list, total_frames: int):
    """
    运行 FFmpeg 并实时输出进度

    Args:
        cmd: FFmpeg 命令列表
        total_frames: 总帧数
    """
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1  # 行缓冲
    )

    for line in process.stdout:
        # FFmpeg 进度格式: frame= 1234 fps= 30 q=28.0 size=  12345kB time=00:01:23.45 ...
        match = re.search(r'frame=\s*(\d+)', line)
        if match:
            current_frame = int(match.group(1))
            progress = (current_frame / total_frames) * 100
            print(f"\rProgress: {progress:.1f}% ({current_frame}/{total_frames} frames)", end='')

    process.wait()
    print()  # 换行

    return process.returncode == 0
```

### 6.4 完整的质量指标计算封装

```python
import subprocess
import json
import os
from typing import Optional, Dict

class VideoQualityMetrics:
    """视频质量指标计算封装类"""

    def __init__(self, ffmpeg_path: str = 'ffmpeg', ffprobe_path: str = 'ffprobe'):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

    def calculate_psnr(
        self,
        distorted: str,
        reference: str,
        log_path: str,
        timeout: int = 3600
    ) -> bool:
        """计算 PSNR"""
        cmd = [
            self.ffmpeg_path,
            '-i', distorted,
            '-i', reference,
            '-lavfi', f'[0:v][1:v]psnr=stats_file={log_path}:stats_version=2',
            '-f', 'null', '-'
        ]

        success, _, stderr = run_ffmpeg_command(cmd, timeout)
        if not success:
            print(f"PSNR calculation failed: {stderr}")
        return success

    def calculate_vmaf(
        self,
        distorted: str,
        reference: str,
        log_path: str,
        model_path: str = '/usr/local/share/model/vmaf_v0.6.1.json',
        n_threads: int = 4,
        timeout: int = 7200
    ) -> bool:
        """计算 VMAF"""
        cmd = [
            self.ffmpeg_path,
            '-i', distorted,
            '-i', reference,
            '-lavfi', f"[0:v][1:v]libvmaf=model='path={model_path}':log_fmt=json:log_path={log_path}:n_threads={n_threads}",
            '-f', 'null', '-'
        ]

        success, _, stderr = run_ffmpeg_command(cmd, timeout)
        if not success:
            print(f"VMAF calculation failed: {stderr}")
        return success

    def calculate_ssim(
        self,
        distorted: str,
        reference: str,
        log_path: str,
        timeout: int = 3600
    ) -> bool:
        """计算 SSIM"""
        cmd = [
            self.ffmpeg_path,
            '-i', distorted,
            '-i', reference,
            '-lavfi', f'[0:v][1:v]ssim=stats_file={log_path}',
            '-f', 'null', '-'
        ]

        success, _, stderr = run_ffmpeg_command(cmd, timeout)
        if not success:
            print(f"SSIM calculation failed: {stderr}")
        return success

    def extract_metadata(self, video_path: str) -> Optional[Dict]:
        """提取视频元数据"""
        cmd = [
            self.ffprobe_path,
            '-v', 'error',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_path
        ]

        success, stdout, stderr = run_ffmpeg_command(cmd, timeout=30)
        if not success:
            print(f"Metadata extraction failed: {stderr}")
            return None

        try:
            return json.loads(stdout)
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            return None

    def calculate_all_metrics(
        self,
        distorted: str,
        reference: str,
        output_dir: str,
        vmaf_model: str = '/usr/local/share/model/vmaf_v0.6.1.json'
    ) -> Dict[str, bool]:
        """计算所有质量指标"""
        os.makedirs(output_dir, exist_ok=True)

        results = {
            'psnr': self.calculate_psnr(
                distorted, reference,
                os.path.join(output_dir, 'psnr.log')
            ),
            'vmaf': self.calculate_vmaf(
                distorted, reference,
                os.path.join(output_dir, 'vmaf.json'),
                model_path=vmaf_model
            ),
            'ssim': self.calculate_ssim(
                distorted, reference,
                os.path.join(output_dir, 'ssim.log')
            )
        }

        return results

# 使用示例
metrics = VideoQualityMetrics()

# 先转码视频
encode_cmd = [
    'ffmpeg', '-i', 'input.mp4',
    '-c:v', 'libx264', '-b:v', '2000k',
    '-preset', 'medium', '-pix_fmt', 'yuv420p', '-an',
    'output_2mbps.mp4'
]
success, _, _ = run_ffmpeg_command(encode_cmd)

if success:
    # 计算所有指标
    results = metrics.calculate_all_metrics(
        distorted='output_2mbps.mp4',
        reference='input.mp4',
        output_dir='metrics_output'
    )

    print(f"PSNR: {'✓' if results['psnr'] else '✗'}")
    print(f"VMAF: {'✓' if results['vmaf'] else '✗'}")
    print(f"SSIM: {'✓' if results['ssim'] else '✗'}")
```

### 6.5 异步执行（适用于并发任务）

```python
import asyncio
from typing import List, Dict

async def run_ffmpeg_async(cmd: list, timeout: int = 3600) -> Tuple[bool, str]:
    """异步运行 FFmpeg 命令"""
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )

    try:
        stdout, _ = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout
        )
        success = process.returncode == 0
        return success, stdout.decode('utf-8')
    except asyncio.TimeoutError:
        process.kill()
        return False, f"Timeout after {timeout} seconds"

async def calculate_metrics_parallel(tasks: List[Dict]) -> List[bool]:
    """并行计算多个视频的质量指标"""
    coroutines = [
        run_ffmpeg_async(task['cmd'], task.get('timeout', 3600))
        for task in tasks
    ]

    results = await asyncio.gather(*coroutines)
    return [success for success, _ in results]

# 使用示例
async def main():
    tasks = [
        {
            'cmd': ['ffmpeg', '-i', 'video1.mp4', '-i', 'ref1.mp4',
                    '-lavfi', '[0:v][1:v]psnr=stats_file=psnr1.log',
                    '-f', 'null', '-'],
            'timeout': 3600
        },
        {
            'cmd': ['ffmpeg', '-i', 'video2.mp4', '-i', 'ref2.mp4',
                    '-lavfi', '[0:v][1:v]psnr=stats_file=psnr2.log',
                    '-f', 'null', '-'],
            'timeout': 3600
        }
    ]

    results = await calculate_metrics_parallel(tasks)
    print(f"Success rate: {sum(results)}/{len(results)}")

# 运行异步任务
asyncio.run(main())
```

---

## 7. 最佳实践清单

### 7.1 命令构建

- ✅ **统一使用 `-lavfi` 而非 `-vf`**: `lavfi` 适用于所有滤镜链
- ✅ **PSNR/SSIM 使用 `stats_version=2`**: 获得带表头的日志，便于解析
- ✅ **VMAF 使用 JSON 输出**: 比 XML 更易解析
- ✅ **始终使用 `-f null -`**: 不生成输出文件，仅计算指标
- ✅ **使用绝对路径**: 避免相对路径导致的文件找不到错误
- ✅ **禁用音频编码**: 质量指标计算时使用 `-an` 跳过音频

### 7.2 性能优化

- ✅ **VMAF 线程数设置为 4-8**: 超过 8 个线程收益递减
- ✅ **使用 `preset medium` 或 `fast`**: 平衡质量与速度
- ✅ **长视频考虑子采样**: VMAF 使用 `n_subsample=2` 加速（仅预览时）
- ✅ **避免不必要的像素格式转换**: 统一使用 `yuv420p`
- ✅ **预先验证视频兼容性**: 避免浪费计算资源

### 7.3 错误处理

- ✅ **总是捕获 stderr**: FFmpeg 将错误和进度信息输出到 stderr
- ✅ **设置合理的 timeout**: 根据视频长度调整（建议 1-2 小时）
- ✅ **检查返回码**: 非 0 返回码表示失败
- ✅ **验证输出文件大小**: 捕获零字节输出
- ✅ **记录完整日志**: 保存 FFmpeg 输出用于故障排查

### 7.4 日志解析

- ✅ **使用正则表达式**: 适配 FFmpeg 版本差异
- ✅ **处理缺失字段**: 某些格式可能不包含所有分量
- ✅ **验证数据完整性**: 检查帧数是否匹配预期
- ✅ **保留原始日志**: 便于调试和复现问题

### 7.5 文件管理

- ✅ **按任务 ID 分桶**: 每个任务独立目录（如 `jobs/{job_id}/`）
- ✅ **使用描述性文件名**: `psnr.log`, `vmaf.json`, `ssim.log`
- ✅ **定期清理临时文件**: 7 天后自动删除
- ✅ **保存元数据 JSON**: 记录任务参数和状态

### 7.6 常见陷阱

- ❌ **不要混用 `model_path` 和 `model`**: 新版本仅支持 `model='path=...'`
- ❌ **不要在生产环境使用子采样**: `n_subsample > 1` 会降低精度
- ❌ **不要忽略分辨率不一致**: 自动缩放会引入额外损失
- ❌ **不要使用 `-loglevel quiet`**: 会丢失重要错误信息
- ❌ **不要在编码和计算指标时同时进行**: 分两步执行，避免资源竞争

### 7.7 VMAF 模型选择

| 视频分辨率 | 推荐模型 | 路径示例 |
|-----------|----------|----------|
| 720p/1080p | `vmaf_v0.6.1.json` | `/usr/local/share/model/vmaf_v0.6.1.json` |
| 4K (2160p) | `vmaf_4k_v0.6.1.json` | `/usr/local/share/model/vmaf_4k_v0.6.1.json` |
| 低质量视频 | `vmaf_v0.6.1neg.json` | `/usr/local/share/model/vmaf_v0.6.1neg.json` |

### 7.8 质量指标阈值参考

| 指标 | 优秀 | 良好 | 可接受 | 差 |
|------|------|------|--------|----|
| **PSNR** | > 40 dB | 35-40 dB | 30-35 dB | < 30 dB |
| **VMAF** | > 95 | 85-95 | 70-85 | < 70 |
| **SSIM** | > 0.95 | 0.90-0.95 | 0.80-0.90 | < 0.80 |

---

## 附录 A: 完整工作流示例

### 单文件模式完整流程（Bash）

```bash
#!/bin/bash

set -euo pipefail

# 配置
INPUT_VIDEO="input.mp4"
OUTPUT_DIR="metrics_output"
BITRATE="2000k"
VMAF_MODEL="/usr/local/share/model/vmaf_v0.6.1.json"

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

# 步骤 1: 转码视频
echo "Step 1: Encoding video..."
ffmpeg -i "$INPUT_VIDEO" \
  -c:v libx264 -b:v "$BITRATE" \
  -preset medium -pix_fmt yuv420p -an \
  "$OUTPUT_DIR/encoded.mp4" \
  -y

# 步骤 2: 计算 PSNR
echo "Step 2: Calculating PSNR..."
ffmpeg -i "$OUTPUT_DIR/encoded.mp4" \
  -i "$INPUT_VIDEO" \
  -lavfi "[0:v][1:v]psnr=stats_file=$OUTPUT_DIR/psnr.log:stats_version=2" \
  -f null -

# 步骤 3: 计算 VMAF
echo "Step 3: Calculating VMAF..."
ffmpeg -i "$OUTPUT_DIR/encoded.mp4" \
  -i "$INPUT_VIDEO" \
  -lavfi "[0:v][1:v]libvmaf=model='path=$VMAF_MODEL':log_fmt=json:log_path=$OUTPUT_DIR/vmaf.json:n_threads=4" \
  -f null -

# 步骤 4: 计算 SSIM
echo "Step 4: Calculating SSIM..."
ffmpeg -i "$OUTPUT_DIR/encoded.mp4" \
  -i "$INPUT_VIDEO" \
  -lavfi "[0:v][1:v]ssim=stats_file=$OUTPUT_DIR/ssim.log" \
  -f null -

# 步骤 5: 提取元数据
echo "Step 5: Extracting metadata..."
ffprobe -v quiet -print_format json -show_format -show_streams \
  "$INPUT_VIDEO" > "$OUTPUT_DIR/input_metadata.json"

ffprobe -v quiet -print_format json -show_format -show_streams \
  "$OUTPUT_DIR/encoded.mp4" > "$OUTPUT_DIR/encoded_metadata.json"

echo "All metrics calculated successfully!"
echo "Results saved to: $OUTPUT_DIR"
```

### Python 完整工作流

```python
#!/usr/bin/env python3

import os
import json
from pathlib import Path

def main():
    # 配置
    input_video = "input.mp4"
    output_dir = Path("metrics_output")
    bitrate = "2000k"
    vmaf_model = "/usr/local/share/model/vmaf_v0.6.1.json"

    # 创建输出目录
    output_dir.mkdir(exist_ok=True)
    encoded_video = output_dir / "encoded.mp4"

    # 步骤 1: 转码视频
    print("Step 1: Encoding video...")
    encode_cmd = [
        'ffmpeg', '-i', input_video,
        '-c:v', 'libx264', '-b:v', bitrate,
        '-preset', 'medium', '-pix_fmt', 'yuv420p', '-an',
        str(encoded_video), '-y'
    ]
    success, _, stderr = run_ffmpeg_command(encode_cmd)
    if not success:
        print(f"Encoding failed: {stderr}")
        return

    # 步骤 2-4: 计算质量指标
    print("Step 2-4: Calculating quality metrics...")
    metrics = VideoQualityMetrics()
    results = metrics.calculate_all_metrics(
        distorted=str(encoded_video),
        reference=input_video,
        output_dir=str(output_dir),
        vmaf_model=vmaf_model
    )

    # 步骤 5: 提取元数据
    print("Step 5: Extracting metadata...")
    input_meta = metrics.extract_metadata(input_video)
    encoded_meta = metrics.extract_metadata(str(encoded_video))

    if input_meta:
        with open(output_dir / "input_metadata.json", 'w') as f:
            json.dump(input_meta, f, indent=2)

    if encoded_meta:
        with open(output_dir / "encoded_metadata.json", 'w') as f:
            json.dump(encoded_meta, f, indent=2)

    # 输出结果
    print("\nResults:")
    print(f"PSNR: {'✓' if results['psnr'] else '✗'}")
    print(f"VMAF: {'✓' if results['vmaf'] else '✗'}")
    print(f"SSIM: {'✓' if results['ssim'] else '✗'}")
    print(f"\nAll results saved to: {output_dir}")

if __name__ == '__main__':
    main()
```

---

## 参考资料

1. **FFmpeg 官方文档**:
   - PSNR Filter: https://ffmpeg.org/ffmpeg-filters.html#psnr
   - SSIM Filter: https://ffmpeg.org/ffmpeg-filters.html#ssim
   - libvmaf Filter: https://ffmpeg.org/ffmpeg-filters.html#libvmaf

2. **VMAF 项目**:
   - Netflix VMAF GitHub: https://github.com/Netflix/vmaf
   - VMAF 模型文件: https://github.com/Netflix/vmaf/tree/master/model

3. **第三方工具**:
   - ffmpeg-quality-metrics (Python): https://github.com/slhck/ffmpeg-quality-metrics
   - PyPI 包: https://pypi.org/project/ffmpeg-quality-metrics/

4. **相关文章**:
   - Calculating VMAF and PSNR with FFmpeg: https://websites.fraunhofer.de/video-dev/calculating-vmaf-and-psnr-with-ffmpeg/
   - OTTVerse PSNR/VMAF/SSIM Guide: https://ottverse.com/calculate-psnr-vmaf-ssim-using-ffmpeg/

---

**文档维护**: 定期更新以反映 FFmpeg 版本变化和新功能。
**最后更新**: 2025-10-25
