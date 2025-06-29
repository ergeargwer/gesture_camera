import time
import threading
import logging

# 嘗試導入 GPIO 庫（按優先順序）/ Try to import GPIO libraries (in priority order)
GPIO_METHOD = "none"
GPIO_AVAILABLE = False

# 方法1: 嘗試 lgpio (Raspberry Pi 5) / Method 1: Try lgpio (Raspberry Pi 5)
try:
    import lgpio
    GPIO_METHOD = "lgpio"
    GPIO_AVAILABLE = True
    print("✅ 使用 lgpio (Raspberry Pi 5) / Using lgpio (Raspberry Pi 5)")
except ImportError:
    pass

# 方法2: 嘗試 gpiozero (高級抽象) / Method 2: Try gpiozero (high-level abstraction)
if GPIO_METHOD == "none":
    try:
        from gpiozero import LED, Buzzer, Button
        from gpiozero.pins.lgpio import LGPIOFactory
        from gpiozero import Device
        GPIO_METHOD = "gpiozero"
        GPIO_AVAILABLE = True
        print("✅ 使用 gpiozero / Using gpiozero")
    except ImportError:
        pass

# 方法3: 嘗試傳統 RPi.GPIO / Method 3: Try traditional RPi.GPIO
if GPIO_METHOD == "none":
    try:
        import RPi.GPIO as GPIO
        GPIO_METHOD = "rpi_gpio"
        GPIO_AVAILABLE = True
        print("✅ 使用 RPi.GPIO / Using RPi.GPIO")
    except ImportError:
        GPIO_METHOD = "simulation"
        GPIO_AVAILABLE = False
        print("⚠️ GPIO 模擬模式 / GPIO simulation mode")

