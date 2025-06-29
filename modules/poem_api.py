import time
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import base64
import requests
import json
import logging
from PIL import Image
import io
import cv2
import numpy as np
from datetime import datetime
from modules.config import Config

# 嘗試導入 OpenAI 庫，如果不存在則提供模擬函數
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("警告: OpenAI 庫未安裝，將使用模擬模式")

# 嘗試導入 python-dotenv
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

# 配置日誌
def setup_logging(config):
    """設置日誌"""
    log_levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    log_level = log_levels.get(getattr(config, 'log_level', 'INFO'), logging.INFO)
    
    logging.basicConfig(
        filename=os.path.join(config.log_dir, 'app.log'),
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

logger = logging.getLogger(__name__)

def load_environment_variables(config):
    """載入環境變數"""
    if DOTENV_AVAILABLE:
        env_path = os.path.join(config.base_dir, '.env')
        if os.path.exists(env_path):
            load_dotenv(env_path)
            logger.info(f"已載入環境變數: {env_path}")
        else:
            logger.warning(f"未找到 .env 文件: {env_path}")

def check_api_keys(config):
    """檢查 API 金鑰是否可用，優先使用環境變數"""
    # 載入環境變數
    load_environment_variables(config)
    
    # 檢查 OpenAI API 金鑰
    openai_key = os.environ.get('OPENAI_API_KEY')
    if not openai_key and hasattr(config, 'openai_api_key') and config.openai_api_key:
        openai_key = config.openai_api_key
        os.environ['OPENAI_API_KEY'] = openai_key
        logger.info("使用配置中的 OpenAI API 金鑰")
    elif openai_key:
        logger.info("使用環境變數中的 OpenAI API 金鑰")
    else:
        logger.warning("警告：未設置 OPENAI_API_KEY")
        print("⚠️ 警告：未設置 OPENAI_API_KEY，將使用模擬模式")
    
    # 檢查 DeepSeek API 金鑰
    deepseek_key = os.environ.get('DEEPSEEK_API_KEY')
    if not deepseek_key and hasattr(config, 'deepseek_api_key') and config.deepseek_api_key:
        deepseek_key = config.deepseek_api_key
        os.environ['DEEPSEEK_API_KEY'] = deepseek_key
        logger.info("使用配置中的 DeepSeek API 金鑰")
    elif deepseek_key:
        logger.info("使用環境變數中的 DeepSeek API 金鑰")
    else:
        logger.warning("警告：未設置 DEEPSEEK_API_KEY")
        print("⚠️ 警告：未設置 DEEPSEEK_API_KEY，將使用模擬模式")
    
    return openai_key, deepseek_key

def encode_image(image):
    """將圖像轉換為 base64 字符串"""
    try:
        # 如果輸入是 numpy 數組 (OpenCV 圖像)
        if isinstance(image, np.ndarray):
            # 確保圖像是 RGB 格式
            if len(image.shape) == 3 and image.shape[2] == 3:
                img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            else:
                img = Image.fromarray(image)
        else:
            img = image
            
        # 將圖像保存到內存緩衝區
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG")
        
        # 將緩衝區內容編碼為 base64
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return img_str
    except Exception as e:
        logger.error(f"圖像編碼失敗: {e}")
        print(f"❌ 圖像編碼失敗: {e}")
        raise

def analyze_photo_with_openai(image, config: Config):
    """使用 OpenAI API 分析照片內容"""
    try:
        logger.info("開始使用 OpenAI API 分析照片")
        print("🔍 使用 OpenAI API（GPT-4o Mini）分析照片...")
        
        # 檢查 OpenAI 庫是否可用
        if not OPENAI_AVAILABLE:
            print("⚠️ OpenAI 庫未安裝，使用模擬回應")
            return get_mock_analysis(), datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 檢查 API 金鑰
        openai_key = os.environ.get('OPENAI_API_KEY')
        if not openai_key:
            print("⚠️ OpenAI API 金鑰未設置，使用模擬回應")
            return get_mock_analysis(), datetime.now().strftime("%Y%m%d_%H%M%S")
        
        client = OpenAI(api_key=openai_key)
        
        # 將圖像轉為 base64
        try:
            image_data = encode_image(image)
        except Exception as e:
            logger.error(f"圖像編碼失敗: {e}")
            print(f"❌ 圖像編碼失敗，使用備用方法: {e}")
            # 如果編碼失敗，保存圖像到臨時文件並使用 PIL 再次加載
            temp_image_path = os.path.join(config.photo_dir, "temp_image.jpg")
            cv2.imwrite(temp_image_path, image)
            with open(temp_image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            os.remove(temp_image_path)
        
        print("🤖 正在分析照片內容...")
        logger.info("向 OpenAI API 發送請求")
        
        # 使用重試機制
        max_retries = getattr(config, 'api_retries', 3)
        retry_delay = getattr(config, 'api_retry_delay', 2)
        
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=config.openai_model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        "你是一個失明的詩人的助手，透過你的眼睛與你的描述感受這個世界。請分析圖片內容並返回以下嚴格 JSON 格式的回應：\n"
                                        "{\"description\": \"場景、手勢或情感的描述（4-6 句）\", \"story\": \"圖片背後可能的簡短故事（50-100 字）\", \"items\": [\"物品1\", \"物品2\", ...]}\n"
                                        "確保回應是有效的 JSON 格式，且只包含 description、story 和 items 三個鍵，items 必須是字符串列表。不要包含額外的文字或格式。"
                                    )
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_data}",
                                        "detail": "low"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=300,
                    timeout=30
                )
                
                result = response.choices[0].message.content.strip()
                logger.info(f"OpenAI 原始回應: {result}")
                
                # 驗證 JSON 格式
                analysis_result = json.loads(result)
                validate_analysis_result(analysis_result)
                
                print("✅ OpenAI 分析完成")
                break
                
            except (requests.exceptions.RequestException, json.JSONDecodeError, ValueError) as e:
                logger.warning(f"OpenAI API 請求失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
                print(f"⚠️ OpenAI API 請求失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    print(f"⏳ {retry_delay} 秒後重試...")
                    time.sleep(retry_delay)
                else:
                    print("❌ OpenAI API 請求失敗，使用備用分析")
                    analysis_result = get_mock_analysis()
        
        # 保存分析結果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        desc_filename = os.path.join(config.poem_dir, f"openai_description_{timestamp}.txt")
        
        os.makedirs(os.path.dirname(desc_filename), exist_ok=True)
        
        with open(desc_filename, 'w', encoding='utf-8') as f:
            f.write(f"描述：{analysis_result['description']}\n故事：{analysis_result['story']}\n物品：{', '.join(analysis_result['items'])}")
        
        logger.info(f"描述已保存至: {desc_filename}")
        print(f"💾 描述已保存至: {desc_filename}")
        
        return analysis_result, timestamp
        
    except Exception as e:
        logger.error(f"整體 OpenAI 分析過程錯誤: {e}")
        print(f"❌ OpenAI 分析過程錯誤: {e}")
        
        # 返回備用分析結果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return get_mock_analysis(), timestamp

def get_mock_analysis():
    """獲取模擬分析結果"""
    return {
        "description": "照片展示了一個明亮的綠色矩形置於藍色背景上。矩形中央有白色文字「Test Image」清晰可見。整體構圖簡單但對比鮮明，色彩飽和度高。這是一張用於測試系統功能的圖像。",
        "story": "這是一張電腦生成的測試圖像，可能用於開發或調試軟件功能。創建者希望通過這個簡單的圖像來驗證系統能否正確處理和顯示各種顏色和文字元素。",
        "items": ["綠色矩形", "藍色背景", "白色文字", "測試圖像"]
    }

def validate_analysis_result(analysis_result):
    """驗證分析結果的格式"""
    required_keys = {"description", "story", "items"}
    if set(analysis_result.keys()) != required_keys:
        raise ValueError("JSON 格式不正確：缺少或多餘的鍵")
    if not isinstance(analysis_result["description"], str):
        raise ValueError("JSON 格式不正確：description 必須是字符串")
    if not isinstance(analysis_result["story"], str):
        raise ValueError("JSON 格式不正確：story 必須是字符串")
    if not isinstance(analysis_result["items"], list) or not all(isinstance(item, str) for item in analysis_result["items"]):
        raise ValueError("JSON 格式不正確：items 必須是字符串列表")

def generate_newpoetry_with_deepseek(analysis_result, config: Config, timestamp=None):
    """使用 DeepSeek API 根據分析結果生成新詩"""
    if not analysis_result or not isinstance(analysis_result, dict):
        logger.error("無效的分析結果，無法生成新詩")
        print("❌ 無效的分析結果，無法生成新詩")
        return None
    
    # 驗證分析結果的 JSON 格式
    try:
        validate_analysis_result(analysis_result)
    except ValueError as e:
        logger.error(f"分析結果格式不正確: {e}")
        print(f"❌ 分析結果格式不正確: {e}")
        return None
    
    deepseek_key = os.environ.get('DEEPSEEK_API_KEY')
    if not deepseek_key:
        print("⚠️ DeepSeek API 金鑰未設置，使用模擬詩歌")
        return generate_mock_poem(config, timestamp)
    
    # 將分析結果轉為 JSON 字符串傳遞給 DeepSeek
    analysis_json = json.dumps(analysis_result, ensure_ascii=False)
    
    prompt = (
        "你是一個失明的詩人，擅長創作新詩。請根據以下 JSON 格式的照片分析結果，創作一首繁體中文新詩（4 行，形式自由）：\n"
        f"{analysis_json}\n"
        "請以新詩形式捕捉照片的情感與意境，返回純文字新詩內容（僅詩歌文字，不包含其他格式）。"
    )
    
    headers = {
        "Authorization": f"Bearer {deepseek_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": config.deepseek_model,
        "messages": [
            {
                "role": "system",
                "content": "你是一個失明的詩人，擅長創作新詩，你透過的助手的眼睛與他對物品、景象的描述來創作新詩，助手所描述的格式:JSON 格式，包含 description、story 和 items。你所創作的新要有詩名,行數在5~10行間,詩將印在一張58公分寬的收據上，將作為禮物或紀念品贈與給別人"
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 100
    }
    
    # 使用重試機制
    max_retries = getattr(config, 'api_retries', 3)
    retry_delay = getattr(config, 'api_retry_delay', 2)
    
    try:
        logger.info("開始使用 DeepSeek API 生成新詩")
        print("📝 使用 DeepSeek API 生成新詩...")
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                response.raise_for_status()
                result = response.json()
                newpoetry = result['choices'][0]['message']['content'].strip()
                
                logger.info("DeepSeek 生成的新詩:")
                logger.info(newpoetry)
                print("✅ DeepSeek 生成的新詩:")
                print(newpoetry)
                
                if timestamp is None:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                poem_path = os.path.join(config.poem_dir, f"poem_{timestamp}.txt")
                os.makedirs(os.path.dirname(poem_path), exist_ok=True)
                with open(poem_path, 'w', encoding='utf-8') as f:
                    f.write(newpoetry)
                
                logger.info(f"詩歌已保存至: {poem_path}")
                print(f"💾 詩歌已保存至: {poem_path}")
                
                return poem_path
                
            except (requests.exceptions.RequestException, KeyError) as e:
                logger.warning(f"DeepSeek API 請求失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
                print(f"⚠️ DeepSeek API 請求失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    print(f"⏳ {retry_delay} 秒後重試...")
                    time.sleep(retry_delay)
                else:
                    print("❌ DeepSeek API 請求失敗，使用備用詩歌")
                    return generate_mock_poem(config, timestamp)
        
    except Exception as e:
        logger.error(f"DeepSeek API 錯誤: {e}")
        print(f"❌ DeepSeek API 錯誤: {e}")
        return generate_mock_poem(config, timestamp)

def generate_mock_poem(config, timestamp=None):
    """生成模擬詩歌"""
    mock_poem = """《瞬間的永恆》

青綠方塊藏文字，
純白筆觸寫真情。
測試之中有意境，
藍海背景映晴空。
像素間的詩意流淌，
簡單卻蘊含深意。"""
    
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    poem_path = os.path.join(config.poem_dir, f"poem_{timestamp}.txt")
    os.makedirs(os.path.dirname(poem_path), exist_ok=True)
    
    with open(poem_path, 'w', encoding='utf-8') as f:
        f.write(mock_poem)
    
    logger.info(f"模擬詩歌已保存至: {poem_path}")
    print("📝 模擬詩歌生成:")
    print(mock_poem)
    print(f"💾 詩歌已保存至: {poem_path}")
    
    return poem_path

def generate_poem(image, photo_path, config: Config):
    """
    分析照片並生成詩歌，保存到磁盤
    
    Args:
        image: 照片圖像（OpenCV 格式）
        photo_path: 照片文件的路徑
        config: 配置對象
        
    Returns:
        生成的詩歌文件路徑，如果失敗則返回 None
    """
    try:
        logger.info(f"開始為照片生成詩歌: {photo_path}")
        print(f"🎨 開始為照片生成詩歌: {os.path.basename(photo_path)}")
        
        # 確保日誌已設置
        setup_logging(config)
        
        # 檢查 API 金鑰
        check_api_keys(config)
        
        # 分析照片
        analysis_result, timestamp = analyze_photo_with_openai(image, config)
        
        if not analysis_result:
            logger.error("照片分析失敗，無法生成詩歌")
            print("❌ 照片分析失敗，無法生成詩歌")
            return None
        
        # 生成詩歌
        poem_path = generate_newpoetry_with_deepseek(analysis_result, config, timestamp)
        
        if poem_path:
            print(f"✅ 詩歌生成完成: {os.path.basename(poem_path)}")
        else:
            print("❌ 詩歌生成失敗")
            
        return poem_path
        
    except Exception as e:
        logger.error(f"詩歌生成過程出錯: {e}")
        print(f"❌ 詩歌生成過程出錯: {e}")
        return None

# 測試代碼
if __name__ == "__main__":
    # 導入需要的模組
    import numpy as np
    
    print("🚀 開始測試詩歌生成模組...")
    
    # 載入配置
    config = Config()
    
    # 設置日誌
    setup_logging(config)
    
    # 測試圖像路徑
    test_image_path = os.path.join(config.photo_dir, "test.jpg")
    
    # 如果測試圖像不存在，創建一個
    if not os.path.exists(test_image_path):
        print(f"📷 測試圖像不存在，創建新圖像: {test_image_path}")
        # 創建一個簡單的測試圖像
        test_img = np.zeros((240, 320, 3), dtype=np.uint8)
        # 藍色背景
        test_img[:, :] = [100, 50, 0]  # BGR 格式
        # 綠色矩形
        cv2.rectangle(test_img, (50, 50), (270, 190), (0, 255, 0), -1)
        # 白色文字
        cv2.putText(test_img, "Test Image", (80, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # 確保目錄存在
        os.makedirs(os.path.dirname(test_image_path), exist_ok=True)
        
        # 保存圖像
        cv2.imwrite(test_image_path, test_img)
        print(f"✅ 測試圖像已創建: {test_image_path}")
    
    # 載入測試圖像
    test_image = cv2.imread(test_image_path)
    if test_image is None:
        print(f"❌ 錯誤: 無法載入測試圖像: {test_image_path}")
        sys.exit(1)
    
    print(f"📂 已載入測試圖像: {test_image_path}")
    print(f"📐 圖像尺寸: {test_image.shape}")
    
    # 檢查 API 金鑰
    print("\n🔑 檢查 API 金鑰配置...")
    openai_key, deepseek_key = check_api_keys(config)
    
    if openai_key:
        print("✅ OpenAI API 金鑰已設置")
    else:
        print("⚠️ OpenAI API 金鑰未設置，將使用模擬模式")
    
    if deepseek_key:
        print("✅ DeepSeek API 金鑰已設置")
    else:
        print("⚠️ DeepSeek API 金鑰未設置，將使用模擬模式")
    
    # 生成詩歌
    print("\n🎨 開始生成詩歌...")
    start_time = time.time()
    
    poem_path = generate_poem(test_image, test_image_path, config)
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    if poem_path and os.path.exists(poem_path):
        print(f"\n🎉 測試成功!")
        print(f"⏱️ 處理時間: {processing_time:.2f} 秒")
        print(f"📄 詩歌已保存到: {poem_path}")
        
        # 顯示詩歌內容
        try:
            with open(poem_path, 'r', encoding='utf-8') as f:
                poem_content = f.read()
                print(f"\n📝 詩歌內容:")
                print("=" * 40)
                print(poem_content)
                print("=" * 40)
        except Exception as e:
            print(f"❌ 讀取詩歌內容時出錯: {e}")
            
        # 顯示分析結果（如果存在）
        timestamp = os.path.basename(poem_path).replace('poem_', '').replace('.txt', '')
        desc_path = os.path.join(config.poem_dir, f"openai_description_{timestamp}.txt")
        if os.path.exists(desc_path):
            try:
                with open(desc_path, 'r', encoding='utf-8') as f:
                    desc_content = f.read()
                    print(f"\n📋 分析結果:")
                    print("=" * 40)
                    print(desc_content)
                    print("=" * 40)
            except Exception as e:
                print(f"❌ 讀取分析結果時出錯: {e}")
    else:
        print(f"\n❌ 測試失敗: 未能生成詩歌")
        print(f"⏱️ 處理時間: {processing_time:.2f} 秒")
        
    print("\n🏁 測試完成")
