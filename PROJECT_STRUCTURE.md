# Poetry Camera 專案架構 / Project Structure

## 📁 根目錄文件 / Root Directory Files

### 核心程式文件 / Core Program Files
- **`main.py`** - 主程式入口點，包含完整的系統邏輯和雙語介面支援
- **`environment_check.py`** - 環境檢查工具，生成詳細的系統環境報告

### 配置文件 / Configuration Files
- **`requirements_tested.txt`** - 經過測試的 Python 依賴套件清單
- **`env_example.txt`** - 環境變數配置範例，用戶可複製為 `.env`
- **`install_dependencies.sh`** - 一鍵安裝腳本，自動設置開發環境

### 文檔文件 / Documentation Files
- **`README.md`** - 主要專案文檔，包含完整的雙語說明
- **`BILINGUAL_UI_SUMMARY.md`** - 雙語介面修改總結
- **`ENVIRONMENT.md`** - 環境測試報告
- **`PROJECT_STRUCTURE.md`** - 本文件，專案架構說明

## 📁 modules/ 目錄 / Modules Directory

### 核心功能模組 / Core Function Modules
- **`config.py`** - 配置管理模組，支援環境變數載入和驗證
- **`camera.py`** - 相機控制模組，支援多種相機初始化方法
- **`gesture.py`** - Teachable Machine 手勢識別模組
- **`mediapipe_gesture.py`** - MediaPipe 手勢識別模組
- **`gpio_control.py`** - GPIO 控制模組，包含音效系統
- **`lcd_display.py`** - LCD 顯示控制模組，支援雙語介面
- **`poem_api.py`** - AI 詩歌生成模組，整合 OpenAI 和 DeepSeek API
- **`printer.py`** - 印表機控制模組，支援雙語輸出

### 備份和舊版本 / Backup and Old Versions
- **`camera_v1.py`** - 相機模組的舊版本
- **`config_v1.py`** - 配置模組的舊版本
- **`old/`** - 舊版本文件目錄

## 📁 models/ 目錄 / Models Directory

### 機器學習模型 / Machine Learning Models
- **`model_unquant.tflite`** - Teachable Machine 訓練的手勢識別模型
- **`labels.txt`** - 手勢標籤文件，定義識別的手勢類型

## 📁 static/ 目錄 / Static Files Directory

### Web 介面文件 / Web Interface Files
- **`index.html`** - 簡單的 Web 介面頁面
- **`floating_window.js`** - 浮動視窗 JavaScript 腳本

## 📁 系統目錄 / System Directories

### 數據存儲 / Data Storage
- **`photos/`** - 照片和詩歌文件存儲目錄
  - 拍攝的照片存儲在此目錄
  - 生成的詩歌文件也存儲在此目錄
- **`logs/`** - 日誌文件存儲目錄
  - 系統運行日誌
  - 錯誤和調試信息

### 開發環境 / Development Environment
- **`venv/`** - Python 虛擬環境目錄
  - 包含所有安裝的 Python 套件
  - 隔離的開發環境

## 🔧 模組功能詳解 / Module Function Details

### 配置管理 (`config.py`)
```python
# 主要功能 / Main Functions:
- 環境變數載入 / Environment variable loading
- 配置驗證 / Configuration validation
- 目錄創建 / Directory creation
- 單例模式 / Singleton pattern
```

### 相機控制 (`camera.py`)
```python
# 支援的相機類型 / Supported Camera Types:
- picamera2 (Raspberry Pi Camera)
- libcamera + GStreamer
- V4L2 + GStreamer
- OpenCV (USB 相機)
- 模擬模式 / Simulation mode
```

### 手勢識別 (`gesture.py`, `mediapipe_gesture.py`)
```python
# 支援的手勢 / Supported Gestures:
- OK 手勢 (拇指與食指形成圓圈)
- YA 手勢 (勝利手勢)
- 無手勢狀態
```