class GPIOControl:
    """
    GPIO 控制類別 / GPIO control class
    
    管理 LED、蜂鳴器、按鈕等 GPIO 設備，支援多種 GPIO 庫
    Manages GPIO devices like LED, buzzer, button, supports multiple GPIO libraries
    """
    def __init__(self, config):
        """
        初始化 GPIO 控制 / Initialize GPIO control
        
        Args:
            config: 配置物件 / Configuration object
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.led_pin = config.led_pin
        self.buzzer_pin = config.buzzer_pin
        self.button_pin = config.button_pin
        
        # GPIO 物件 / GPIO objects
        self.chip = None
        self.gpio_led = None
        self.gpio_buzzer = None
        self.gpio_button = None
        self.buzzer_pwm = None
        
        # 按鈕監控 / Button monitoring
        self.button_callback = None
        self.button_thread = None
        self.running = True
        
        # 定義音階頻率 (Hz) / Define note frequencies (Hz)
        self.notes = {
            'C4': 261.63,   # Do
            'D4': 293.66,   # Re
            'E4': 329.63,   # Mi
            'F4': 349.23,   # Fa
            'G4': 392.00,   # Sol
            'A4': 440.00,   # La
            'B4': 493.88,   # Ti
            'C5': 523.25,   # 高音Do / High Do
            'D5': 587.33,   # 高音Re / High Re
            'E5': 659.25,   # 高音Mi / High Mi
            'REST': 0       # 休止符 / Rest
        }
        
        # 初始化 GPIO / Initialize GPIO
        self._initialize_gpio()
    
    def _initialize_gpio(self):
        """
        初始化 GPIO / Initialize GPIO
        
        根據可用的 GPIO 庫選擇適當的初始化方法
        Choose appropriate initialization method based on available GPIO library
        """
        
        if GPIO_METHOD == "lgpio":
            self._setup_lgpio()
        elif GPIO_METHOD == "gpiozero":
            self._setup_gpiozero()
        elif GPIO_METHOD == "rpi_gpio":
            self._setup_rpi_gpio()
        else:
            self._setup_simulation()
    
    def _setup_lgpio(self):
        """
        設置 lgpio / Setup lgpio
        
        使用 lgpio 庫初始化 GPIO 設備（適用於 Raspberry Pi 5）
        Initialize GPIO devices using lgpio library (for Raspberry Pi 5)
        """
        try:
            import lgpio
            
            # 開啟 GPIO chip / Open GPIO chip
            self.chip = lgpio.gpiochip_open(0)
            
            # 設置引腳 / Setup pins
            lgpio.gpio_claim_output(self.chip, self.led_pin)
            lgpio.gpio_claim_output(self.chip, self.buzzer_pin) 
            lgpio.gpio_claim_input(self.chip, self.button_pin, lgpio.SET_PULL_UP)
            
            # 儲存 lgpio 模組 / Store lgpio module
            self.lgpio = lgpio
            
            self.logger.info("lgpio 初始化成功 / lgpio initialized successfully")
            
        except Exception as e:
            self.logger.error(f"lgpio 初始化失敗: {e} / lgpio initialization failed: {e}")
            self._setup_simulation()
    
    def _setup_gpiozero(self):
        """
        設置 gpiozero / Setup gpiozero
        
        使用 gpiozero 庫初始化 GPIO 設備（高級抽象）
        Initialize GPIO devices using gpiozero library (high-level abstraction)
        """
        try:
            from gpiozero import LED, Buzzer, Button
            from gpiozero.pins.lgpio import LGPIOFactory
            from gpiozero import Device
            
            # 設置使用 lgpio 作為後端 / Set lgpio as backend
            Device.pin_factory = LGPIOFactory()
            
            # 建立 GPIO 物件 / Create GPIO objects
            self.gpio_led = LED(self.led_pin)
            self.gpio_buzzer = Buzzer(self.buzzer_pin)
            self.gpio_button = Button(self.button_pin, pull_up=True)
            
            self.logger.info("gpiozero 初始化成功 / gpiozero initialized successfully")
            
        except Exception as e:
            self.logger.error(f"gpiozero 初始化失敗: {e} / gpiozero initialization failed: {e}")
            self._setup_simulation()
    
    def _setup_rpi_gpio(self):
        """
        設置傳統 RPi.GPIO / Setup traditional RPi.GPIO
        
        使用傳統 RPi.GPIO 庫初始化 GPIO 設備
        Initialize GPIO devices using traditional RPi.GPIO library
        """
        try:
            import RPi.GPIO as GPIO
            
            # 設置 GPIO 模式 / Set GPIO mode
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # 設置引腳 / Setup pins
            GPIO.setup(self.led_pin, GPIO.OUT)
            GPIO.setup(self.buzzer_pin, GPIO.OUT)
            GPIO.setup(self.button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # 設置 PWM / Setup PWM
            self.buzzer_pwm = GPIO.PWM(self.buzzer_pin, 1000)
            
            self.GPIO = GPIO
            self.logger.info("RPi.GPIO 初始化成功 / RPi.GPIO initialized successfully")
            
        except Exception as e:
            self.logger.error(f"RPi.GPIO 初始化失敗: {e} / RPi.GPIO initialization failed: {e}")
            self._setup_simulation()
    
    def _setup_simulation(self):
        """
        設置模擬模式 / Setup simulation mode
        
        當所有 GPIO 庫都不可用時使用模擬模式
        Use simulation mode when all GPIO libraries are unavailable
        """
        global GPIO_METHOD
        GPIO_METHOD = "simulation"
        self.logger.warning("使用 GPIO 模擬模式 / Using GPIO simulation mode")
    
    def led_on(self):
        """
        LED 開啟 / Turn on LED
        
        根據當前 GPIO 方法開啟 LED
        Turn on LED according to current GPIO method
        """
        if GPIO_METHOD == "lgpio":
            try:
                self.lgpio.gpio_write(self.chip, self.led_pin, 1)
            except Exception as e:
                self.logger.error(f"LED 開啟失敗: {e} / LED turn on failed: {e}")
                
        elif GPIO_METHOD == "gpiozero":
            try:
                self.gpio_led.on()
            except Exception as e:
                self.logger.error(f"LED 開啟失敗: {e} / LED turn on failed: {e}")
                
        elif GPIO_METHOD == "rpi_gpio":
            try:
                self.GPIO.output(self.led_pin, self.GPIO.HIGH)
            except Exception as e:
                self.logger.error(f"LED 開啟失敗: {e} / LED turn on failed: {e}")
        else:
            print("💡 LED 開啟 (模擬) / LED on (simulation)")
    
    def led_off(self):
        """
        LED 關閉 / Turn off LED
        
        根據當前 GPIO 方法關閉 LED
        Turn off LED according to current GPIO method
        """
        if GPIO_METHOD == "lgpio":
            try:
                self.lgpio.gpio_write(self.chip, self.led_pin, 0)
            except Exception as e:
                self.logger.error(f"LED 關閉失敗: {e} / LED turn off failed: {e}")
                
        elif GPIO_METHOD == "gpiozero":
            try:
                self.gpio_led.off()
            except Exception as e:
                self.logger.error(f"LED 關閉失敗: {e} / LED turn off failed: {e}")
                
        elif GPIO_METHOD == "rpi_gpio":
            try:
                self.GPIO.output(self.led_pin, self.GPIO.LOW)
            except Exception as e:
                self.logger.error(f"LED 關閉失敗: {e} / LED turn off failed: {e}")
        else:
            print("💡 LED 關閉 (模擬) / LED off (simulation)")
    
    def led_blink(self, times, delay=0.2):
        """LED 閃爍"""
        def blink():
            for _ in range(times):
                self.led_on()
                time.sleep(delay)
                self.led_off()
                time.sleep(delay)
        
        thread = threading.Thread(target=blink, daemon=True)
        thread.start()
    
    def play_note(self, note, duration=0.3, duty_cycle=50):
        """播放單個音符"""
        if note in self.notes and self.notes[note] > 0:
            frequency = self.notes[note]
            
            if GPIO_METHOD == "lgpio":
                self._play_note_lgpio(frequency, duration, duty_cycle)
            elif GPIO_METHOD == "gpiozero":
                self._play_note_gpiozero(frequency, duration)
            elif GPIO_METHOD == "rpi_gpio":
                self._play_note_rpi_gpio(frequency, duration, duty_cycle)
            else:
                print(f"🎵 播放音符 {note} ({frequency}Hz, {duration}s)")
        elif note == 'REST':
            time.sleep(duration)
    
    def _play_note_lgpio(self, frequency, duration, duty_cycle):
        """使用 lgpio 播放音符"""
        try:
            # 簡單的方波生成
            period = 1.0 / frequency
            half_period = period / 2
            cycles = int(frequency * duration)
            
            for _ in range(cycles):
                self.lgpio.gpio_write(self.chip, self.buzzer_pin, 1)
                time.sleep(half_period * duty_cycle / 100)
                self.lgpio.gpio_write(self.chip, self.buzzer_pin, 0)
                time.sleep(half_period * (100 - duty_cycle) / 100)
                
        except Exception as e:
            self.logger.error(f"lgpio 播放音符失敗: {e}")
    
    def _play_note_gpiozero(self, frequency, duration):
        """使用 gpiozero 播放音符"""
        try:
            # gpiozero 的 Buzzer 不支援頻率，使用簡單的開關
            on_time = 1.0 / frequency / 2
            cycles = int(frequency * duration)
            
            for _ in range(cycles):
                self.gpio_buzzer.on()
                time.sleep(on_time)
                self.gpio_buzzer.off()
                time.sleep(on_time)
                
        except Exception as e:
            self.logger.error(f"gpiozero 播放音符失敗: {e}")
    
    def _play_note_rpi_gpio(self, frequency, duration, duty_cycle):
        """使用 RPi.GPIO 播放音符"""
        try:
            if self.buzzer_pwm:
                self.buzzer_pwm.ChangeFrequency(frequency)
                self.buzzer_pwm.start(duty_cycle)
                time.sleep(duration)
                self.buzzer_pwm.stop()
        except Exception as e:
            self.logger.error(f"RPi.GPIO 播放音符失敗: {e}")
    
    def play_melody(self, melody, note_duration=0.3):
        """播放旋律"""
        for note in melody:
            self.play_note(note, note_duration)
            time.sleep(0.05)  # 音符間的小間隔
    
    # 音效方法（保持與您原版本相容）
    def startup_sound(self):
        """開機提示音 - Do Re Mi 上升音階"""
        melody = ['C4', 'D4', 'E4', 'F4', 'G4']
        self.play_melody(melody, 0.2)
    
    def countdown_sound(self):
        """倒數計時提示音 - 短促的中音"""
        self.play_note('G4', 0.15)
    
    def capture_sound(self):
        """拍照提示音 - 快門聲模擬"""
        self.play_note('C5', 0.1)
        time.sleep(0.05)
        self.play_note('E5', 0.1)
    
    def success_sound(self):
        """成功提示音 - 愉快的上升三和弦"""
        melody = ['C4', 'E4', 'G4', 'C5']
        self.play_melody(melody, 0.25)
    
    def error_sound(self):
        """錯誤提示音 - 下降音階"""
        melody = ['B4', 'A4', 'G4', 'F4']
        self.play_melody(melody, 0.2)
    
    def processing_sound(self):
        """處理中提示音 - 輕柔的雙音循環"""
        melody = ['F4', 'A4', 'F4', 'A4']
        self.play_melody(melody, 0.3)
    
    def gesture_detected_sound(self):
        """手勢識別提示音 - 兩個快速音符"""
        melody = ['E4', 'G4']
        self.play_melody(melody, 0.15)
    
    def print_start_sound(self):
        """開始列印提示音 - 機械感音效"""
        melody = ['D4', 'REST', 'D4', 'REST', 'D4']
        durations = [0.1, 0.05, 0.1, 0.05, 0.1]
        for note, duration in zip(melody, durations):
            self.play_note(note, duration)
    
    def print_complete_sound(self):
        """列印完成提示音 - 完成鈴聲"""
        melody = ['G4', 'C5', 'E5', 'G4', 'C5']
        self.play_melody(melody, 0.2)
    
    def mode_switch_sound(self):
        """模式切換提示音 - 簡短的音階"""
        melody = ['C4', 'E4', 'C4']
        self.play_melody(melody, 0.15)
    
    def button_press_sound(self):
        """按鈕按下提示音 - 單音確認"""
        self.play_note('A4', 0.1)
    
    def system_ready_sound(self):
        """系統就緒提示音 - 和諧的和弦"""
        melody = ['C4', 'E4', 'G4']
        # 同時播放和弦效果（快速連續播放）
        for note in melody:
            threading.Thread(target=self.play_note, args=(note, 0.5), daemon=True).start()
            time.sleep(0.02)
        time.sleep(0.5)
    
    # 保留原有的基本功能
    def buzzer_on(self):
        """開啟蜂鳴器（基本音）"""
        if GPIO_METHOD == "lgpio":
            try:
                self.lgpio.gpio_write(self.chip, self.buzzer_pin, 1)
            except Exception as e:
                self.logger.error(f"蜂鳴器開啟失敗: {e}")
        elif GPIO_METHOD == "gpiozero":
            try:
                self.gpio_buzzer.on()
            except Exception as e:
                self.logger.error(f"蜂鳴器開啟失敗: {e}")
        elif GPIO_METHOD == "rpi_gpio":
            try:
                if self.buzzer_pwm:
                    self.buzzer_pwm.start(50)
                    self.buzzer_pwm.ChangeFrequency(1000)
            except Exception as e:
                self.logger.error(f"蜂鳴器開啟失敗: {e}")
        else:
            print("🔊 蜂鳴器開啟 (模擬)")
    
    def buzzer_off(self):
        """關閉蜂鳴器"""
        if GPIO_METHOD == "lgpio":
            try:
                self.lgpio.gpio_write(self.chip, self.buzzer_pin, 0)
            except Exception as e:
                self.logger.error(f"蜂鳴器關閉失敗: {e}")
        elif GPIO_METHOD == "gpiozero":
            try:
                self.gpio_buzzer.off()
            except Exception as e:
                self.logger.error(f"蜂鳴器關閉失敗: {e}")
        elif GPIO_METHOD == "rpi_gpio":
            try:
                if self.buzzer_pwm:
                    self.buzzer_pwm.stop()
            except Exception as e:
                self.logger.error(f"蜂鳴器關閉失敗: {e}")
        else:
            print("🔊 蜂鳴器關閉 (模擬)")
    
    def buzz(self, duration):
        """使蜂鳴器發聲一段時間"""
        self.buzzer_on()
        time.sleep(duration)
        self.buzzer_off()
    
    def beep(self, times=1, duration=0.1, interval=0.1):
        """發出嗶嗶聲"""
        for i in range(times):
            self.buzz(duration)
            if i < times - 1:
                time.sleep(interval)
    
    def is_button_pressed(self):
        """檢查按鈕是否被按下"""
        if GPIO_METHOD == "lgpio":
            try:
                return not self.lgpio.gpio_read(self.chip, self.button_pin)
            except:
                return False
        elif GPIO_METHOD == "gpiozero":
            try:
                return self.gpio_button.is_pressed
            except:
                return False
        elif GPIO_METHOD == "rpi_gpio":
            try:
                return not self.GPIO.input(self.button_pin)
            except:
                return False
        else:
            return False
    
    def wait_for_button_press(self, timeout=None):
        """等待按鈕按下"""
        if timeout:
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.is_button_pressed():
                    return True
                time.sleep(0.1)
            return False
        else:
            while not self.is_button_pressed():
                time.sleep(0.1)
            return True
    
    def setup_button_callback(self, callback_function):
        """設置按鈕的中斷回調函數"""
        self.button_callback = callback_function
        
        if GPIO_METHOD == "lgpio":
            self._setup_lgpio_callback()
        elif GPIO_METHOD == "gpiozero":
            self._setup_gpiozero_callback()
        elif GPIO_METHOD == "rpi_gpio":
            self._setup_rpi_gpio_callback()
        else:
            self._setup_simulation_callback()
    
    def _setup_lgpio_callback(self):
        """設置 lgpio 按鈕回調"""
        def monitor_button():
            last_state = 1  # 按鈕預設為高電平（上拉）
            while self.running:
                try:
                    current_state = self.lgpio.gpio_read(self.chip, self.button_pin)
                    if current_state == 0 and last_state == 1:  # 按下（下降沿）
                        self.logger.info("按鈕被按下 (lgpio)")
                        if self.button_callback:
                            self.button_callback(self.button_pin)
                        time.sleep(0.3)  # 防抖動
                    last_state = current_state
                    time.sleep(0.01)  # 10ms 輪詢
                except Exception as e:
                    self.logger.error(f"按鈕監控錯誤: {e}")
                    break
        
        self.button_thread = threading.Thread(target=monitor_button, daemon=True)
        self.button_thread.start()
        self.logger.info("lgpio 按鈕監控已啟動")
    
    def _setup_gpiozero_callback(self):
        """設置 gpiozero 按鈕回調"""
        def button_pressed():
            self.logger.info("按鈕被按下 (gpiozero)")
            if self.button_callback:
                self.button_callback(self.button_pin)
        
        try:
            self.gpio_button.when_pressed = button_pressed
            self.logger.info("gpiozero 按鈕回調已設置")
        except Exception as e:
            self.logger.error(f"gpiozero 按鈕回調設置失敗: {e}")
    
    def _setup_rpi_gpio_callback(self):
        """設置 RPi.GPIO 按鈕回調"""
        try:
            self.GPIO.add_event_detect(
                self.button_pin, 
                self.GPIO.FALLING, 
                callback=self.button_callback, 
                bouncetime=300
            )
            self.logger.info("RPi.GPIO 按鈕回調已設置")
        except Exception as e:
            self.logger.error(f"設置按鈕回調時出錯: {e}")
    
    def _setup_simulation_callback(self):
        """設置模擬按鈕回調"""
        def auto_trigger():
            time.sleep(60)  # 等待60秒後開始
            count = 1
            while self.running:
                time.sleep(90)  # 每90秒觸發一次
                if self.running and self.button_callback:
                    print(f"🔘 模擬按鈕觸發 #{count}")
                    self.button_callback(self.button_pin)
                    count += 1
        
        self.button_thread = threading.Thread(target=auto_trigger, daemon=True)
        self.button_thread.start()
        print("🤖 模擬模式：每90秒自動觸發按鈕")
    
    def cleanup(self):
        """清理 GPIO 資源"""
        self.running = False
        
        # 等待按鈕監控線程結束
        if self.button_thread and self.button_thread.is_alive():
            self.button_thread.join(timeout=1)
        
        if GPIO_METHOD == "lgpio":
            try:
                if self.chip is not None:
                    self.lgpio.gpiochip_close(self.chip)
                self.logger.info("lgpio 資源已清理")
            except Exception as e:
                self.logger.error(f"lgpio 清理失敗: {e}")
                
        elif GPIO_METHOD == "gpiozero":
            try:
                if self.gpio_led:
                    self.gpio_led.close()
                if self.gpio_buzzer:
                    self.gpio_buzzer.close()
                if self.gpio_button:
                    self.gpio_button.close()
                self.logger.info("gpiozero 資源已清理")
            except Exception as e:
                self.logger.error(f"gpiozero 清理失敗: {e}")
                
        elif GPIO_METHOD == "rpi_gpio":
            try:
                if self.buzzer_pwm:
                    self.buzzer_pwm.stop()
                self.GPIO.cleanup([self.led_pin, self.buzzer_pin, self.button_pin])
                self.logger.info("RPi.GPIO 資源已清理")
            except Exception as e:
                self.logger.error(f"RPi.GPIO 清理失敗: {e}")
        
        print("🧹 GPIO 資源已清理")
    
    def get_status(self):
        """獲取 GPIO 狀態"""
        return {
            'method': GPIO_METHOD,
            'available': GPIO_AVAILABLE,
            'hardware_mode': GPIO_AVAILABLE,
            'simulation_mode': not GPIO_AVAILABLE
        }
