# Poetry Camera - 測試環境報告 / Test Environment Report

**生成時間 / Generated Time**: 2025-06-28T19:03:22.750372

## 🖥️ 系統資訊 / System Information

**Raspberry Pi 型號 / Raspberry Pi Model**: Raspberry Pi 5 Model B Rev 1.0
**作業系統 / Operating System**: Linux 6.12.25+rpt-rpi-2712
**核心版本 / Kernel Version**: 6.12.25+rpt-rpi-2712
**架構 / Architecture**: aarch64

## 🐍 Python 環境 / Python Environment

**Python 版本 / Python Version**: 3.11.2
**虛擬環境 / Virtual Environment**: /home/sweet/gesture_camera/venv
**pip 版本 / pip Version**: 25.1.1

## 📦 Python 套件版本 / Python Package Versions

| 套件名稱 / Package Name | 版本 / Version | 狀態 / Status |
|----------|------|------|
| opencv-python | 4.11.0.86 | ✅ 已安裝 / Installed |
| opencv-contrib-python | 4.11.0.86 | ✅ 已安裝 / Installed |
| numpy | 1.26.4 | ✅ 已安裝 / Installed |
| pygame | 2.1.2 | ✅ 已安裝 / Installed |
| Pillow | 9.4.0 | ✅ 已安裝 / Installed |
| python-dotenv | 0.21.0 | ✅ 已安裝 / Installed |
| openai | 1.82.1 | ✅ 已安裝 / Installed |
| requests | 2.28.1 | ✅ 已安裝 / Installed |
| mediapipe | 0.10.18 | ✅ 已安裝 / Installed |
| RPi.GPIO | 0.7.1 | ✅ 已安裝 / Installed |
| python-escpos | 3.1 | ✅ 已安裝 / Installed |
| pyusb | 1.3.1 | ✅ 已安裝 / Installed |
| tflite-runtime | 2.14.0 | ✅ 已安裝 / Installed |
| tensorflow | 2.19.0 | ✅ 已安裝 / Installed |
| picamera2 | 0.3.28 | ✅ 已安裝 / Installed |
| libcamera | 未安裝 / Not Installed | ❌ 未安裝 / Not Installed |

## 🔧 系統工具 / System Tools

| 工具名稱 / Tool Name | 版本/狀態 / Version/Status |
|----------|----------|
| libcamera-hello | rpicam-apps build: v1.7.0 5a3f5965aca9 30-04-2025 (11:42:35) |
| libcamera-still | rpicam-apps build: v1.7.0 5a3f5965aca9 30-04-2025 (11:42:35) |
| v4l2-ctl | v4l2-ctl 1.22.1 |
| ffmpeg | ffmpeg version 5.1.6-0+deb12u1+rpt3 Copyright (c) 2000-2024 the FFmpeg developers |
| git | git version 2.39.5 |
| cmake | 未安裝 / Not Installed |
| gcc | gcc (Debian 12.2.0-14+deb12u1) 12.2.0 |
| g++ | g++ (Debian 12.2.0-14+deb12u1) 12.2.0 |
| pkg-config | 1.8.1 |

## 🧪 功能測試結果 / Function Test Results

- ✅ **opencv**: 成功 / Success
- ✅ **gpio**: 成功 / Success
- ✅ **mediapipe**: 成功 / Success
- ✅ **pygame**: 成功 / Success
- ✅ **tflite**: 成功 / Success

## 📋 Requirements.txt

```
opencv-python==4.11.0.86
opencv-contrib-python==4.11.0.86
numpy==1.26.4
pygame==2.1.2
Pillow==9.4.0
python-dotenv==0.21.0
openai==1.82.1
requests==2.28.1
mediapipe==0.10.18
RPi.GPIO==0.7.1
python-escpos==3.1
pyusb==1.3.1
tflite-runtime==2.14.0
tensorflow==2.19.0
picamera2==0.3.28
```

## 🚀 安裝指令 / Installation Commands

```bash
# 更新系統 / Update system
sudo apt update && sudo apt upgrade -y

# 安裝系統依賴 / Install system dependencies
sudo apt install python3-pip python3-venv git cmake gcc g++ pkg-config -y

# 建立虛擬環境 / Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 安裝 Python 套件 / Install Python packages
pip install -r requirements.txt
```

