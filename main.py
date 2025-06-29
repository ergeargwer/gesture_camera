import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import time
import logging
from datetime import datetime
import pygame

# 安全導入 RPi.GPIO / Safe import of RPi.GPIO
try:
    import RPi.GPIO as GPIO
    RPI_GPIO_AVAILABLE = True
except ImportError:
    RPI_GPIO_AVAILABLE = False
    print("⚠️ RPi.GPIO 不可用，將使用相容模式 / RPi.GPIO not available, using compatibility mode")

from modules.camera import Camera
from modules.gesture import GestureRecognizer
from modules.mediapipe_gesture import MediaPipeGestureRecognizer
from modules.poem_api import generate_poem
from modules.printer import print_poem
from modules.gpio_control import GPIOControl
from modules.lcd_display import LCDDisplay
from modules.config import Config
import subprocess

def setup_logging(config):
    """
    設置日誌系統 / Setup logging system
    
    Args:
        config: 配置物件 / Configuration object
    """
    os.makedirs(config.log_dir, exist_ok=True)
    
    # 設置日誌級別 / Set log levels
    log_levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    log_level = log_levels.get(config.log_level, logging.INFO)
    
    logging.basicConfig(
        filename=os.path.join(config.log_dir, 'app.log'),
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # 如果是調試模式，也輸出到控制台 / If in debug mode, also output to console
    if config.debug:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logging.getLogger().addHandler(console_handler)

def main():
    """
    主程式入口點 / Main program entry point
    
    初始化所有模組並運行手勢識別相機系統
    Initializes all modules and runs the gesture recognition camera system
    """
    config = Config()
    setup_logging(config)
    
    # 列印配置摘要（調試模式下）/ Print configuration summary (in debug mode)
    config.print_config_summary()
    
    logging.info("===== Gesture Recognition Camera Program Started =====")
    print("===== 手勢識別詩歌相機程序啟動 / Gesture Recognition Poetry Camera Program Started =====")

    # 初始化各個模組 / Initialize all modules
    try:
        print("🔧 正在初始化系統組件... / Initializing system components...")
        
        camera = Camera(config)
        print("✓ 相機模組初始化完成 / Camera module initialized")
        
        gesture_recognizer = GestureRecognizer(config)
        print("✓ Teachable Machine 手勢識別模組初始化完成 / Teachable Machine gesture recognition module initialized")
        
        mediapipe_recognizer = MediaPipeGestureRecognizer(config)
        print("✓ MediaPipe 手勢識別模組初始化完成 / MediaPipe gesture recognition module initialized")
        
        gpio_control = GPIOControl(config)
        print("✓ GPIO 控制模組初始化完成 / GPIO control module initialized")
        
        lcd_display = LCDDisplay(config)
        print("✓ LCD 顯示模組初始化完成 / LCD display module initialized")
        
        # 播放啟動音效 / Play startup sound
        print("🎵 播放啟動音效... / Playing startup sound...")
        gpio_control.startup_sound()
        
    except Exception as e:
        logging.error(f"模組初始化失敗: {e} / Module initialization failed: {e}")
        print(f"❌ 模組初始化失敗: {e} / Module initialization failed: {e}")
        return

    # 啟動 HTTP 服務器 / Start HTTP server
    server_process = None
    try:
        print("🌐 正在啟動 HTTP 服務器... / Starting HTTP server...")
        server_process = subprocess.Popen(
            ['python3', '-m', 'http.server', '8000', '--directory', config.static_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        logging.info("HTTP server started on port 8000")
        print("✓ HTTP 服務器已在端口 8000 啟動 / HTTP server started on port 8000")
    except Exception as e:
        logging.error(f"Failed to start HTTP server: {e}")
        print(f"❌ HTTP 服務器啟動失敗: {e} / HTTP server startup failed: {e}")

    # 系統狀態變數 / System state variables
    gesture_counter = 0
    current_gesture = None
    in_countdown = False
    is_processing = False
    processed_photos = set()
    
    # 錯誤計數器 / Error counter
    consecutive_errors = 0
    max_consecutive_errors = 10

    def button_callback(channel):
        """
        按鈕回調函數 / Button callback function
        
        Args:
            channel: GPIO 通道 / GPIO channel
        """
        nonlocal consecutive_errors
        
        # 檢查是否為手動模式（支援中英文）/ Check if in manual mode (supports Chinese and English)
        is_manual_mode = ("手動" in lcd_display.current_mode or 
                         "Manual Mode" == lcd_display.current_mode)
        
        if is_manual_mode and not in_countdown and not is_processing:
            logging.info("Button triggered, starting countdown")
            print("🔘 按鈕觸發，開始倒數計時... / Button triggered, starting countdown...")
            gpio_control.button_press_sound()  # 按鈕按下音效 / Button press sound
            start_countdown()
            consecutive_errors = 0

    def start_countdown():
        """
        開始倒數計時 / Start countdown
        
        執行 5 秒倒數計時，期間顯示相機畫面和手勢識別結果
        Executes 5-second countdown while displaying camera feed and gesture recognition results
        """
        nonlocal in_countdown, is_processing, consecutive_errors
        in_countdown = True
        start_time = time.time()
        countdown_duration = 5  # 倒數 5 秒 / Countdown 5 seconds
        
        print("⏰ 開始 5 秒倒數計時... / Starting 5-second countdown...")
        
        while time.time() - start_time < countdown_duration:
            try:
                # 在倒數期間持續獲取並更新畫面 / Continuously capture and update frame during countdown
                frame = camera.get_frame()
                if frame is None:
                    logging.warning("Failed to capture frame during countdown")
                    print("⚠️ 倒數期間無法獲取影格 / Failed to capture frame during countdown")
                    lcd_display.update_status("無法獲取相機畫面")
                    time.sleep(0.1)
                    continue

                remaining_time = int(countdown_duration - (time.time() - start_time)) + 1
                lcd_display.update_status(f"倒數計時: {remaining_time} 秒")
                print(f"⏱️  倒數: {remaining_time} 秒 / Countdown: {remaining_time}s")

                # 根據當前模式更新畫面 / Update display based on current mode
                current_mode = lcd_display.current_mode
                
                if "Teachable Machine" in current_mode:
                    try:
                        ok_conf, ya_conf, none_conf = gesture_recognizer.predict(frame)
                        lcd_display.update_frame(frame)
                        lcd_display.update_confidence(ok_conf, ya_conf, none_conf)
                    except Exception as e:
                        logging.warning(f"Teachable Machine 預測錯誤: {e} / Teachable Machine prediction error: {e}")
                        lcd_display.update_frame(frame)
                        lcd_display.update_confidence(0, 0, 100)
                        
                elif "MediaPipe" in current_mode:
                    try:
                        ok_conf, ya_conf, none_conf, annotated_frame = mediapipe_recognizer.predict(frame)
                        lcd_display.update_frame(annotated_frame)
                        lcd_display.update_confidence(ok_conf, ya_conf, none_conf)
                    except Exception as e:
                        logging.warning(f"MediaPipe 預測錯誤: {e} / MediaPipe prediction error: {e}")
                        lcd_display.update_frame(frame)
                        lcd_display.update_confidence(0, 0, 100)
                else:  # Manual Mode / 手動模式
                    lcd_display.update_frame(frame)
                    lcd_display.update_confidence(0, 0, 100)

                # LED 閃爍和倒數音效 / LED blink and countdown sound
                gpio_control.led_blink(1, 0.2)
                gpio_control.countdown_sound()  # 倒數計時音效 / Countdown sound
                time.sleep(0.3)
                
            except Exception as e:
                logging.error(f"倒數期間錯誤: {e} / Error during countdown: {e}")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    print("❌ 過多錯誤，中止倒數 / Too many errors, aborting countdown")
                    gpio_control.error_sound()
                    break

        # 倒數結束後拍照 / Take photo after countdown
        print("📸 倒數結束，準備拍照... / Countdown finished, preparing to take photo...")
        
        try:
            frame = camera.capture_photo()
            
            if frame is not None:
                logging.info("Photo captured, saving...")
                print("✓ 照片拍攝成功，正在保存... / Photo captured successfully, saving...")
                
                # 拍照音效 / Photo capture sound
                gpio_control.capture_sound()
                
                photo_path = camera.save_photo(frame)
                
                if photo_path and photo_path not in processed_photos:
                    processed_photos.add(photo_path)
                    lcd_display.update_status(f"照片已保存: {os.path.basename(photo_path)}")
                    print(f"✓ 照片已保存: {photo_path}")
                    
                    is_processing = True
                    
                    try:
                        print("🤖 正在生成詩歌... / Generating poem...")
                        lcd_display.update_status("正在分析照片並生成詩歌")
                        gpio_control.processing_sound()  # 處理中音效 / Processing sound
                        
                        poem_path = generate_poem(frame, photo_path, config)
                        
                        if poem_path:
                            lcd_display.update_status(f"詩歌已生成: {os.path.basename(poem_path)}")
                            print(f"✓ 詩歌已生成: {poem_path}")
                            gpio_control.success_sound()  # 成功音效 / Success sound
                            
                            print("🖨️  正在列印詩歌... / Printing poem...")
                            lcd_display.update_status("正在列印詩歌")
                            gpio_control.print_start_sound()  # 開始列印音效 / Starting print sound
                            
                            print_poem(poem_path, config)
                            
                            print("✅ 詩歌列印完成! / Poem printing completed!")
                            lcd_display.update_status("詩歌列印完成")
                            gpio_control.print_complete_sound()  # 列印完成音效 / Print complete sound
                            
                        else:
                            print("❌ 詩歌生成失敗 / Poem generation failed")
                            lcd_display.update_status("詩歌生成失敗")
                            gpio_control.error_sound()  # 錯誤音效 / Error sound
                            
                    except Exception as e:
                        logging.error(f"Poem generation/printing failed: {e}")
                        print(f"❌ 詩歌生成/列印失敗: {e}")
                        lcd_display.update_status("處理失敗")
                        gpio_control.error_sound()  # 錯誤音效 / Error sound
                    finally:
                        is_processing = False
            else:
                print("❌ 拍照失敗 / Photo capture failed")
                lcd_display.update_status("拍照失敗")
                gpio_control.error_sound()  # 錯誤音效 / Error sound
                
        except Exception as e:
            logging.error(f"拍照過程錯誤: {e}")
            print(f"❌ 拍照過程錯誤: {e}")
            gpio_control.error_sound()
            
        in_countdown = False
        lcd_display.update_status("系統就緒")
        gpio_control.system_ready_sound()  # 系統就緒音效 / System ready sound

    # 設置按鈕回調
    gpio_control.setup_button_callback(button_callback)

    # 系統就緒提示
    print("🎵 系統初始化完成，播放就緒音效... / System initialization completed, playing ready sound...")
    gpio_control.system_ready_sound()
    print("✅ 系統就緒，開始運行主迴圈... / System ready, starting main loop...")
    
    try:
        while True:
            # 處理觸控事件 / Handle touch events
            lcd_display.handle_touch_events(button_callback)
            
            # 如果正在倒數或處理中，跳過主要邏輯 / Skip main logic if in countdown or processing
            if in_countdown or is_processing:
                time.sleep(0.5)
                continue

            # 獲取相機影格 / Get camera frame
            frame = camera.get_frame()
            if frame is None:
                logging.warning("Failed to capture frame")
                lcd_display.update_status("無法獲取相機畫面")
                time.sleep(1)
                continue

            # 根據當前模式處理手勢識別 / Handle gesture recognition based on current mode
            current_mode = lcd_display.current_mode
            
            if "Teachable Machine" in current_mode:
                try:
                    ok_conf, ya_conf, none_conf = gesture_recognizer.predict(frame)
                    lcd_display.update_frame(frame)
                    lcd_display.update_confidence(ok_conf, ya_conf, none_conf)
                    
                    # 手勢識別邏輯 / Gesture recognition logic
                    if ok_conf > config.gesture_confidence_threshold:
                        if current_gesture == "OK":
                            gesture_counter += 1
                        else:
                            gesture_counter = 1
                            current_gesture = "OK"
                        if config.debug:
                            print(f"🔍 偵測到 OK 手勢 (信心度: {ok_conf:.1f}%) / Detected OK gesture (confidence: {ok_conf:.1f}%)")
                    elif ya_conf > config.gesture_confidence_threshold:
                        if current_gesture == "YA":
                            gesture_counter += 1
                        else:
                            gesture_counter = 1
                            current_gesture = "YA"
                        if config.debug:
                            print(f"🔍 偵測到 YA 手勢 (信心度: {ya_conf:.1f}%) / Detected YA gesture (confidence: {ya_conf:.1f}%)")
                    else:
                        gesture_counter = 0
                        current_gesture = None
                    
                    # 達到連續識別次數閾值時觸發拍照 / Trigger photo when consecutive recognition threshold is reached
                    if gesture_counter >= config.gesture_detection_frames:
                        logging.info(f"{current_gesture} gesture detected, starting countdown")
                        print(f"✋ {current_gesture} 手勢確認識別，開始倒數計時... / {current_gesture} gesture recognized, starting countdown...")
                        gpio_control.gesture_detected_sound()  # 手勢識別音效 / Gesture recognition sound
                        start_countdown()
                        gesture_counter = 0
                        current_gesture = None
                        
                except Exception as e:
                    logging.error(f"Teachable Machine 錯誤: {e} / Teachable Machine error: {e}")
                    consecutive_errors += 1

            elif "MediaPipe" in current_mode:
                try:
                    ok_conf, ya_conf, none_conf, annotated_frame = mediapipe_recognizer.predict(frame)
                    lcd_display.update_frame(annotated_frame)
                    lcd_display.update_confidence(ok_conf, ya_conf, none_conf)
                    
                    # MediaPipe 手勢識別邏輯 / MediaPipe gesture recognition logic
                    if ok_conf > config.gesture_confidence_threshold:
                        if current_gesture == "OK":
                            gesture_counter += 1
                        else:
                            gesture_counter = 1
                            current_gesture = "OK"
                        if config.debug:
                            print(f"🔍 MediaPipe 偵測到 OK 手勢 (信心度: {ok_conf:.1f}%) / MediaPipe detected OK gesture (confidence: {ok_conf:.1f}%)")
                    elif ya_conf > config.gesture_confidence_threshold:
                        if current_gesture == "YA":
                            gesture_counter += 1
                        else:
                            gesture_counter = 1
                            current_gesture = "YA"
                        if config.debug:
                            print(f"🔍 MediaPipe 偵測到 YA 手勢 (信心度: {ya_conf:.1f}%) / MediaPipe detected YA gesture (confidence: {ya_conf:.1f}%)")
                    else:
                        gesture_counter = 0
                        current_gesture = None
                    
                    # 達到連續識別次數閾值時觸發拍照 / Trigger photo when consecutive recognition threshold is reached
                    if gesture_counter >= config.gesture_detection_frames:
                        logging.info(f"{current_gesture} gesture detected, starting countdown")
                        print(f"✋ MediaPipe {current_gesture} 手勢確認識別，開始倒數計時... / MediaPipe {current_gesture} gesture recognized, starting countdown...")
                        gpio_control.gesture_detected_sound()  # 手勢識別音效 / Gesture recognition sound
                        start_countdown()
                        gesture_counter = 0
                        current_gesture = None
                        
                except Exception as e:
                    logging.error(f"MediaPipe 錯誤: {e} / MediaPipe error: {e}")
                    consecutive_errors += 1

            else:  # Manual Mode / 手動模式
                lcd_display.update_frame(frame)
                lcd_display.update_confidence(0, 0, 100)

            # 重置錯誤計數器 / Reset error counter
            if consecutive_errors > 0:
                consecutive_errors = max(0, consecutive_errors - 0.1)

            time.sleep(0.1)

    except KeyboardInterrupt:
        logging.info("Program interrupted by user")
        print("\n🛑 程序被用戶中斷 / Program interrupted by user")
        
    except Exception as e:
        logging.error(f"Unexpected error in main loop: {e}")
        print(f"❌ 主迴圈發生未預期錯誤: {e} / Unexpected error in main loop: {e}")
        gpio_control.error_sound()  # 錯誤音效 / Error sound
        
    finally:
        print("🧹 正在清理資源... / Cleaning up resources...")
        
        # 清理 HTTP 服務器 / Clean up HTTP server
        if server_process:
            print("🌐 正在停止 HTTP 服務器... / Stopping HTTP server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=2)
                logging.info("HTTP server terminated")
                print("✓ HTTP 服務器已停止 / HTTP server stopped")
            except subprocess.TimeoutExpired:
                server_process.kill()
                logging.warning("HTTP server forcefully killed")
                print("⚠️ HTTP 服務器已強制終止 / HTTP server forcefully killed")
        
        # 清理各個模組 / Clean up all modules
        print("📷 正在釋放相機資源... / Releasing camera resources...")
        camera.release()
        
        print("🔧 正在釋放 GPIO 資源... / Releasing GPIO resources...")
        gpio_control.cleanup()
        
        print("🤖 正在釋放 MediaPipe 資源... / Releasing MediaPipe resources...")
        mediapipe_recognizer.cleanup()
        
        print("🖥️ 正在釋放 LCD 顯示資源... / Releasing LCD display resources...")
        lcd_display.cleanup()
        
        logging.info("===== Program Ended =====")
        print("✅ 程序結束，所有資源已清理完畢 / Program ended, all resources cleaned up")

def check_dependencies():
    """
    檢查依賴項目 / Check dependencies
    
    Returns:
        bool: 依賴項目是否完整 / Whether all dependencies are available
    """
    missing_deps = []
    warnings = []
    
    if not RPI_GPIO_AVAILABLE:
        warnings.append("RPi.GPIO (將使用相容模式 / will use compatibility mode)")
    
    try:
        import cv2
    except ImportError:
        missing_deps.append("opencv-python")
    
    try:
        import pygame
    except ImportError:
        missing_deps.append("pygame")
    
    try:
        from dotenv import load_dotenv
    except ImportError:
        warnings.append("python-dotenv (將使用預設值 / will use default values)")
    
    if missing_deps:
        print("❌ 缺少以下依賴項目: / Missing dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\n請執行以下命令安裝: / Please install with:")
        print(f"pip install {' '.join(missing_deps)}")
        return False
    
    if warnings:
        print("⚠️ 以下項目不可用但可繼續運行: / Following items unavailable but can continue:")
        for warning in warnings:
            print(f"  - {warning}")
    
    return True

if __name__ == "__main__":
    print("🚀 正在啟動手勢識別詩歌相機... / Starting gesture recognition poetry camera...")
    
    # 檢查依賴項目 / Check dependencies
    if not check_dependencies():
        print("❌ 依賴項目檢查失敗，程序無法啟動 / Dependency check failed, program cannot start")
        sys.exit(1)
    
    # 執行主程序 / Execute main program
    main()
