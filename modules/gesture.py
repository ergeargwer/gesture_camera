import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import cv2
import logging
from modules.config import Config

# 嘗試導入 tflite_runtime / Try to import tflite_runtime
try:
    import tflite_runtime.interpreter as tflite
    TFLITE_AVAILABLE = True
except ImportError:
    TFLITE_AVAILABLE = False
    logging.error("無法導入 tflite_runtime，請安裝: pip install tflite_runtime / Cannot import tflite_runtime, please install: pip install tflite_runtime")

logging.basicConfig(
    filename=os.path.join(Config().log_dir, 'app.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GestureRecognizer:
    """
    Teachable Machine 手勢識別器 / Teachable Machine gesture recognizer
    
    使用 TensorFlow Lite 模型進行手勢識別，支援 OK、YA、None 三種手勢
    Uses TensorFlow Lite model for gesture recognition, supports OK, YA, None gestures
    """
    def __init__(self, config: Config):
        """
        初始化手勢識別器 / Initialize gesture recognizer
        
        Args:
            config: 配置物件 / Configuration object
            
        Raises:
            ImportError: tflite_runtime 未安裝時拋出 / Raised when tflite_runtime is not installed
            FileNotFoundError: 模型或標籤文件不存在時拋出 / Raised when model or label files don't exist
        """
        self.config = config
        if not TFLITE_AVAILABLE:
            raise ImportError("tflite_runtime 未安裝，無法初始化手勢識別器 / tflite_runtime not installed, cannot initialize gesture recognizer")
            
        try:
            if not os.path.exists(config.model_path):
                raise FileNotFoundError(f"找不到模型文件: {config.model_path} / Model file not found: {config.model_path}")
            if not os.path.exists(config.labels_path):
                raise FileNotFoundError(f"找不到標籤文件: {config.labels_path} / Label file not found: {config.labels_path}")
            
            # 載入 TensorFlow Lite 模型 / Load TensorFlow Lite model
            self.interpreter = tflite.Interpreter(model_path=config.model_path)
            self.interpreter.allocate_tensors()
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            
            logger.info(f"模型輸入形狀: {self.input_details[0]['shape']} / Model input shape: {self.input_details[0]['shape']}")
            
            try:
                # 載入標籤文件 / Load label file
                with open(config.labels_path, 'r') as f:
                    raw_labels = [line.strip() for line in f.readlines()]
                    self.labels = [label.split(' ', 1)[1] if ' ' in label else label 
                                  for label in raw_labels]
                logger.info(f"載入標籤: {self.labels} / Loaded labels: {self.labels}")
            except Exception as e:
                logger.warning(f"載入標籤文件失敗: {e}，使用默認標籤 / Failed to load label file: {e}, using default labels")
                self.labels = ["OK", "YA", "None"]  # 更新默認標籤 / Updated default labels
                
            logger.info(f"手勢識別器初始化成功，類別數: {len(self.labels)} / Gesture recognizer initialized successfully, class count: {len(self.labels)}")
            
        except Exception as e:
            logger.error(f"初始化手勢識別器失敗: {e} / Failed to initialize gesture recognizer: {e}")
            raise

    def preprocess_frame(self, frame):
        """
        預處理影格以符合模型輸入要求 / Preprocess frame to meet model input requirements
        
        Args:
            frame: 輸入影格 / Input frame
            
        Returns:
            numpy.ndarray: 預處理後的影格 / Preprocessed frame
            
        Raises:
            Exception: 預處理失敗時拋出 / Raised when preprocessing fails
        """
        try:
            input_shape = self.input_details[0]['shape']
            input_height, input_width = input_shape[1], input_shape[2]
            # 調整影格大小 / Resize frame
            frame_resized = cv2.resize(frame, (input_width, input_height))
            # 正規化像素值 / Normalize pixel values
            frame_normalized = frame_resized.astype(np.float32) / 255.0
            return np.expand_dims(frame_normalized, axis=0)
        except Exception as e:
            logger.error(f"預處理影格失敗: {e} / Failed to preprocess frame: {e}")
            raise

    def predict(self, frame):
        """
        對影格進行手勢預測 / Perform gesture prediction on frame
        
        Args:
            frame: 輸入影格 / Input frame
            
        Returns:
            tuple: (OK信心度, YA信心度, None信心度) / (OK confidence, YA confidence, None confidence)
        """
        try:
            # 預處理影格 / Preprocess frame
            input_data = self.preprocess_frame(frame)
            # 設置輸入張量 / Set input tensor
            self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
            # 執行推理 / Run inference
            self.interpreter.invoke()
            # 獲取輸出結果 / Get output results
            output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
            confidences = output_data[0]
            
            # 獲取各手勢的索引 / Get indices for each gesture
            ok_idx = self.labels.index("OK") if "OK" in self.labels else 0
            ya_idx = self.labels.index("YA") if "YA" in self.labels else 1
            none_idx = self.labels.index("None") if "None" in self.labels else 2
            
            # 計算信心度百分比 / Calculate confidence percentages
            ok_confidence = confidences[ok_idx] * 100
            ya_confidence = confidences[ya_idx] * 100
            none_confidence = confidences[none_idx] * 100
            
            logger.debug(f"手勢預測: OK={ok_confidence:.1f}%, YA={ya_confidence:.1f}%, None={none_confidence:.1f}% / Gesture prediction: OK={ok_confidence:.1f}%, YA={ya_confidence:.1f}%, None={none_confidence:.1f}%")
            return ok_confidence, ya_confidence, none_confidence
            
        except Exception as e:
            logger.error(f"手勢預測失敗: {e} / Gesture prediction failed: {e}")
            return 0, 0, 0
