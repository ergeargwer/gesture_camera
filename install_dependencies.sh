#!/bin/bash

echo "🔧 修復 Raspberry Pi 虛擬環境問題"
echo "=================================="

# 檢查當前位置
echo "📍 當前目錄: $(pwd)"

# 停用當前虛擬環境
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "⚠️  停用當前虛擬環境..."
    deactivate
fi

# 安裝必要的系統套件
echo "📦 安裝系統級 Python 套件..."
sudo apt update
sudo apt install -y python3-full python3-pip python3-venv
sudo apt install -y python3-opencv python3-pygame python3-rpi.gpio
sudo apt install -y gstreamer1.0-tools gstreamer1.0-plugins-base 
sudo apt install -y gstreamer1.0-plugins-good gstreamer1.0-plugins-bad
sudo apt install -y gstreamer1.0-libcamera libcamera-apps

# 移除舊的虛擬環境
if [ -d "venv" ]; then
    echo "🗑️  移除舊的虛擬環境..."
    rm -rf venv
fi

# 建立新的虛擬環境
echo "🔨 建立新的虛擬環境..."
python3 -m venv venv --system-site-packages

# 啟用虛擬環境
echo "✅ 啟用虛擬環境..."
source venv/bin/activate

# 更新 pip
echo "📦 更新 pip..."
pip install --upgrade pip

# 安裝額外的 Python 套件（虛擬環境中）
echo "📦 安裝額外套件..."
pip install mediapipe tensorflow requests pillow

echo "=================================="
echo "🔍 驗證安裝..."

# 驗證核心套件
echo "核心套件:"
python3 -c "import RPi.GPIO; print('✅ RPi.GPIO')" 2>/dev/null || echo "❌ RPi.GPIO"
python3 -c "import cv2; print('✅ OpenCV:', cv2.__version__)" 2>/dev/null || echo "❌ OpenCV"
python3 -c "import pygame; print('✅ Pygame'); pygame.init()" 2>/dev/null || echo "❌ Pygame"

# 驗證 ML 套件
echo "機器學習套件:"
python3 -c "import mediapipe; print('✅ MediaPipe')" 2>/dev/null || echo "❌ MediaPipe"
python3 -c "import tensorflow; print('✅ TensorFlow')" 2>/dev/null || echo "❌ TensorFlow"

# 驗證系統工具
echo "系統工具:"
gst-inspect-1.0 --version >/dev/null 2>&1 && echo "✅ GStreamer" || echo "❌ GStreamer"
libcamera-hello --list-cameras >/dev/null 2>&1 && echo "✅ libcamera" || echo "⚠️  libcamera (需要相機連接)"

echo "=================================="
echo "✅ 設置完成！"
echo ""
echo "現在您可以："
echo "1. source venv/bin/activate  # 啟用虛擬環境"
echo "2. python3 main.py           # 執行程式"
