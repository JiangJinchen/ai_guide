from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import httpx
import os
import base64
import hashlib
import hmac
import json
import datetime
import re
import asyncio
import websockets
from urllib.parse import urlparse, urlencode
from email.utils import formatdate
from app.database import get_db
from sqlalchemy.orm import Session

from dotenv import load_dotenv
load_dotenv(override=True)

ai_client = httpx.AsyncClient(timeout=60, limits=httpx.Limits(max_connections=10))

router = APIRouter()

class AIRequest(BaseModel):
    text: str
    user_id: str

class ASRRequest(BaseModel):
    audio_data: str
    format: str = "pcm"

class TTSRequest(BaseModel):
    text: str
    voice: str = "female"
    reply_id: str = ""

class RAGRequest(BaseModel):
    query: str

# ======================
# 配置
# ======================
AI_API_KEY = os.getenv("AI_API_KEY", "")

ASR_APP_ID = os.getenv("ASR_APP_ID", "")
ASR_API_KEY = os.getenv("ASR_API_KEY", "")
ASR_API_SECRET = os.getenv("ASR_API_SECRET", "")

TTS_APP_ID = os.getenv("TTS_APP_ID", "")
TTS_API_KEY = os.getenv("TTS_API_KEY", "")
TTS_API_SECRET = os.getenv("TTS_API_SECRET", "")

QWEN_API_URL = "https://apihub.agnes-ai.com/v1/chat/completions"
QWEN_MODEL = "agnes-2.0-flash"

# ======================
# 系统提示词
# ======================
SYSTEM_PROMPT = """
你是【灵山胜境】专属智能导游助手。
回答规则：
1. 如果提供了参考信息（知识库内容），请优先根据参考信息回答，确保准确。
2. 如果没有参考信息或参考信息不够，请根据你自身的知识回答灵山胜境相关问题。
3. 回答必须简洁、准确、有礼貌，控制在120字以内，适合语音播报。
4. 不使用Markdown、表格、项目符号、emoji或复杂符号。
5. 如果问题与灵山胜境完全无关，请礼貌拒绝回答。
"""

def clean_tts_text(text: str, max_chars: int = 320) -> str:
    if not text:
        return ""

    cleaned = str(text)
    cleaned = re.sub(r"[\U00010000-\U0010ffff]", "", cleaned)
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"`([^`]*)`", r"\1", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"^[\s>*#-]+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\n+\s*", "。", cleaned)
    cleaned = re.sub(r"\s*→\s*", "，然后到", cleaned)
    cleaned = re.sub(r"[*_#|]", "", cleaned)
    cleaned = re.sub(r"。{2,}", "。", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" 。\n\t")

    if len(cleaned) > max_chars:
        end = max(cleaned.rfind("。", 0, max_chars), cleaned.rfind("，", 0, max_chars))
        if end < 80:
            end = max_chars
        cleaned = cleaned[:end].rstrip("，。 ") + "。"

    return cleaned

# ======================
# 主推理接口
# ======================
@router.post("/inference")
async def ai_inference(request: AIRequest, db: Session = Depends(get_db)):
    try:
        from app.services.knowledge_service import KnowledgeService
        ks = KnowledgeService()
        ks.sync_from_database(db)
        rag_results = ks.search(request.text, top_k=3)
        knowledge = "\n".join([r["content"] for r in rag_results]) if rag_results else ""
        return await qwen_inference(request.text, request.user_id, knowledge, rag_results)
    except Exception as e:
        print(f"[AI] ai_inference异常: {str(e)}")
        from app.services.knowledge_service import KnowledgeService
        ks = KnowledgeService()
        ks.sync_from_database(db)
        rag_results = ks.search(request.text, top_k=3)
        return await knowledge_fallback_inference(request.text, rag_results)

