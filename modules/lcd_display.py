import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
import time
import cv2
import numpy as np
import pygame
from pygame.locals import *
from modules.config import Config

logging.basicConfig(
    filename=os.path.join(Config().log_dir, 'app.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LCDDisplay:
    """
    LCD 顯示控制類別 / LCD display control class
    
    支援中英文並存的介面
    Supports bilingual Chinese-English display for touch screen interface
    """
    def __init__(self, config: Config):
        """
        初始化 LCD 顯示模組 / Initialize LCD display module
        
        Args:
            config: 配置物件 / Configuration object
        """
        self.config = config
        try:
            pygame.init()
            self.screen = pygame.display.set_mode((config.screen_width, config.screen_height))
            pygame.display.set_caption("詩歌相機系統 / Poetry Camera System")  # 雙語標題 / Bilingual title
            
            # 初始化中文字體 / Initialize Chinese fonts
            self._setup_chinese_fonts()
            
            # 復古咖啡色調 / Retro coffee color scheme
            self.BACKGROUND = (139, 69, 19)  # 深咖啡色（背景）/ Dark coffee (background)
            self.FRAME_BORDER = (210, 180, 140)  # 淺棕色（邊框）/ Light brown (border)
            self.BUTTON_INACTIVE = (160, 82, 45)  # 淺咖啡色（按鈕未選中）/ Light coffee (inactive button)
            self.BUTTON_ACTIVE = (205, 133, 63)  # 較亮的棕色（按鈕選中）/ Brighter brown (active button)
            self.TEXT_COLOR = (245, 245, 220)  # 米色（文字）/ Beige (text)
            self.ERROR_COLOR = (255, 100, 100)  # 錯誤訊息顏色 / Error message color
            self.SUCCESS_COLOR = (100, 255, 100)  # 成功訊息顏色 / Success message color
            
            self.frame = None
            self.status_text = "系統就緒 / System Ready"
            self.ok_confidence = 0
            self.ya_confidence = 0
            self.none_confidence = 0
            self.current_mode = "手動模式 / Manual Mode"  # 預設模式改為雙語 / Default mode as bilingual
            
            # 按鈕定義（雙語）/ Button definitions (bilingual)
            self.buttons = [
                {
                    "name": "Teachable Machine", 
                    "chinese": "Teachable Machine 手勢偵測", 
                    "english": "Teachable Machine Gesture Detection",
                    "rect": pygame.Rect(1100, 100, 600, 80)
                },
                {
                    "name": "MediaPipe", 
                    "chinese": "MediaPipe 手勢偵測", 
                    "english": "MediaPipe Gesture Detection",
                    "rect": pygame.Rect(1100, 220, 600, 80)
                },
                {
                    "name": "Manual Mode", 
                    "chinese": "手動模式", 
                    "english": "Manual Mode",
                    "rect": pygame.Rect(1100, 340, 600, 80)
                },
            ]
            
            # 雙語狀態訊息對應 / Bilingual status message mapping
            self.status_messages = {
                "系統就緒": "System Ready",
                "正在初始化": "Initializing",
                "等待相機畫面": "Waiting for Camera",
                "手勢識別中": "Gesture Recognition",
                "倒數計時": "Countdown",
                "拍照中": "Taking Photo",
                "正在分析": "Analyzing",
                "正在生成詩歌": "Generating Poetry",
                "正在列印": "Printing",
                "完成": "Completed",
                "錯誤": "Error",
                "相機錯誤": "Camera Error",
                "網路錯誤": "Network Error",
                "API 錯誤": "API Error",
                "印表機錯誤": "Printer Error",
                "無法獲取相機畫面": "Cannot Get Camera Frame",
                "照片已保存": "Photo Saved",
                "詩歌已生成": "Poem Generated",
                "詩歌列印完成": "Poem Printed",
                "詩歌生成失敗": "Poem Generation Failed",
                "拍照失敗": "Photo Capture Failed",
                "處理失敗": "Processing Failed"
            }
            
            logger.info("LCD 顯示模組初始化成功 / LCD display module initialized successfully")
            
        except Exception as e:
            logger.error(f"初始化 LCD 顯示模組時出錯: {e} / Error initializing LCD display module: {e}")
            pygame.quit()
            raise
    
    def _setup_chinese_fonts(self):
        """
        設置中文字體 / Setup Chinese fonts
        """
        # 中文字體路徑（按優先順序）/ Chinese font paths (in priority order)
        chinese_font_paths = [
            # Linux 常見中文字體 / Common Chinese fonts on Linux
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
            '/usr/share/fonts/truetype/arphic/uming.ttc',
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
            # 專案內字體 / Project fonts
            os.path.join(os.path.dirname(__file__), '..', 'fonts', 'NotoSansCJK-Regular.ttc'),
            # Windows 字體（如果存在）/ Windows fonts (if exists)
            'C:/Windows/Fonts/simhei.ttf',
            'C:/Windows/Fonts/simsun.ttc',
            'C:/Windows/Fonts/msyh.ttc',
        ]
        
        # 找到第一個可用的中文字體 / Find first available Chinese font
        font_path = None
        for path in chinese_font_paths:
            if os.path.exists(path):
                font_path = path
                logger.info(f"找到中文字體: {path} / Found Chinese font: {path}")
                break
        
        try:
            if font_path:
                # 使用找到的中文字體 / Use found Chinese font
                self.font_large = pygame.font.Font(font_path, 60)
                self.font_medium = pygame.font.Font(font_path, 36)
                self.font_small = pygame.font.Font(font_path, 24)
                self.font_tiny = pygame.font.Font(font_path, 18)
                logger.info(f"成功載入中文字體: {os.path.basename(font_path)} / Successfully loaded Chinese font: {os.path.basename(font_path)}")
            else:
                # 後備方案：使用系統字體 / Fallback: use system fonts
                logger.warning("未找到中文字體，使用系統預設字體 / Chinese font not found, using system default fonts")
                self.font_large = pygame.font.SysFont(['SimHei', 'WenQuanYi Zen Hei', 'Noto Sans CJK TC', 'DejaVu Sans'], 60)
                self.font_medium = pygame.font.SysFont(['SimHei', 'WenQuanYi Zen Hei', 'Noto Sans CJK TC', 'DejaVu Sans'], 36)
                self.font_small = pygame.font.SysFont(['SimHei', 'WenQuanYi Zen Hei', 'Noto Sans CJK TC', 'DejaVu Sans'], 24)
                self.font_tiny = pygame.font.SysFont(['SimHei', 'WenQuanYi Zen Hei', 'Noto Sans CJK TC', 'DejaVu Sans'], 18)
                
        except Exception as e:
            logger.error(f"載入中文字體失敗: {e} / Failed to load Chinese font: {e}")
            # 最後後備方案 / Final fallback
            self.font_large = pygame.font.Font(None, 60)
            self.font_medium = pygame.font.Font(None, 36)
            self.font_small = pygame.font.Font(None, 24)
            self.font_tiny = pygame.font.Font(None, 18)
    
    def _safe_render_text(self, text, font, color):
        """
        安全地渲染文字，處理中文顯示問題 / Safely render text, handle Chinese display issues
        
        Args:
            text: 要渲染的文字 / Text to render
            font: 字體 / Font
            color: 顏色 / Color
            
        Returns:
            pygame.Surface: 渲染後的文字表面 / Rendered text surface
        """
        try:
            return font.render(text, True, color)
        except UnicodeError:
            # 如果中文渲染失敗，嘗試用 ASCII / If Chinese rendering fails, try ASCII
            try:
                ascii_text = text.encode('ascii', 'ignore').decode('ascii')
                if ascii_text:
                    return font.render(ascii_text, True, color)
                else:
                    return font.render("Font Error", True, color)
            except:
                return font.render("Display Error", True, color)
        except Exception as e:
            logger.error(f"文字渲染錯誤: {e} / Text rendering error: {e}")
            return font.render("Error", True, color)
    
    def _get_bilingual_text(self, chinese_text):
        """
        獲取雙語文字 / Get bilingual text
        
        Args:
            chinese_text: 中文文字 / Chinese text
            
        Returns:
            str: 雙語文字 / Bilingual text
        """
        english_text = self.status_messages.get(chinese_text, chinese_text)
        return f"{chinese_text} / {english_text}"
    
    def update_frame(self, frame):
        """
        更新相機畫面 / Update camera frame
        
        Args:
            frame: 相機影格 / Camera frame
        """
        self.frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) if frame is not None else None
        self._refresh_display()
    
    def update_status(self, text):
        """
        更新狀態文字 / Update status text
        
        Args:
            text: 狀態文字 / Status text
        """
        # 如果是純中文，轉換為雙語 / If pure Chinese, convert to bilingual
        if '/' not in text and text in self.status_messages:
            self.status_text = self._get_bilingual_text(text)
        else:
            self.status_text = text
        logger.info(f"Status updated: {self.status_text}")
        self._refresh_display()
    
    def update_confidence(self, ok_confidence, ya_confidence, none_confidence):
        """
        更新手勢信心度 / Update gesture confidence
        
        Args:
            ok_confidence: OK 手勢信心度 / OK gesture confidence
            ya_confidence: YA 手勢信心度 / YA gesture confidence
            none_confidence: 無手勢信心度 / No gesture confidence
        """
        self.ok_confidence = ok_confidence
        self.ya_confidence = ya_confidence
        self.none_confidence = none_confidence
        self._refresh_display()
    
    def set_mode(self, mode):
        """
        設置當前模式 / Set current mode
        
        Args:
            mode: 模式名稱 / Mode name
        """
        # 模式名稱對應 / Mode name mapping
        mode_mapping = {
            "Teachable Machine": "Teachable Machine 手勢偵測 / Gesture Detection",
            "MediaPipe": "MediaPipe 手勢偵測 / Gesture Detection", 
            "Manual Mode": "手動模式 / Manual Mode"
        }
        
        self.current_mode = mode_mapping.get(mode, mode)
        logger.info(f"Mode switched to: {mode}")
        self._refresh_display()
    
    def _refresh_display(self):
        """
        刷新顯示畫面 / Refresh display
        """
        try:
            self.screen.fill(self.BACKGROUND)
            
            # 左方相機畫面 (800x600) / Left camera frame (800x600)
            if self.frame is not None:
                frame_resized = cv2.resize(self.frame, (800, 600))
                frame_surface = pygame.surfarray.make_surface(frame_resized.swapaxes(0, 1))
                pos_x = 50
                pos_y = 50
                pygame.draw.rect(self.screen, self.FRAME_BORDER, (pos_x-2, pos_y-2, 804, 604), 4)  # 較粗的邊框 / Thicker border
                self.screen.blit(frame_surface, (pos_x, pos_y))
            else:
                # 沒有畫面時顯示提示 / Show prompt when no frame
                no_frame_rect = pygame.Rect(50, 50, 800, 600)
                pygame.draw.rect(self.screen, (60, 60, 60), no_frame_rect)
                pygame.draw.rect(self.screen, self.FRAME_BORDER, no_frame_rect, 4)
                
                no_frame_text = self._safe_render_text("等待相機畫面... / Waiting for camera...", self.font_medium, self.TEXT_COLOR)
                text_rect = no_frame_text.get_rect(center=no_frame_rect.center)
                self.screen.blit(no_frame_text, text_rect)
            
            # 右方按鈕與置信度 / Right buttons and confidence
            for button in self.buttons:
                # 檢查是否為當前模式 / Check if current mode
                is_active = (button["chinese"] in self.current_mode or 
                           button["english"] in self.current_mode or
                           button["name"] in self.current_mode)
                
                bg_color = self.BUTTON_ACTIVE if is_active else self.BUTTON_INACTIVE
                pygame.draw.rect(self.screen, bg_color, button["rect"], border_radius=10)  # 圓角按鈕 / Rounded button
                
                # 顯示雙語按鈕文字 / Display bilingual button text
                button_text = self._safe_render_text(button["chinese"], self.font_medium, self.TEXT_COLOR)
                text_rect = button_text.get_rect(center=button["rect"].center)
                self.screen.blit(button_text, text_rect)
                
                # 顯示英文按鈕文字 / Display English button text
                button_text_en = self._safe_render_text(button["english"], self.font_small, self.TEXT_COLOR)
                text_rect_en = button_text_en.get_rect(center=(button["rect"].centerx, button["rect"].centery + 25))
                self.screen.blit(button_text_en, text_rect_en)
                
                # 顯示置信度 / Display confidence
                if button["name"] == "Teachable Machine" and "Teachable Machine" in self.current_mode:
                    confidence_text = f"OK: {self.ok_confidence:.1f}% | YA: {self.ya_confidence:.1f}% | 無/None: {self.none_confidence:.1f}%"
                    confidence_surface = self._safe_render_text(confidence_text, self.font_small, self.TEXT_COLOR)
                    confidence_rect = confidence_surface.get_rect(topleft=(button["rect"].left, button["rect"].bottom + 10))
                    self.screen.blit(confidence_surface, confidence_rect)
                elif button["name"] == "MediaPipe" and "MediaPipe" in self.current_mode:
                    confidence_text = f"OK: {self.ok_confidence:.1f}% | YA: {self.ya_confidence:.1f}%"
                    confidence_surface = self._safe_render_text(confidence_text, self.font_small, self.TEXT_COLOR)
                    confidence_rect = confidence_surface.get_rect(topleft=(button["rect"].left, button["rect"].bottom + 10))
                    self.screen.blit(confidence_surface, confidence_rect)
            
            # 右上角顯示當前模式 / Display current mode in top right
            mode_text = f"當前模式 / Current Mode: {self.current_mode}"
            mode_surface = self._safe_render_text(mode_text, self.font_small, self.TEXT_COLOR)
            mode_rect = mode_surface.get_rect(topright=(self.config.screen_width - 50, 50))
            self.screen.blit(mode_surface, mode_rect)
            
            # 底部狀態文字 / Bottom status text
            status_surface = self._safe_render_text(self.status_text, self.font_medium, self.TEXT_COLOR)
            status_rect = status_surface.get_rect(center=(self.config.screen_width // 2, 900))
            pygame.draw.rect(self.screen, self.FRAME_BORDER, (450, 850, 1020, 100), 4)  # 訊息區背景框 / Message area background
            self.screen.blit(status_surface, status_rect)
            
            # 左下角顯示操作提示 / Display operation tips in bottom left
            help_texts = [
                "操作說明 / Instructions:",
                "• 點擊右側按鈕切換模式 / Click right buttons to switch modes",
                "• 手動模式下按空白鍵拍照 / Press spacebar in manual mode to take photo",
                "• 按 ESC 鍵退出程式 / Press ESC to exit program"
            ]
            
            for i, help_text in enumerate(help_texts):
                help_surface = self._safe_render_text(help_text, self.font_small, self.TEXT_COLOR)
                help_rect = help_surface.get_rect(topleft=(50, 700 + i * 30))
                self.screen.blit(help_surface, help_rect)
            
            pygame.display.flip()
            
        except Exception as e:
            logger.error(f"刷新顯示時出錯: {e} / Error refreshing display: {e}")
    
    def handle_touch_events(self, button_callback=None):
        """
        處理觸控事件 / Handle touch events
        
        Args:
            button_callback: 按鈕回調函數 / Button callback function
        """
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                for button in self.buttons:
                    if button["rect"].collidepoint(pos):
                        self.set_mode(button["name"])
                        logger.info(f"Clicked button: {button['name']}")
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                elif event.key == K_SPACE and button_callback and ("手動" in self.current_mode or "Manual" in self.current_mode):
                    button_callback(None)
    
    def cleanup(self):
        """
        清理資源 / Cleanup resources
        """
        try:
            pygame.quit()
            logger.info("LCD 顯示模組資源已釋放 / LCD display module resources released")
        except Exception as e:
            logger.error(f"清理 LCD 顯示模組資源時出錯: {e} / Error cleaning up LCD display module resources: {e}")