### GPIO 控制 (`gpio_control.py`)
```python
# 支援的 GPIO 庫 / Supported GPIO Libraries:
- lgpio (Raspberry Pi 5)
- gpiozero (高級抽象)
- RPi.GPIO (傳統)
- 模擬模式 / Simulation mode

# 音效系統 / Sound System:
- 開機音效 / Startup sound
- 倒數音效 / Countdown sound
- 拍照音效 / Photo sound
- 成功音效 / Success sound
- 錯誤音效 / Error sound
```

### LCD 顯示 (`lcd_display.py`)
```python
# 雙語支援 / Bilingual Support:
- 自動狀態訊息轉換 / Automatic status message conversion
- 按鈕雙語顯示 / Button bilingual display
- 操作提示雙語 / Operation tips bilingual
- 錯誤訊息雙語 / Error messages bilingual
```

### 詩歌生成 (`poem_api.py`)
```python
# API 整合 / API Integration:
- OpenAI GPT-4o (圖像分析)
- DeepSeek (詩歌生成)
- 重試機制 / Retry mechanism
- 錯誤處理 / Error handling
```

### 印表機控制 (`printer.py`)
```python
# 支援的印表機 / Supported Printers:
- USB 熱敏印表機 / USB thermal printer
- 模擬列印模式 / Simulation print mode
- 雙語頁頭頁尾 / Bilingual header and footer
```

## 🌐 雙語介面架構 / Bilingual Interface Architecture

### 自動轉換機制 / Automatic Conversion Mechanism
```python
# 狀態訊息對應表 / Status Message Mapping
self.status_messages = {
    "系統就緒": "System Ready",
    "正在初始化": "Initializing",
    # ... 更多對應
}

# 自動轉換函數 / Automatic Conversion Function
def _get_bilingual_text(self, chinese_text):
    english_text = self.status_messages.get(chinese_text, chinese_text)
    return f"{chinese_text} / {english_text}"
```

### 按鈕雙語顯示 / Button Bilingual Display
```python
# 按鈕定義結構 / Button Definition Structure
{
    "name": "Teachable Machine",
    "chinese": "Teachable Machine 手勢偵測",
    "english": "Teachable Machine Gesture Detection",
    "rect": pygame.Rect(1100, 100, 600, 80)
}
```

## 🔄 系統流程 / System Flow

### 主要執行流程 / Main Execution Flow
1. **初始化階段** / Initialization Phase
   - 載入配置 / Load configuration
   - 初始化各模組 / Initialize modules
   - 設置雙語介面 / Setup bilingual interface

2. **運行階段** / Runtime Phase
   - 手勢識別 / Gesture recognition
   - 拍照處理 / Photo capture
   - AI 分析 / AI analysis
   - 詩歌生成 / Poetry generation
   - 列印輸出 / Print output

3. **清理階段** / Cleanup Phase
   - 釋放資源 / Release resources
   - 保存日誌 / Save logs

## 📊 依賴關係 / Dependencies

### 核心依賴 / Core Dependencies
```
opencv-python==4.11.0.86      # 圖像處理
mediapipe==0.10.18           # 手勢識別
pygame==2.1.2                # 顯示介面
RPi.GPIO==0.7.1              # GPIO 控制
openai==1.82.1               # OpenAI API
tflite-runtime==2.14.0       # TensorFlow Lite
picamera2==0.3.28            # Raspberry Pi 相機
```

### 可選依賴 / Optional Dependencies
```
python-dotenv==0.21.0        # 環境變數
python-escpos==3.1           # 印表機控制
pyusb==1.3.1                 # USB 設備
```

## 🛠️ 開發指南 / Development Guidelines

### 添加新功能 / Adding New Features
1. 在相應模組中添加功能
2. 更新配置管理
3. 添加雙語支援
4. 更新文檔

### 雙語支援 / Bilingual Support
1. 在 `lcd_display.py` 中添加狀態訊息對應
2. 在主程式中使用中文關鍵字
3. 確保錯誤訊息支援雙語

### 測試 / Testing
1. 運行 `environment_check.py`
2. 測試各模組功能
3. 驗證雙語顯示
4. 檢查錯誤處理

---

**最後更新 / Last Updated**: 2025-06-28  
**版本 / Version**: 1.0 