async def qwen_inference(text: str, user_id: str, knowledge: str = "", rag_results: list = None):
    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json"
    }

    if knowledge:
        user_prompt = f"参考信息：\n{knowledge}\n\n问题：{text}"
    else:
        user_prompt = f"知识库中未检索到相关信息，请根据你自身的知识回答：{text}"

    payload = {
        "model": QWEN_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
    }

    print(f"[AI] 开始调用Agnes AI: {text[:50]}...")
    print(f"[AI] API URL: {QWEN_API_URL}")
    print(f"[AI] API Key: {AI_API_KEY[:20]}...")
    print(f"[AI] Knowledge: {knowledge[:100]}...")

    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            response = await ai_client.post(QWEN_API_URL, headers=headers, json=payload)
            print(f"[AI] Agnes AI状态码: {response.status_code}")
            response.raise_for_status()
            result = response.json()
            print(f"[AI] Agnes AI返回: {json.dumps(result)[:200]}...")
            content = result["choices"][0]["message"]["content"]
            return {"text": content, "confidence": 0.9}
        except httpx.TimeoutException:
            print(f"[AI] Agnes AI超时(第{attempt+1}/{max_retries}次)")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
        except httpx.HTTPStatusError as e:
            print(f"[AI] Agnes AI HTTP错误: {str(e)}")
            if response.status_code in [500, 502, 503, 504] and attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                break
        except Exception as e:
            print(f"[AI] Agnes AI调用失败: {str(e)}")
            break

    print(f"[AI] Agnes AI调用失败，使用知识库降级方案")
    return await knowledge_fallback_inference(text, rag_results)

async def local_fallback_inference(text: str):
    responses = {
        "你好": "您好！我是灵山胜境智能导游。",
        "景点": "灵山胜境有灵山大佛、梵宫、九龙灌浴、五印坛城等著名景点。",
        "门票": "灵山胜境成人票210元，优惠政策请咨询景区。",
        "演出": "梵宫吉祥颂演出每天有多场，具体时间请查看景区公告。",
        "路线": "推荐游览路线：大照壁→五明桥→佛足坛→五智门→菩提大道→九龙灌浴→降魔浮雕→阿育王柱→百子戏弥勒→祥符禅寺→灵山大佛→梵宫→五印坛城。",
        "开放": "灵山胜境开放时间为7:30-17:30，建议提前到达。",
        "历史": "灵山胜境始建于1997年，是国家AAAAA级旅游景区。",
        "文化": "灵山胜境融合了佛教文化、艺术、科技，是华东地区著名的文化旅游胜地。",
        "祈福": "灵山大佛脚下有祈福台，您可以在此祈福许愿。",
        "停车": "景区设有大型停车场，收费标准请现场咨询。",
        "餐饮": "景区内有素斋馆和各类餐饮场所，满足您的用餐需求。",
        "购物": "景区内有特色纪念品商店，您可以选购灵山特色商品。",
        "讲解": "我可以为您详细讲解各个景点的历史和文化内涵。",
        "推荐": "推荐游览时间约3-4小时，建议乘坐景区观光车。",
        "拍照": "灵山大佛和梵宫都是绝佳的拍照地点。",
        "儿童": "1.2米以下儿童免票，1.2-1.5米儿童半票。",
        "老人": "60岁以上老人凭身份证享受优惠。",
        "学生": "全日制学生凭学生证享受优惠。",
        "军人": "现役军人凭军官证免票。",
        "梵宫": "灵山梵宫是一座集建筑、艺术、文化于一体的佛教艺术殿堂，内部装饰精美，值得一看。",
        "大佛": "灵山大佛高88米，是世界上最高的佛像之一，庄严壮观。",
        "九龙灌浴": "九龙灌浴每天定时表演，再现释迦牟尼诞生时的壮观景象。",
        "五印坛城": "五印坛城是藏传佛教风格的建筑，展示了藏传佛教文化。",
        "百子戏弥勒": "百子戏弥勒是一尊大型铜雕，展现了孩童嬉戏的生动场景。",
        "阿育王柱": "阿育王柱高16.9米，是国内最高的阿育王柱。",
        "祥符禅寺": "祥符禅寺是一座千年古刹，历史悠久。",
        "菩提大道": "菩提大道两侧种植了数百棵菩提树，寓意吉祥。",
        "五智门": "五智门是进入景区的第一道大门，寓意佛教五智。",
        "佛足坛": "佛足坛展示了佛陀的足印，象征佛陀的足迹遍布天下。",
        "五明桥": "五明桥是五座汉白玉石桥，代表佛教五明。",
        "大照壁": "灵山大照壁长39.8米，高7米，是华东地区最大的照壁。"
    }
    
    for k, v in responses.items():
        if k in text:
            print(f"[AI] 使用本地回复: {k} → {v[:30]}...")
            return {"text": v, "confidence": 0.8}
    
    default_response = "我是灵山胜境专属导游，只回答景区相关问题。您可以问我关于景点、路线、演出、门票等方面的问题。"
    print(f"[AI] 使用默认回复")
    return {"text": default_response, "confidence": 0.5}

