import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
import usb.core
from escpos.printer import Usb
from modules.config import Config
from datetime import datetime  # 引入 datetime 用於獲取當前時間

# 配置日誌 / Configure logging
config = Config()
logging.basicConfig(
    filename=os.path.join(config.log_dir, 'app.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_usb_printer():
    """
    檢查 USB 印表機是否可用 / Check if USB printer is available
    
    Returns:
        bool: 印表機是否可用 / Whether printer is available
    """
    try:
        dev = usb.core.find(idVendor=0x28e9, idProduct=0x0289)
        if dev is not None:
            logger.info("找到 EM5820 USB 印表機設備 / Found EM5820 USB printer device")
            return True
        else:
            logger.warning("未找到 EM5820 USB 印表機設備 / EM5820 USB printer device not found")
            return False
    except Exception as e:
        logger.error(f"檢查 USB 印表機時發生錯誤: {e} / Error checking USB printer: {e}")
        return False

def get_printer(config: Config):
    """
    獲取印表機物件 - 直接使用 USB 連接 / Get printer object - direct USB connection
    
    Args:
        config: 配置物件 / Configuration object
        
    Returns:
        Usb: 印表機物件 / Printer object
    """
    try:
        printer = Usb(0x28e9, 0x0289, in_ep=0x81, out_ep=0x03)
        try:
            printer.charcode(config.printer_encoding)
            logger.info(f"印表機字元編碼設置為 {config.printer_encoding} / Printer character encoding set to {config.printer_encoding}")
        except Exception as e:
            logger.warning(f"設置印表機字元編碼失敗（{config.printer_encoding}）: {e} / Failed to set printer character encoding ({config.printer_encoding}): {e}")
        logger.info("印表機初始化成功 (直接 USB 連接) / Printer initialized successfully (direct USB connection)")
        return printer
    except Exception as e:
        logger.error(f"初始化印表機失敗: {e} / Failed to initialize printer: {e}")
        raise

def print_poem(poem_path: str, config: Config):
    """
    列印詩歌 - 添加雙語頁頭與頁尾 / Print poem - add bilingual header and footer
    
    Args:
        poem_path: 詩歌文件路徑 / Poem file path
        config: 配置物件 / Configuration object
    """
    printer = None
    try:
        if not check_usb_printer():
            logger.warning("USB 印表機不可用，進入模擬模式 / USB printer unavailable, entering simulation mode")
            simulate_print(poem_path)
            return
        
        try:
            printer = get_printer(config)
        except Exception as e:
            logger.error(f"無法連接到印表機: {e} / Cannot connect to printer: {e}")
            logger.info("轉入模擬模式 / Switching to simulation mode")
            simulate_print(poem_path)
            return
        
        try:
            printer._raw(b'\x1C\x26')
            logger.info("已啟用印表機中文模式 / Printer Chinese mode enabled")
        except Exception as e:
            logger.warning(f"啟用中文模式失敗: {e} / Failed to enable Chinese mode: {e}")
        
        with open(poem_path, 'r', encoding='utf-8') as f:
            poem = f.read()
        
        poem_encoded = poem
        if config.chinese_mode == "default":
            try:
                poem_encoded = poem.encode('gb18030').decode('gb18030', errors='ignore')
                logger.info("詩歌文本已轉換為 GB18030 編碼 / Poem text converted to GB18030 encoding")
            except Exception as e:
                logger.warning(f"詩歌文本編碼轉換失敗（gb18030）: {e} / Poem text encoding conversion failed (gb18030): {e}")
                poem_encoded = poem
        
        # 列印雙語頁頭、詩歌內容與頁尾 / Print bilingual header, poem content and footer
        try:
            # 雙語頁頭 / Bilingual header
            printer.text("===== 詩歌相機 / Poetry Camera =====\n")
            printer.text("\n")
            # 詩歌內容 / Poem content
            printer.text(poem_encoded)
            printer.text("\n")
            # 雙語頁尾：列印日期與時間 / Bilingual footer: print date and time
            print_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            printer.text("======================\n")
            printer.text(f"列印時間 / Print Time: {print_time}")

            printer.cut()
            logger.info(f"詩歌已成功列印: {poem_path} / Poem printed successfully: {poem_path}")
            print(f"詩歌已成功列印: {os.path.basename(poem_path)} / Poem printed successfully: {os.path.basename(poem_path)}")
        except Exception as e:
            logger.error(f"列印過程中發生錯誤: {e} / Error during printing: {e}")
            raise
        
    except Exception as e:
        logger.error(f"列印詩歌失敗: {e} / Failed to print poem: {e}")
        logger.info("轉入模擬模式 / Switching to simulation mode")
        simulate_print(poem_path)
        
    finally:
        if printer is not None:
            try:
                printer.close()
                logger.info("印表機資源已釋放 / Printer resources released")
            except Exception as e:
                logger.error(f"關閉印表機失敗: {e} / Failed to close printer: {e}")

def simulate_print(poem_path: str):
    """
    模擬列印模式 / Simulation print mode
    
    Args:
        poem_path: 詩歌文件路徑 / Poem file path
    """
    try:
        with open(poem_path, 'r', encoding='utf-8') as f:
            poem = f.read()
        
        print_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print("=" * 50)
        print("===== 詩歌相機 / Poetry Camera =====")
        print(poem)
        print("=" * 50)
        print(f"列印時間 / Print Time: {print_time}")
        
        
        logger.info(f"模擬列印成功: {poem_path} / Simulation print successful: {poem_path}")
    except Exception as e:
        logger.error(f"模擬列印失敗: {e} / Simulation print failed: {e}")
        print(f"模擬列印失敗: {e} / Simulation print failed: {e}")

def test_printer_connection():
    """
    測試印表機連接 / Test printer connection
    
    Returns:
        bool: 測試是否成功 / Whether test was successful
    """
    print("=== 測試印表機連接 / Test Printer Connection ===")
    
    config = Config()
    
    if check_usb_printer():
        print("✓ USB 印表機設備已找到 / USB printer device found")
    else:
        print("✗ USB 印表機設備未找到 / USB printer device not found")
        return False
    
    try:
        printer = get_printer(config)
        print("✓ 印表機初始化成功 / Printer initialized successfully")
        
        try:
            printer._raw(b'\x1C\x26')
            printer.text("===== 詩歌相機 / Poetry Camera =====\n")
            printer.text("測試列印成功! / Test Print Successful!\n")
            print_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            printer.text("=================\n")
            printer.text(f"列印時間 / Print Time: {print_time}")
            printer.cut()
            print("✓ 測試列印成功 / Test print successful")
            return True
        except Exception as e:
            print(f"✗ 測試列印失敗: {e} / Test print failed: {e}")
            return False
        finally:
            printer.close()
            
    except Exception as e:
        print(f"✗ 印表機初始化失敗: {e} / Printer initialization failed: {e}")
        return False

if __name__ == "__main__":
    test_printer_connection()
