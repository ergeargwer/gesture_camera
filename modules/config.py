import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 全域變數，確保只載入一次 / Global variables to ensure loading only once
_env_loaded = False
_config_instance = None

# 嘗試導入 python-dotenv / Try to import python-dotenv
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    print("警告: python-dotenv 未安裝，請執行: pip install python-dotenv / Warning: python-dotenv not installed, please run: pip install python-dotenv")
    print("將使用配置文件中的預設值 / Will use default values from config file")

class Config:
    """
    配置管理類別 / Configuration management class
    
    負責載入和管理所有系統配置，包括相機、GPIO、API 等設置
    Responsible for loading and managing all system configurations including camera, GPIO, API settings
    """
    def __init__(self):
        global _env_loaded, _config_instance
        
        # 單例模式：如果已經有實例，直接返回 / Singleton pattern: if instance exists, return directly
        if _config_instance is not None:
            self.__dict__ = _config_instance.__dict__
            return
        
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        
        # 載入環境變數（只載入一次）/ Load environment variables (only once)
        if not _env_loaded:
            self._load_environment()
            _env_loaded = True
        
        # 相機設置 / Camera settings
        self.camera_index = int(os.getenv('CAMERA_INDEX', 0))
        self.frame_width = int(os.getenv('FRAME_WIDTH', 800))
        self.frame_height = int(os.getenv('FRAME_HEIGHT', 600))
        self.photo_dir = os.path.join(self.base_dir, "photos")
        
        # 模型設置 / Model settings
        self.model_path = os.path.join(self.base_dir, "models", "model_unquant.tflite")
        self.labels_path = os.path.join(self.base_dir, "models", "labels.txt")
        
        # GPIO 設置 / GPIO settings
        self.button_pin = int(os.getenv('BUTTON_PIN', 16))
        self.led_pin = int(os.getenv('LED_PIN', 13))
        self.buzzer_pin = int(os.getenv('BUZZER_PIN', 5))
        
        # 印表機設置 / Printer settings
        self.printer_dev = os.getenv('PRINTER_DEV', "/dev/usblp0")
        self.printer_width = int(os.getenv('PRINTER_WIDTH', 58))
        self.printer_encoding = os.getenv('PRINTER_ENCODING', 'GB18030')
        self.chinese_mode = "default"
        self.poem_dir = os.path.join(self.base_dir, "photos", "poems")
        
        # 顯示設置 / Display settings
        self.screen_width = 1920
        self.screen_height = 1080
        
        # 日誌設置 / Logging settings
        self.log_dir = os.path.join(self.base_dir, "logs")
        self.log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        
        # OpenAI API 設置 - 優先使用環境變數 / OpenAI API settings - prioritize environment variables
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            print("警告: 未在環境變數中找到 OPENAI_API_KEY / Warning: OPENAI_API_KEY not found in environment variables")
            self.openai_api_key = ""
        
        self.openai_model = os.getenv('OPENAI_MODEL', "gpt-4o-mini")
        
        # DeepSeek API 設置 - 優先使用環境變數 / DeepSeek API settings - prioritize environment variables
        self.deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
        if not self.deepseek_api_key:
            print("警告: 未在環境變數中找到 DEEPSEEK_API_KEY / Warning: DEEPSEEK_API_KEY not found in environment variables")
            self.deepseek_api_key = ""
        
        self.deepseek_model = os.getenv('DEEPSEEK_MODEL', "deepseek-chat")
        
        # API 重試設置 / API retry settings
        self.api_retries = int(os.getenv('API_RETRIES', 3))
        self.api_retry_delay = int(os.getenv('API_RETRY_DELAY', 2))
        
        # 手勢識別設置 / Gesture recognition settings
        self.gesture_confidence_threshold = float(os.getenv('GESTURE_CONFIDENCE_THRESHOLD', 95.0))
        self.gesture_detection_frames = int(os.getenv('GESTURE_DETECTION_FRAMES', 3))
        
        # 調試模式 / Debug mode
        self.debug = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes', 'on')
        
        # 確保目錄存在 / Ensure directories exist
        self._create_directories()
        
        # 驗證配置 / Validate configuration
        self._validate_config()
        
        # 儲存單例實例 / Store singleton instance
        _config_instance = self
    
    def _load_environment(self):
        """
        載入環境變數檔案（只載入一次）/ Load environment variables file (only once)
        """
        if DOTENV_AVAILABLE:
            env_path = os.path.join(self.base_dir, '.env')
            if os.path.exists(env_path):
                load_dotenv(env_path)
                print(f"✓ 已載入環境變數配置: {env_path} / Environment variables loaded: {env_path}")
            else:
                print(f"⚠️ 未找到 .env 文件: {env_path} / .env file not found: {env_path}")
        else:
            print("⚠️ python-dotenv 不可用，使用預設值 / python-dotenv not available, using default values")
    
    def _create_directories(self):
        """
        建立必要目錄 / Create necessary directories
        """
        directories = [
            self.photo_dir,
            self.poem_dir, 
            self.log_dir
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        
        # 靜態文件目錄設置 / Static files directory setup
        self.static_dir = os.path.join(self.base_dir, "static")
        os.makedirs(self.static_dir, exist_ok=True)
    
    def _validate_config(self):
        """
        驗證配置 / Validate configuration
        """
        # 驗證 API 金鑰 / Validate API keys
        missing_keys = []
        
        if not self.openai_api_key:
            missing_keys.append("OPENAI_API_KEY")
        
        if not self.deepseek_api_key:
            missing_keys.append("DEEPSEEK_API_KEY")
        
        if missing_keys:
            print("=" * 60)
            print("⚠️  重要：缺少 API 金鑰設置 / Important: Missing API key configuration")
            print("=" * 60)
            print("缺少以下 API 金鑰: / Missing the following API keys:")
            for key in missing_keys:
                print(f"  - {key}")
            print("\n請執行以下步驟: / Please follow these steps:")
            print("1. 複製 .env.example 為 .env / Copy .env.example to .env")
            print("2. 在 .env 文件中填入您的 API 金鑰 / Fill in your API keys in .env file")
            print("3. 確保 .env 文件在專案根目錄 / Ensure .env file is in project root directory")
            print("4. 安裝 python-dotenv: pip install python-dotenv / Install python-dotenv: pip install python-dotenv")
            print("=" * 60)
        else:
            print("✓ API 金鑰配置完成 / API key configuration completed")
        
        # 驗證模型檔案 / Validate model files
        if not os.path.exists(self.model_path):
            print(f"⚠️ 模型檔案不存在: {self.model_path} / Model file does not exist: {self.model_path}")
        
        if not os.path.exists(self.labels_path):
            print(f"⚠️ 標籤檔案不存在: {self.labels_path} / Labels file does not exist: {self.labels_path}")
    
    def get_env_info(self):
        """
        獲取環境配置信息（用於調試）/ Get environment configuration info (for debugging)
        
        Returns:
            dict: 環境配置信息 / Environment configuration information
        """
        info = {
            "DOTENV_AVAILABLE": DOTENV_AVAILABLE,
            "ENV_FILE_EXISTS": os.path.exists(os.path.join(self.base_dir, '.env')),
            "OPENAI_API_KEY_SET": bool(self.openai_api_key),
            "DEEPSEEK_API_KEY_SET": bool(self.deepseek_api_key),
            "DEBUG_MODE": self.debug,
            "LOG_LEVEL": self.log_level
        }
        return info
    
    def print_config_summary(self):
        """
        列印配置摘要（用於調試）/ Print configuration summary (for debugging)
        """
        if not self.debug:
            return
            
        print("\n" + "=" * 50)
        print("🔧 配置摘要 / Configuration Summary")
        print("=" * 50)
        print(f"基礎目錄: {self.base_dir} / Base directory: {self.base_dir}")
        print(f"相機解析度: {self.frame_width}x{self.frame_height} / Camera resolution: {self.frame_width}x{self.frame_height}")
        print(f"GPIO 針腳: 按鈕={self.button_pin}, LED={self.led_pin}, 蜂鳴器={self.buzzer_pin} / GPIO pins: Button={self.button_pin}, LED={self.led_pin}, Buzzer={self.buzzer_pin}")
        print(f"手勢識別閾值: {self.gesture_confidence_threshold}% / Gesture recognition threshold: {self.gesture_confidence_threshold}%")
        print(f"OpenAI 模型: {self.openai_model} / OpenAI model: {self.openai_model}")
        print(f"DeepSeek 模型: {self.deepseek_model} / DeepSeek model: {self.deepseek_model}")
        print(f"API 重試次數: {self.api_retries} / API retry count: {self.api_retries}")
        print(f"日誌級別: {self.log_level} / Log level: {self.log_level}")
        
        env_info = self.get_env_info()
        print("\n🌍 環境狀態: / Environment Status:")
        for key, value in env_info.items():
            status = "✓" if value else "✗"
            print(f"  {status} {key}: {value}")
        print("=" * 50 + "\n")

# 單例模式便利函數 / Singleton pattern convenience function
def get_config():
    """
    獲取配置實例（單例）/ Get configuration instance (singleton)
    
    Returns:
        Config: 配置實例 / Configuration instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