async def knowledge_fallback_inference(text: str, rag_results: list = None):
    if rag_results and len(rag_results) > 0:
        best_result = rag_results[0]
        content = best_result.get("content", "")
        score = best_result.get("score", 0)
        
        print(f"[AI] 使用知识库降级方案，匹配分数: {score}")
        
        if score > 0 and len(content) > 20:
            lines = content.split("\n")
            answer_lines = []
            for line in lines:
                if any(kw in line for kw in ["介绍", "内容", "亮点", "开放", "位置", "内涵"]):
                    clean_line = re.sub(r'^[^\u4e00-\u9fff]+', '', line).strip()
                    if clean_line:
                        answer_lines.append(clean_line)
            
            if answer_lines:
                knowledge_answer = "。".join(answer_lines)
                if len(knowledge_answer) > 150:
                    knowledge_answer = knowledge_answer[:150] + "。"
                print(f"[AI] 知识库生成回答: {knowledge_answer[:50]}...")
                return {"text": knowledge_answer, "confidence": 0.7}
            
            if len(content) > 150:
                content = content[:150] + "。"
            print(f"[AI] 知识库内容直接回答: {content[:50]}...")
            return {"text": content, "confidence": 0.6}
    
    print(f"[AI] 知识库无匹配，使用关键词降级方案")
    return await local_fallback_inference(text)

# ======================
# 讯飞 ASR
# ======================
@router.post("/asr")
async def speech_recognition(request: ASRRequest):
    try:
        if ASR_APP_ID and ASR_API_KEY and ASR_API_SECRET:
            return await xunfei_asr(request.audio_data, request.format)
        else:
            return await local_fallback_asr()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ASR失败：{str(e)}")

def decode_audio_payload(audio_data: str) -> bytes:
    payload = (audio_data or "").split(",")[-1]
    if not payload:
        return b""
    return base64.b64decode(payload)

def extract_wav_pcm(audio_bytes: bytes) -> bytes:
    if len(audio_bytes) < 44 or audio_bytes[:4] != b"RIFF" or audio_bytes[8:12] != b"WAVE":
        return audio_bytes

    offset = 12
    while offset + 8 <= len(audio_bytes):
        chunk_id = audio_bytes[offset:offset + 4]
        chunk_size = int.from_bytes(audio_bytes[offset + 4:offset + 8], "little")
        data_start = offset + 8
        data_end = data_start + chunk_size
        if chunk_id == b"data":
            return audio_bytes[data_start:data_end]
        offset = data_end + (chunk_size % 2)

    return audio_bytes[44:]

def normalize_asr_audio(audio_data: str, audio_format: str) -> bytes:
    audio_bytes = decode_audio_payload(audio_data)
    normalized_format = (audio_format or "pcm").lower()
    if normalized_format in ("wav", "wave", "audio/wav", "audio/x-wav"):
        return extract_wav_pcm(audio_bytes)
    return audio_bytes

async def xunfei_asr(audio_base64: str, format: str = "pcm"):
    app_id = ASR_APP_ID
    api_key = ASR_API_KEY
    api_secret = ASR_API_SECRET

    HOST_URL = "wss://iat-api.xfyun.cn/v2/iat"
    HOST = "iat-api.xfyun.cn"
    PATH = "/v2/iat"

    # 鉴权
    date = formatdate(usegmt=True)
    signature_origin = f"host: {HOST}\ndate: {date}\nGET {PATH} HTTP/1.1"
    
    signature_sha = hmac.new(
        api_secret.encode(),
        signature_origin.encode(),
        hashlib.sha256
    ).digest()
    signature = base64.b64encode(signature_sha).decode()

    authorization_origin = f'''api_key="{api_key}",algorithm="hmac-sha256",headers="host date request-line",signature="{signature}"'''
    authorization = base64.b64encode(authorization_origin.encode()).decode()

    params = {"host": HOST, "date": date, "authorization": authorization}
    auth_url = f"{HOST_URL}?{urlencode(params)}"

    pcm_audio = normalize_asr_audio(audio_base64, format)
    final_text = ""

    try:
        if not pcm_audio:
            return {"text": "无法识别", "confidence": 0}

        print(f"[ASR] format={format}, pcm_bytes={len(pcm_audio)}")

        async with websockets.connect(auth_url) as ws:
            frame_size = 1280
            chunks = [pcm_audio[i:i + frame_size] for i in range(0, len(pcm_audio), frame_size)]

            for index, chunk in enumerate(chunks):
                is_first = index == 0
                is_last = index == len(chunks) - 1
                req = {
                    "data": {
                        "status": 2 if is_last else (0 if is_first else 1),
                        "format": "audio/L16;rate=16000",
                        "encoding": "raw",
                        "audio": base64.b64encode(chunk).decode()
                    }
                }
                if is_first:
                    req["common"] = {"app_id": app_id}
                    req["business"] = {
                        "language": "zh_cn",
                        "domain": "iat",
                        "accent": "mandarin",
                        "ptt": 1
                    }
                await ws.send(json.dumps(req))
                if not is_last:
                    await asyncio.sleep(0.04)

            # 接收识别结果
            while True:
                res = json.loads(await ws.recv())
                if res.get("code") != 0:
                    break

                data = res.get("data", {})
                result = data.get("result")
                if not result:
                    continue

                text = ""
                for w in result.get("ws", []):
                    for cw in w.get("cw", []):
                        text += cw.get("w", "")

                if text:
                    final_text += text

                if data.get("status") == 2:
                    break

    except Exception as e:
        print("ASR错误：", e)

    return {
        "text": final_text.strip() or "无法识别",
        "confidence": 0.95
    }

