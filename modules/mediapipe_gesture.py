import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import cv2
import mediapipe as mp
import numpy as np
import logging
from modules.config import Config

logging.basicConfig(
    filename=os.path.join(Config().log_dir, 'app.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MediaPipeGestureRecognizer:
    """
    MediaPipe 手勢識別器 / MediaPipe gesture recognizer
    
    使用 MediaPipe Hands 進行實時手勢識別，支援 OK 和 YA 手勢
    Uses MediaPipe Hands for real-time gesture recognition, supports OK and YA gestures
    """
    def __init__(self, config: Config):
        """
        初始化 MediaPipe 手勢識別器 / Initialize MediaPipe gesture recognizer
        
        Args:
            config: 配置物件 / Configuration object
        """
        self.config = config
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        # 初始化手部檢測 / Initialize hand detection
        self.hands = self.mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        logger.info("MediaPipe Hands 初始化成功 / MediaPipe Hands initialized successfully")

    def preprocess_frame(self, frame):
        """
        將影格轉換為 RGB 格式以供 MediaPipe 使用 / Convert frame to RGB format for MediaPipe
        
        Args:
            frame: 輸入影格 / Input frame
            
        Returns:
            numpy.ndarray: RGB 格式的影格 / Frame in RGB format
        """
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def calculate_distance(self, point1, point2):
        """
        計算兩個關鍵點之間的歐氏距離 / Calculate Euclidean distance between two keypoints
        
        Args:
            point1: 第一個關鍵點 / First keypoint
            point2: 第二個關鍵點 / Second keypoint
            
        Returns:
            float: 兩點之間的距離 / Distance between two points
        """
        return np.sqrt((point1.x - point2.x)**2 + (point1.y - point2.y)**2)

    def is_finger_extended(self, tip, pip, mcp):
        """
        判斷手指是否伸直（基於關鍵點角度）/ Determine if finger is extended (based on keypoint angles)
        
        Args:
            tip: 指尖關鍵點 / Fingertip keypoint
            pip: 近端指間關節關鍵點 / Proximal interphalangeal joint keypoint
            mcp: 掌指關節關鍵點 / Metacarpophalangeal joint keypoint
            
        Returns:
            bool: 手指是否伸直 / Whether finger is extended
        """
        return (tip.y < pip.y) and (pip.y < mcp.y)

    def predict(self, frame):
        """
        預測手勢並返回置信度與骨骼標記影格 / Predict gesture and return confidence with skeleton marked frame
        
        Args:
            frame: 輸入影格 / Input frame
            
        Returns:
            tuple: (OK信心度, YA信心度, None信心度, 標記影格) / (OK confidence, YA confidence, None confidence, annotated frame)
        """
        try:
            rgb_frame = self.preprocess_frame(frame)
            results = self.hands.process(rgb_frame)
            ok_confidence, ya_confidence = 0, 0
            annotated_frame = frame.copy()

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # 繪製骨骼標記 / Draw skeleton landmarks
                    self.mp_drawing.draw_landmarks(
                        annotated_frame,
                        hand_landmarks,
                        self.mp_hands.HAND_CONNECTIONS,
                        self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=4),
                        self.mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2)
                    )

                    # 獲取關鍵點 / Get keypoints
                    landmarks = hand_landmarks.landmark
                    thumb_tip = landmarks[self.mp_hands.HandLandmark.THUMB_TIP]
                    index_tip = landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
                    middle_tip = landmarks[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
                    ring_tip = landmarks[self.mp_hands.HandLandmark.RING_FINGER_TIP]
                    pinky_tip = landmarks[self.mp_hands.HandLandmark.PINKY_TIP]
                    index_pip = landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_PIP]
                    middle_pip = landmarks[self.mp_hands.HandLandmark.MIDDLE_FINGER_PIP]
                    ring_pip = landmarks[self.mp_hands.HandLandmark.RING_FINGER_PIP]
                    pinky_pip = landmarks[self.mp_hands.HandLandmark.PINKY_PIP]
                    index_mcp = landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_MCP]
                    middle_mcp = landmarks[self.mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
                    ring_mcp = landmarks[self.mp_hands.HandLandmark.RING_FINGER_MCP]
                    pinky_mcp = landmarks[self.mp_hands.HandLandmark.PINKY_MCP]

                    # OK 手勢：拇指與食指接近，其他手指伸直 / OK gesture: thumb and index finger close, other fingers extended
                    thumb_index_dist = self.calculate_distance(thumb_tip, index_tip)
                    max_dist = 0.05  # 假設影格已正規化 / Assuming frame is normalized
                    if thumb_index_dist < max_dist:
                        index_extended = self.is_finger_extended(index_tip, index_pip, index_mcp)
                        middle_extended = self.is_finger_extended(middle_tip, middle_pip, middle_mcp)
                        ring_extended = self.is_finger_extended(ring_tip, ring_pip, ring_mcp)
                        pinky_extended = self.is_finger_extended(pinky_tip, pinky_pip, pinky_mcp)
                        if middle_extended and ring_extended and pinky_extended and not index_extended:
                            ok_confidence = (1 - thumb_index_dist / max_dist) * 100
                            ya_confidence = 0
                        else:
                            ok_confidence = 0
                            ya_confidence = 0
                    else:
                        # YA 手勢：食指與中指伸直，其他手指捲曲 / YA gesture: index and middle fingers extended, other fingers curled
                        index_extended = self.is_finger_extended(index_tip, index_pip, index_mcp)
                        middle_extended = self.is_finger_extended(middle_tip, middle_pip, middle_mcp)
                        ring_extended = self.is_finger_extended(ring_tip, ring_pip, ring_mcp)
                        pinky_extended = self.is_finger_extended(pinky_tip, pinky_pip, pinky_mcp)
                        if index_extended and middle_extended and not ring_extended and not pinky_extended:
                            ya_confidence = 100  # 簡單假設 / Simple assumption
                            ok_confidence = 0
                        else:
                            ok_confidence = 0
                            ya_confidence = 0

            none_confidence = 100 - max(ok_confidence, ya_confidence)
            logger.debug(f"MediaPipe 手勢預測: OK={ok_confidence:.1f}%, YA={ya_confidence:.1f}%, None={none_confidence:.1f}% / MediaPipe gesture prediction: OK={ok_confidence:.1f}%, YA={ya_confidence:.1f}%, None={none_confidence:.1f}%")
            return ok_confidence, ya_confidence, none_confidence, annotated_frame

        except Exception as e:
            logger.error(f"MediaPipe 手勢預測失敗: {e} / MediaPipe gesture prediction failed: {e}")
            return 0, 0, 100, frame

    def cleanup(self):
        """
        釋放 MediaPipe 資源 / Release MediaPipe resources
        """
        self.hands.close()
        logger.info("MediaPipe Hands 資源已釋放 / MediaPipe Hands resources released")
