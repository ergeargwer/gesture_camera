import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
import cv2
import datetime
import time
import numpy as np
import subprocess
import tempfile
from modules.config import Config

# 嘗試導入 picamera2 / Try to import picamera2
try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False
    logging.warning("picamera2 模組不可用，將使用其他方法 / picamera2 module not available, will use other methods")

class Camera:
    """
    相機控制類別 / Camera control class
    
    支援多種相機初始化方法，包括 picamera2、libcamera、V4L2 和 OpenCV
    Supports multiple camera initialization methods including picamera2, libcamera, V4L2 and OpenCV
    """
    def __init__(self, config: Config):
        """
        初始化相機 / Initialize camera
        
        Args:
            config: 配置物件 / Configuration object
        """
        self.config = config
        
        # 配置日誌 / Configure logging
        logging.basicConfig(
            filename=os.path.join(self.config.log_dir, 'app.log'),
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        self.cap = None
        self.picam2 = None
        self.method_used = "none"
        self.retry_count = 3
        self.last_error_time = 0
        self.error_cooldown = 5  # 5秒錯誤冷卻期 / 5-second error cooldown period
        
        # 初始化相機 / Initialize camera
        self._initialize_camera()
    
    def _initialize_camera(self):
        """
        強化的相機初始化，支援多種方法並處理超時問題
        Enhanced camera initialization supporting multiple methods and handling timeout issues
        """
        
        for attempt in range(self.retry_count):
            self.logger.info(f"相機初始化嘗試 {attempt + 1}/{self.retry_count} / Camera initialization attempt {attempt + 1}/{self.retry_count}")
            
            if attempt > 0:
                self.logger.info("等待硬體穩定... / Waiting for hardware to stabilize...")
                time.sleep(3)  # 增加等待時間 / Increase wait time
            
            # 方法1: 嘗試 picamera2 (如果可用) - 最穩定 / Method 1: Try picamera2 (if available) - most stable
            if PICAMERA2_AVAILABLE and self._try_picamera2():
                self.method_used = "picamera2"
                self.logger.info("✅ 使用 picamera2 / Using picamera2")
                return
            
            # 方法2: 嘗試 libcamera + GStreamer - 降低超時風險 / Method 2: Try libcamera + GStreamer - reduce timeout risk
            if self._try_libcamera_gstreamer_safe():
                self.method_used = "libcamera_gstreamer"
                self.logger.info("✅ 使用 libcamera + GStreamer (安全模式) / Using libcamera + GStreamer (safe mode)")
                return
            
            # 方法3: 嘗試 V4L2 + GStreamer / Method 3: Try V4L2 + GStreamer
            if self._try_v4l2_gstreamer():
                self.method_used = "v4l2_gstreamer"
                self.logger.info("✅ 使用 V4L2 + GStreamer / Using V4L2 + GStreamer")
                return
            
            # 方法4: 嘗試 OpenCV / Method 4: Try OpenCV
            if self._try_opencv():
                self.method_used = "opencv"
                self.logger.info("✅ 使用 OpenCV / Using OpenCV")
                return
                
            self.logger.warning(f"第 {attempt + 1} 次嘗試失敗 / Attempt {attempt + 1} failed")
        
        # 所有方法都失敗，使用模擬模式 / All methods failed, use simulation mode
        self.method_used = "simulation"
        self.logger.warning("❌ 所有相機方法都失敗，使用模擬模式 / All camera methods failed, using simulation mode")
    
    def _check_camera_hardware(self):
        """
        檢查相機硬體連線（增強版）/ Check camera hardware connection (enhanced version)
        
        Returns:
            bool: 硬體是否正常 / Whether hardware is normal
        """
        try:
            # 使用更短的超時時間，避免長時間阻塞 / Use shorter timeout to avoid long blocking
            result = subprocess.run(
                ['libcamera-hello', '--list-cameras'], 
                capture_output=True, text=True, timeout=3
            )
            
            if result.returncode == 0 and 'imx708' in result.stdout:
                self.logger.info("相機硬體檢測正常 / Camera hardware detection normal")
                return True
            else:
                self.logger.warning("相機硬體檢測異常 / Camera hardware detection abnormal")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.warning("硬體檢測超時 / Hardware detection timeout")
            return False
        except Exception as e:
            self.logger.warning(f"硬體檢測失敗: {e} / Hardware detection failed: {e}")
            return False
    
    def _try_picamera2(self):
        """
        嘗試使用 picamera2（增強版，處理超時）/ Try using picamera2 (enhanced version, handles timeout)
        
        Returns:
            bool: 是否成功 / Whether successful
        """
        try:
            self.logger.info("嘗試 picamera2... / Trying picamera2...")
            
            # 檢查硬體（但不強制要求）/ Check hardware (but not mandatory)
            hardware_ok = self._check_camera_hardware()
            if not hardware_ok:
                self.logger.warning("硬體檢測異常，但仍嘗試 picamera2 / Hardware detection abnormal, but still trying picamera2")
            
            self.picam2 = Picamera2()
            
            # 使用更保守的配置 / Use more conservative configuration
            preview_config = self.picam2.create_preview_configuration(
                main={"size": (self.config.frame_width, self.config.frame_height)}
            )
            self.picam2.configure(preview_config)
            
            # 啟動相機 / Start camera
            self.picam2.start()
            
            # 等待相機穩定（增加等待時間）/ Wait for camera to stabilize (increase wait time)
            time.sleep(3)
            
            # 測試拍攝（減少測試次數，避免累積超時）/ Test capture (reduce test count to avoid cumulative timeout)
            for test in range(2):
                try:
                    frame = self.picam2.capture_array()
                    if frame is not None and frame.size > 0:
                        self.logger.info("picamera2 測試成功 / picamera2 test successful")
                        return True
                except Exception as e:
                    self.logger.warning(f"picamera2 測試 {test+1} 失敗: {e} / picamera2 test {test+1} failed: {e}")
                time.sleep(1)
            
            # 測試失敗，清理資源 / Test failed, clean up resources
            self.picam2.stop()
            self.picam2 = None
            return False
            
        except Exception as e:
            self.logger.warning(f"picamera2 初始化失敗: {e} / picamera2 initialization failed: {e}")
            if self.picam2:
                try:
                    self.picam2.stop()
                except:
                    pass
                self.picam2 = None
            return False
    
    def _try_libcamera_gstreamer_safe(self):
        """
        嘗試安全的 libcamera + GStreamer 配置 / Try safe libcamera + GStreamer configuration
        
        Returns:
            bool: 是否成功 / Whether successful
        """
        
        # 不強制要求硬體檢測通過 / Don't require hardware detection to pass
        hardware_ok = self._check_camera_hardware()
        if not hardware_ok:
            self.logger.warning("硬體檢測異常，跳過 GStreamer / Hardware detection abnormal, skipping GStreamer")
            return False
        
        # 使用最簡單的配置，減少超時風險 / Use simplest configuration to reduce timeout risk
        pipelines = [
            # 最簡配置，最少的處理 / Simplest configuration, minimal processing
            (
                "libcamerasrc ! "
                "video/x-raw,width=640,height=480,framerate=10/1 ! "
                "videoconvert ! "
                "appsink max-buffers=1 drop=true sync=false emit-signals=false"
            ),
            # 備用配置 / Backup configuration
            (
                "libcamerasrc ! "
                "videoconvert ! "
                "videoscale ! "
                "video/x-raw,width=320,height=240 ! "
                "appsink max-buffers=1 drop=true"
            )
        ]
        
        for i, pipeline in enumerate(pipelines):
            try:
                self.logger.info(f"嘗試安全 libcamera pipeline {i+1}/{len(pipelines)}... / Trying safe libcamera pipeline {i+1}/{len(pipelines)}...")
                cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
                
                if cap.isOpened():
                    # 給相機時間初始化，但不要太長 / Give camera time to initialize, but not too long
                    time.sleep(1.5)
                    
                    # 快速測試，不要過度測試 / Quick test, don't over-test
                    success_count = 0
                    for test in range(3):  # 減少測試次數 / Reduce test count
                        ret, frame = cap.read()
                        if ret and frame is not None and frame.size > 0:
                            success_count += 1
                        time.sleep(0.2)
                    
                    if success_count >= 2:  # 至少 2 次成功 / At least 2 successful
                        self.cap = cap
                        self.logger.info(f"libcamera pipeline {i+1} 成功 / libcamera pipeline {i+1} successful")
                        return True
                    else:
                        cap.release()
                        self.logger.warning(f"libcamera pipeline {i+1} 測試失敗 / libcamera pipeline {i+1} test failed")
                else:
                    self.logger.warning(f"libcamera pipeline {i+1} 無法開啟 / libcamera pipeline {i+1} cannot open")
                    
            except Exception as e:
                self.logger.warning(f"libcamera pipeline {i+1} 錯誤: {e} / libcamera pipeline {i+1} error: {e}")
                if cap:
                    cap.release()
        
        return False
    
    def _try_v4l2_gstreamer(self):
        """
        嘗試 V4L2 + GStreamer / Try V4L2 + GStreamer
        
        Returns:
            bool: 是否成功 / Whether successful
        """
        v4l_devices = ['/dev/video0', '/dev/video1']  # 減少測試設備 / Reduce test devices
        
        for device in v4l_devices:
            if not os.path.exists(device):
                continue
                
            try:
                self.logger.info(f"嘗試 V4L2 設備: {device} / Trying V4L2 device: {device}")
                
                # 使用較低的解析度和幀率 / Use lower resolution and frame rate
                pipeline = (
                    f"v4l2src device={device} ! "
                    "video/x-raw,width=640,height=480,framerate=10/1 ! "
                    "videoconvert ! "
                    "appsink max-buffers=1 drop=true"
                )
                
                cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
                
                if cap.isOpened():
                    time.sleep(0.5)
                    
                    success_count = 0
                    for test in range(3):  # 減少測試次數 / Reduce test count
                        ret, frame = cap.read()
                        if ret and frame is not None and frame.size > 0:
                            success_count += 1
                        time.sleep(0.2)
                    
                    if success_count >= 2:
                        self.cap = cap
                        self.logger.info(f"V4L2 {device} 成功 / V4L2 {device} successful")
                        return True
                    else:
                        cap.release()
                        
            except Exception as e:
                self.logger.warning(f"V4L2 {device} 異常: {e} / V4L2 {device} error: {e}")
        
        return False
    
    def _try_opencv(self):
        """
        嘗試標準 OpenCV / Try standard OpenCV
        
        Returns:
            bool: 是否成功 / Whether successful
        """
        camera_indices = [0, 1]  # 減少測試索引 / Reduce test indices
        
        for index in camera_indices:
            try:
                self.logger.info(f"嘗試 OpenCV 索引 {index}... / Trying OpenCV index {index}...")
                cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
                
                if cap.isOpened():
                    # 設置較低的參數 / Set lower parameters
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    cap.set(cv2.CAP_PROP_FPS, 10)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    
                    time.sleep(1)
                    
                    # 清除初始幀 / Clear initial frames
                    for _ in range(3):
                        cap.read()
                    
                    # 簡化測試 / Simplified test
                    success_count = 0
                    for test in range(3):
                        ret, frame = cap.read()
                        if ret and frame is not None and frame.size > 0:
                            success_count += 1
                        time.sleep(0.2)
                    
                    if success_count >= 2:
                        self.cap = cap
                        self.logger.info(f"OpenCV 索引 {index} 成功 / OpenCV index {index} successful")
                        return True
                    else:
                        cap.release()
                        
            except Exception as e:
                self.logger.warning(f"OpenCV 索引 {index} 異常: {e} / OpenCV index {index} error: {e}")
        
        return False

    def get_frame(self):
        """
        獲取一幀圖像（增強錯誤處理）/ Get a frame (enhanced error handling)
        
        Returns:
            numpy.ndarray: 圖像幀 / Image frame
        """
        current_time = time.time()
        
        # 如果在錯誤冷卻期內，返回模擬畫面 / If in error cooldown period, return simulated frame
        if current_time - self.last_error_time < self.error_cooldown:
            if self.method_used != "simulation":
                return self._get_simulated_frame()
        
        if self.method_used == "simulation":
            return self._get_simulated_frame()
        
        if self.method_used == "picamera2":
            try:
                if self.picam2:
                    # 捕捉 RGB 格式的影格 / Capture frame in RGB format
                    frame = self.picam2.capture_array()
                    # 轉換為 BGR (OpenCV 格式) / Convert to BGR (OpenCV format)
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    
                    # 調整到目標解析度 / Resize to target resolution
                    if frame.shape[:2] != (self.config.frame_height, self.config.frame_width):
                        frame = cv2.resize(frame, (self.config.frame_width, self.config.frame_height))
                    
                    return frame
            except Exception as e:
                self.logger.error(f"使用 picamera2 獲取影格失敗: {e} / Failed to get frame using picamera2: {e}")
                self.last_error_time = current_time
                # 不立即重新初始化，避免累積錯誤 / Don't reinitialize immediately to avoid cumulative errors
                return self._get_simulated_frame()
        
        else:
            # 使用 OpenCV/GStreamer / Use OpenCV/GStreamer
            if not self.cap or not self.cap.isOpened():
                self.logger.warning("相機連接中斷 / Camera connection interrupted")
                self.last_error_time = current_time
                return self._get_simulated_frame()
            
            try:
                # 清除緩存但不要太頻繁 / Clear cache but not too frequently
                if hasattr(self.cap, 'grab'):
                    self.cap.grab()
                
                ret, frame = self.cap.read()
                if ret and frame is not None and frame.size > 0:
                    # 調整解析度 / Resize resolution
                    target_height, target_width = self.config.frame_height, self.config.frame_width
                    if frame.shape[:2] != (target_height, target_width):
                        frame = cv2.resize(frame, (target_width, target_height))
                    return frame
                else:
                    self.last_error_time = current_time
                    return self._get_simulated_frame()
                    
            except Exception as e:
                self.logger.warning(f"get_frame 異常: {e} / get_frame error: {e}")
                self.last_error_time = current_time
                return self._get_simulated_frame()
    
    def _get_simulated_frame(self):
        """
        生成模擬畫面（改善版）/ Generate simulated frame (improved version)
        
        Returns:
            numpy.ndarray: 模擬圖像 / Simulated image
        """
        frame = np.ones((self.config.frame_height, self.config.frame_width, 3), dtype=np.uint8) * 50
        
        # 動態元素 / Dynamic elements
        current_time = time.time()
        x = int((np.sin(current_time) + 1) * self.config.frame_width / 4) + self.config.frame_width // 4
        y = int((np.cos(current_time) + 1) * self.config.frame_height / 4) + self.config.frame_height // 4
        
        cv2.circle(frame, (x, y), 20, (100, 150, 200), -1)
        cv2.putText(frame, "Camera Simulation", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, "Timeout recovery mode", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        
        # 顯示冷卻時間
        if self.last_error_time > 0:
            remaining = max(0, self.error_cooldown - (current_time - self.last_error_time))
            if remaining > 0:
                cv2.putText(frame, f"Cooldown: {remaining:.1f}s", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 100, 100), 1)
            else:
                cv2.putText(frame, "Ready to retry", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 1)
        
        return frame

    def capture_photo(self):
        """捕捉照片（增強版）"""
        if self.method_used == "simulation":
            frame = self._get_simulated_frame()
            cv2.putText(frame, "PHOTO CAPTURED", (50, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            return frame
        
        # 優先嘗試 libcamera-still 高質量拍照
        photo = self._try_libcamera_still()
        if photo is not None:
            return photo
        
        # 回退到串流拍照
        self.logger.info("使用串流模式拍照...")
        
        if self.method_used == "picamera2":
            try:
                if self.picam2:
                    # picamera2 高解析度拍照
                    still_config = self.picam2.create_still_configuration(
                        main={"size": (1920, 1080)}
                    )
                    self.picam2.switch_mode_and_capture_image(still_config)
                    frame = self.picam2.capture_array()
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    self.logger.info("picamera2 高解析度拍照成功")
                    return frame
            except Exception as e:
                self.logger.error(f"picamera2 拍照失敗: {e}")
        
        # 使用串流獲取最佳幀
        best_frame = None
        for attempt in range(3):  # 減少嘗試次數
            frame = self.get_frame()
            if frame is not None:
                best_frame = frame
                break
            time.sleep(0.2)
        
        if best_frame is not None:
            self.logger.info("串流拍照成功")
        
        return best_frame
    
    def _try_libcamera_still(self):
        """使用 libcamera-still 拍攝高質量照片（優化版）"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                cmd = [
                    'libcamera-still', 
                    '-o', tmp_file.name,
                    '--camera', '0',
                    '--width', '1920', 
                    '--height', '1080',
                    '--timeout', '1500',  # 進一步減少超時時間
                    '--quality', '95',
                    '--nopreview',
                    '--immediate',
                    '--encoding', 'jpg'
                ]
                
                self.logger.info("使用 libcamera-still 拍攝...")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
                
                if result.returncode == 0 and os.path.exists(tmp_file.name):
                    photo = cv2.imread(tmp_file.name)
                    os.unlink(tmp_file.name)
                    if photo is not None and photo.size > 0:
                        self.logger.info("libcamera-still 拍攝成功")
                        return photo
                else:
                    self.logger.warning(f"libcamera-still 失敗: {result.stderr}")
                
                if os.path.exists(tmp_file.name):
                    os.unlink(tmp_file.name)
                    
        except subprocess.TimeoutExpired:
            self.logger.warning("libcamera-still 超時")
        except Exception as e:
            self.logger.warning(f"libcamera-still 異常: {e}")
        
        return None

    def save_photo(self, photo):
        """保存照片"""
        if photo is None:
            self.logger.warning("無照片可儲存")
            return None
            
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        photo_path = os.path.join(self.config.photo_dir, f"photo_{timestamp}.jpg")
        
        try:
            success = cv2.imwrite(photo_path, photo, [
                cv2.IMWRITE_JPEG_QUALITY, 95,
                cv2.IMWRITE_JPEG_OPTIMIZE, 1
            ])
            if success:
                self.logger.info(f"照片已儲存: {photo_path}")
                return photo_path
            else:
                self.logger.error("照片儲存失敗")
        except Exception as e:
            self.logger.error(f"儲存照片錯誤: {e}")
        
        return None

    def release(self):
        """釋放相機資源"""
        if self.method_used == "picamera2" and self.picam2:
            try:
                self.picam2.stop()
                self.picam2 = None
                self.logger.info("picamera2 資源已釋放")
            except Exception as e:
                self.logger.error(f"picamera2 釋放失敗: {e}")
        
        if self.cap:
            try:
                self.cap.release()
                self.cap = None
                self.logger.info("OpenCV 相機資源已釋放")
            except Exception as e:
                self.logger.error(f"OpenCV 相機釋放失敗: {e}")
        
        self.logger.info(f"相機資源已釋放 (方法: {self.method_used})")
    
    def get_camera_info(self):
        """獲取相機資訊"""
        return {
            'method': self.method_used,
            'available': self.method_used != "simulation",
            'resolution': (self.config.frame_width, self.config.frame_height),
            'hardware': 'Camera Module 3 (imx708)' if self.method_used != "simulation" else 'Simulation',
            'last_error': self.last_error_time,
            'error_cooldown': self.error_cooldown
        }