# ======================
# 讯飞 TTS
# ======================
@router.post("/tts")
async def text_to_speech(request: TTSRequest):
    try:
        speech_text = clean_tts_text(request.text)
        print(
            f"[TTS] reply_id={request.reply_id or '-'} "
            f"input_len={len(request.text or '')}, speech_len={len(speech_text)}, text={speech_text[:80]}"
        )
        if not speech_text:
            return await local_fallback_tts(request.text)

        if TTS_APP_ID and TTS_API_KEY and TTS_API_SECRET:
            return await xunfei_tts(speech_text, request.voice)
        else:
            return await local_fallback_tts(speech_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS失败：{str(e)}")

async def xunfei_tts(text: str, voice: str = "female"):
    APP_ID = TTS_APP_ID
    API_KEY = TTS_API_KEY
    API_SECRET = TTS_API_SECRET
    HOST_URL = "wss://tts-api.xfyun.cn/v2/tts"

    if voice == "female":
        VCN = "x4_xiaoyan"
    elif voice == "male":
        VCN = "aisjiuxu"
    else:
        VCN = "x4_xiaoyan"

    auth_url = create_auth_url(HOST_URL, API_KEY, API_SECRET)
    audio_data = b""

    try:
        async with websockets.connect(auth_url) as websocket:
            req = {
                "common": {"app_id": APP_ID},
                "business": {
                    "aue": "lame",
                    "tte": "UTF8",
                    "vcn": VCN,
                    "speed": 50,
                    "volume": 80
                },
                "data": {
                    "status": 2,
                    "text": base64.b64encode(text.encode("utf-8")).decode()
                }
            }
            await websocket.send(json.dumps(req))

            while True:
                res = json.loads(await websocket.recv())
                if res.get("code") != 0:
                    raise Exception(f"讯飞TTS返回错误 code={res.get('code')}, message={res.get('message')}")
                if "audio" in res.get("data", {}):
                    audio_data += base64.b64decode(res["data"]["audio"])
                if res.get("data", {}).get("status") == 2:
                    break

        if not audio_data:
            raise Exception("讯飞TTS返回空音频")

        return {
            "audio_data": f"data:audio/mp3;base64,{base64.b64encode(audio_data).decode()}",
            "duration": len(text) * 0.3,
            "speech_text": text
        }
    except Exception as e:
        raise Exception(f"TTS失败：{str(e)}")

def create_auth_url(host_url: str, api_key: str, api_secret: str) -> str:
    ul = urlparse(host_url)
    host_name = ul.hostname
    path = ul.path
    date = formatdate(usegmt=True)

    signature_origin = f"host: {host_name}\ndate: {date}\nGET {path} HTTP/1.1"
    signature_sha = hmac.new(
        api_secret.encode(),
        signature_origin.encode(),
        hashlib.sha256
    ).digest()
    signature = base64.b64encode(signature_sha).decode()

    authorization_origin = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )
    authorization = base64.b64encode(authorization_origin.encode()).decode()

    params = {"host": host_name, "date": date, "authorization": authorization}
    return f"{host_url}?{urlencode(params)}"

async def local_fallback_tts(text: str):
    return {"audio_data": "", "duration": 0.3, "note": "请配置TTS密钥"}

# ======================
# RAG
# ======================
@router.post("/rag")
async def rag_retrieval(request: RAGRequest, db: Session = Depends(get_db)):
    try:
        from app.services.knowledge_service import KnowledgeService
        ks = KnowledgeService()
        ks.sync_from_database(db)
        res = ks.search(request.query, top_k=3)
        return {"documents": [r["content"] for r in res], "scores": [r["score"] for r in res]}
    except:
        return {"documents": [], "scores": []}
