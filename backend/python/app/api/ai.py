from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, AsyncGenerator
import httpx
import os
import base64
import struct
import hashlib
import hmac
import json
import datetime
import re
import asyncio
import time
import websockets
from urllib.parse import urlparse, urlencode
from email.utils import formatdate
from app.database import get_db
from app.utils.streaming import IntentStreamFilter
from app.services.guide_asset_service import save_audio_file
from sqlalchemy.orm import Session

from dotenv import load_dotenv
load_dotenv(override=True)

ai_client = httpx.AsyncClient(timeout=30, limits=httpx.Limits(max_connections=20))

router = APIRouter()

class AIRequest(BaseModel):
    text: str
    user_id: str
    emotion: str = "neutral"
    emotion_reason: str = ""
    history: Optional[list] = None

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
AI_API_URL = os.getenv("AI_API_URL", "https://apihub.agnes-ai.com/v1/chat/completions")
AI_MODEL = os.getenv("AI_MODEL", "agnes-2.0-flash")

ASR_APP_ID = os.getenv("ASR_APP_ID", "")
ASR_API_KEY = os.getenv("ASR_API_KEY", "")
ASR_API_SECRET = os.getenv("ASR_API_SECRET", "")

TTS_APP_ID = os.getenv("TTS_APP_ID", "")
TTS_API_KEY = os.getenv("TTS_API_KEY", "")
TTS_API_SECRET = os.getenv("TTS_API_SECRET", "")

QWEN_API_URL = AI_API_URL
QWEN_MODEL = AI_MODEL
AGNES_STREAM_CONNECT_TIMEOUT = max(0.5, float(os.getenv("AGNES_STREAM_CONNECT_TIMEOUT", "1.5")))
AGNES_STREAM_READ_TIMEOUT = max(3.0, float(os.getenv("AGNES_STREAM_READ_TIMEOUT", "8.0")))
AGNES_CIRCUIT_FAILURE_THRESHOLD = max(1, int(os.getenv("AGNES_CIRCUIT_FAILURE_THRESHOLD", "2")))
AGNES_CIRCUIT_OPEN_SECONDS = max(10, int(os.getenv("AGNES_CIRCUIT_OPEN_SECONDS", "60")))

_AGNES_FAILURE_COUNT = 0
_AGNES_BLOCKED_UNTIL = 0.0


def mask_secret(value: str, keep: int = 4) -> str:
    if not value:
        return "<empty>"
    if len(value) <= keep * 2:
        return "*" * len(value)
    return f"{value[:keep]}...{value[-keep:]}"


def agnes_circuit_is_open() -> bool:
    return time.monotonic() < _AGNES_BLOCKED_UNTIL


def record_agnes_success() -> None:
    global _AGNES_FAILURE_COUNT, _AGNES_BLOCKED_UNTIL
    _AGNES_FAILURE_COUNT = 0
    _AGNES_BLOCKED_UNTIL = 0.0


def record_agnes_failure(reason: str) -> None:
    global _AGNES_FAILURE_COUNT, _AGNES_BLOCKED_UNTIL
    _AGNES_FAILURE_COUNT += 1
    if _AGNES_FAILURE_COUNT >= AGNES_CIRCUIT_FAILURE_THRESHOLD:
        _AGNES_BLOCKED_UNTIL = time.monotonic() + AGNES_CIRCUIT_OPEN_SECONDS
        print(f"[AI] Agnes circuit opened for {AGNES_CIRCUIT_OPEN_SECONDS}s: {reason}")

SERVICE_INTENT_MAP = {
    "ticket": {"name": "购票", "path": "/pages/ticket-assistant/index", "keywords": ["门票", "购票", "票价", "买票", "票", "多少钱"], "icon": "🎫"},
    "activity": {"name": "活动", "path": "/pages/activity-service/index", "keywords": ["演出", "活动", "表演", "禅修", "时间", "节目"], "icon": "🎭"},
    "route": {"name": "路线规划", "path": "/pages/route-planning/index", "keywords": ["路线", "怎么走", "游览路线", "推荐路线", "规划"], "icon": "🗺️"},
    "navigation": {"name": "导航", "path": "/pages/route-navigation/index", "keywords": ["导航", "去", "到", "位置", "在哪", "怎么走"], "icon": "🧭"},
    "guide": {"name": "景点讲解", "path": "/pages/guide/index", "keywords": ["讲解", "介绍", "故事", "文化", "历史"], "icon": "📖"},
    "nearby": {"name": "附近景点", "path": "/pages/nearby-spots/index", "keywords": ["附近", "周边", "景点", "推荐"], "icon": "📍"},
    "recommendation": {"name": "个性化推荐", "path": "/pages/recommendation/index", "keywords": ["推荐", "建议", "好玩", "喜欢"], "icon": "⭐"},
    "profile": {"name": "个人中心", "path": "/pages/profile/index", "keywords": ["我的", "收藏", "偏好", "足迹"], "icon": "👤"}
}

NAVIGATION_SPOTS = ["灵山大佛", "梵宫", "九龙灌浴", "五印坛城", "祥符禅寺", "灵山胜境"]

def recognize_intent_local(text: str) -> dict:
    text_lower = text
    
    matched_service = None
    matched_keyword = None
    max_score = 0
    
    for service_type, config in SERVICE_INTENT_MAP.items():
        for keyword in config["keywords"]:
            if keyword in text_lower:
                score = len(keyword) / len(text_lower) if len(text_lower) > 0 else 0
                if score > max_score:
                    max_score = score
                    matched_service = service_type
                    matched_keyword = keyword
    
    if matched_service:
        params = {}
        if matched_service == "navigation":
            for spot in NAVIGATION_SPOTS:
                if spot in text_lower:
                    params["spot"] = spot
                    break
        
        print(f"[INTENT] 本地规则命中: {matched_service}, keyword={matched_keyword}, score={max_score}")
        return {
            "service": matched_service,
            "params": params,
            "source": "local_rule",
            "confidence": round(max_score, 2)
        }
    
    return {"service": None, "params": {}, "source": "local_rule", "confidence": 0.0}

# ======================
# 系统提示词
# ======================
SYSTEM_PROMPT = """
你是【灵山胜境】专属智能导游助手，你具有情感感知能力，能够根据游客情绪调整回应方式。
回答规则：
1. 如果提供了参考信息（知识库内容），请优先根据参考信息回答，确保准确。
2. 如果没有参考信息或参考信息不够，请根据你自身的知识回答灵山胜境相关问题。
3. 回答必须简洁、准确、有礼貌，必要时可以适当展开，适合语音播报。
4. 不使用Markdown、表格、项目符号、emoji或复杂符号。
5. 如果问题与灵山胜境完全无关，请礼貌拒绝回答。
6. 根据游客情绪调整语气和内容：
   - positive（开心）：用热情、欢快的语气回应，表达分享的喜悦
   - negative（难过/焦虑）：先表达理解和安慰，再提供帮助，语气温和关怀
   - surprised（惊讶）：用好奇、兴奋的语气回应，表现出同感
   - shy（害羞）：用温柔、鼓励的语气回应，让游客感到放松
   - angry（生气）：先真诚道歉，表达理解，再积极提供解决方案
   - neutral（平静）：保持专业、礼貌的正常回应
7. 服务意图识别：分析用户是否有使用特定服务的需求，可选服务类型包括：
   - ticket（购票）：涉及门票、票价、购票相关
   - activity（活动）：涉及演出、表演、活动安排相关
   - route（路线规划）：涉及游览路线规划相关
   - navigation（导航）：涉及前往某个地点、位置导航相关
   - guide（景点讲解）：涉及景点介绍、讲解、故事相关
   - nearby（附近景点）：涉及周边景点、附近设施相关
   - recommendation（个性化推荐）：涉及推荐、建议相关
   - profile（个人中心）：涉及用户个人信息、收藏、足迹相关
8. 在回答的最后，用JSON格式输出服务意图，格式为：<intent>{"service":"service_type","params":{"key":"value"}}</intent>
   - 如果识别到明确的服务需求，填写对应的service_type
   - 如果没有明确的服务需求，填写service为null
   - params为可选参数，可包含spot_id等信息
   - 服务意图JSON必须单独占一行，前后用<intent>和</intent>包裹
   - 例如：<intent>{"service":"navigation","params":{"spot":"灵山大佛"}}</intent>
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
        return await qwen_inference(request.text, request.user_id, knowledge, rag_results, request.emotion, request.emotion_reason, request.history)
    except Exception as e:
        print(f"[AI] ai_inference异常: {str(e)}")
        from app.services.knowledge_service import KnowledgeService
        ks = KnowledgeService()
        ks.sync_from_database(db)
        rag_results = ks.search(request.text, top_k=3)
        return await knowledge_fallback_inference(request.text, rag_results)

def parse_service_intent(content: str) -> dict:
    import re
    intent_match = re.search(r"<intent>(.*?)</intent>", content, re.S)
    if not intent_match:
        return {"service": None, "params": {}}
    
    try:
        intent_str = intent_match.group(1).strip()
        intent_data = json.loads(intent_str)
        service = intent_data.get("service")
        if service not in SERVICE_INTENT_MAP:
            service = None
        params = intent_data.get("params")
        if not isinstance(params, dict):
            params = {}
        return {
            "service": service,
            "params": params,
        }
    except Exception as e:
        print(f"[INTENT] 解析意图失败: {str(e)}")
        return {"service": None, "params": {}}

def extract_clean_text(content: str) -> str:
    import re
    cleaned = re.sub(r"<intent>.*?</intent>", "", content, flags=re.S)
    return cleaned.strip()

def summarize_rag_results(rag_results: list = None, limit: int = 3) -> list:
    if not rag_results:
        return []
    summary = []
    for item in rag_results[:limit]:
        content = item.get("content", "")
        title = ""
        for marker in ["知识点：", "景点名称："]:
            if marker in content:
                title = content.split(marker, 1)[1].split("\n", 1)[0].strip()
                break
        summary.append({
            "title": title or content[:30],
            "score": item.get("score", 0)
        })
    return summary

async def qwen_inference(text: str, user_id: str, knowledge: str = "", rag_results: list = None, emotion: str = "neutral", emotion_reason: str = "", history: list = None):
    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json"
    }
    print(f"[AI] Inference target: url={QWEN_API_URL}, model={QWEN_MODEL}, key={mask_secret(AI_API_KEY)}")

    emotion_prompt = f""
    if emotion and emotion != "neutral":
        emotion_desc = {
            "positive": "开心",
            "negative": "难过/焦虑",
            "surprised": "惊讶",
            "shy": "害羞",
            "angry": "生气"
        }.get(emotion, emotion)
        reason_part = f"，原因：{emotion_reason}" if emotion_reason else ""
        emotion_prompt = f"当前游客情绪：{emotion_desc}{reason_part}。请根据情绪调整回应方式。\n\n"

    if knowledge:
        user_prompt = f"{emotion_prompt}参考信息：\n{knowledge}\n\n问题：{text}"
    else:
        user_prompt = f"{emotion_prompt}知识库中未检索到相关信息，请根据你自身的知识回答：{text}"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    if history and isinstance(history, list):
        recent_history = history[-6:]
        for h in recent_history:
            if h.get("role") in ["user", "assistant"]:
                messages.append({
                    "role": h["role"],
                    "content": h.get("content", "")[:200]
                })

    messages.append({"role": "user", "content": user_prompt})

    payload = {
        "model": QWEN_MODEL,
        "messages": messages,
        "max_tokens": 512
    }

    print(f"[AI] 开始调用AI: {text[:50]}...")
    print(f"[AI] API URL: {QWEN_API_URL}")
    print(f"[AI] Knowledge: {knowledge[:100]}...")

    max_retries = 0 if agnes_circuit_is_open() else 1

    for attempt in range(max_retries):
        try:
            response = await ai_client.post(
                QWEN_API_URL,
                headers=headers,
                json=payload,
                timeout=httpx.Timeout(
                    connect=AGNES_STREAM_CONNECT_TIMEOUT,
                    read=AGNES_STREAM_READ_TIMEOUT,
                    write=AGNES_STREAM_READ_TIMEOUT,
                    pool=AGNES_STREAM_CONNECT_TIMEOUT,
                ),
            )
            print(f"[AI] AI状态码: {response.status_code}")
            response.raise_for_status()
            record_agnes_success()
            result = response.json()
            print(f"[AI] AI返回: {json.dumps(result)[:200]}...")
            content = result["choices"][0]["message"]["content"]
            
            intent = parse_service_intent(content)
            clean_text = extract_clean_text(content)
            
            return {
                "text": clean_text,
                "confidence": 0.9,
                "intent": intent,
                "debug": {
                    "source": "qwen_rag",
                    "knowledge_used": bool(knowledge.strip() if isinstance(knowledge, str) else knowledge),
                    "rag_hit_count": len(rag_results or []),
                    "rag_hits": summarize_rag_results(rag_results),
                }
            }
        except httpx.TimeoutException:
            print(f"[AI] AI超时(第{attempt+1}/{max_retries}次)")
        except httpx.HTTPStatusError as e:
            print(f"[AI] AI HTTP错误: {str(e)}")
            if response.status_code in [500, 502, 503, 504]:
                record_agnes_failure(f"HTTP {response.status_code}")
            break
        except Exception as e:
            print(f"[AI] AI调用失败: {str(e)}")
            break

    print(f"[AI] AI调用失败，使用知识库降级方案")
    fallback_result = await knowledge_fallback_inference(text, rag_results)
    return {
        **fallback_result,
        "intent": {"service": None, "params": {}},
        "debug": {
            **fallback_result.get("debug", {}),
            "source": "knowledge_fallback_after_ai_failure",
            "rag_hit_count": len(rag_results or []),
            "rag_hits": summarize_rag_results(rag_results),
        }
    }

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
            return {
                "text": v,
                "confidence": 0.8,
                "debug": {
                    "source": "local_keyword",
                    "matched_keyword": k
                }
            }
    
    default_response = "我是灵山胜境专属导游，只回答景区相关问题。您可以问我关于景点、路线、演出、门票等方面的问题。"
    print(f"[AI] 使用默认回复")
    return {
        "text": default_response,
        "confidence": 0.5,
        "debug": {
            "source": "local_default"
        }
    }

def clean_knowledge_fallback_text(content: str) -> str:
    """Strip retrieval metadata before exposing a knowledge result to users."""
    if not content:
        return ""

    raw = str(content).replace("\r\n", "\n").strip()
    lines = [line.strip() for line in raw.split("\n") if line.strip()]
    body_lines = []
    saw_content_marker = False
    metadata_keys = ("source:", "title:", "score:", "retrieval_mode:")

    for line in lines:
        lowered = line.lower()
        if lowered.startswith("content:"):
            saw_content_marker = True
            value = line.split(":", 1)[1].strip()
            if value:
                body_lines.append(value)
            continue
        if saw_content_marker:
            if lowered.startswith(metadata_keys):
                continue
            body_lines.append(line)
            continue
        if lowered.startswith(metadata_keys):
            continue
        body_lines.append(line)

    cleaned = "\n".join(body_lines).strip()
    return cleaned or raw

def is_reliable_fallback_result(result: dict) -> bool:
    if not isinstance(result, dict):
        return False
    confidence = result.get("confidence")
    if confidence is not None:
        try:
            return float(confidence) >= 0.45
        except (TypeError, ValueError):
            return False
    try:
        # Semantic scores close to zero are not useful enough to answer directly.
        return float(result.get("score", 0)) >= 0.15
    except (TypeError, ValueError):
        return False

async def knowledge_fallback_inference(text: str, rag_results: list = None):
    if rag_results and len(rag_results) > 0:
        best_result = rag_results[0]
        content = best_result.get("content", "")
        score = best_result.get("score", 0)
        
        print(f"[AI] 使用知识库降级方案，匹配分数: {score}")
        
        if is_reliable_fallback_result(best_result) and len(content) > 20:
            lines = content.split("\n")
            answer_lines = []
            for line in lines:
                if any(kw in line for kw in ["介绍", "内容", "亮点", "开放", "位置", "内涵"]):
                    clean_line = re.sub(r'^[^\u4e00-\u9fff]+', '', line).strip()
                    if clean_line:
                        answer_lines.append(clean_line)
            
            if answer_lines:
                knowledge_answer = "。".join(answer_lines)
                print(f"[AI] 知识库生成回答: {knowledge_answer[:50]}...")
                return {
                    "text": knowledge_answer,
                    "confidence": 0.7,
                    "debug": {
                        "source": "knowledge_fallback",
                        "best_score": score,
                        "rag_hit_count": len(rag_results or []),
                        "rag_hits": summarize_rag_results(rag_results)
                    }
                }
            
            cleaned_content = clean_knowledge_fallback_text(content)
            print(f"[AI] 知识库内容直接回答: {cleaned_content[:50]}...")
            return {
                "text": cleaned_content,
                "confidence": 0.6,
                "debug": {
                    "source": "knowledge_fallback",
                    "best_score": score,
                    "rag_hit_count": len(rag_results or []),
                    "rag_hits": summarize_rag_results(rag_results)
                }
            }
    
    print(f"[AI] 知识库无匹配，使用关键词降级方案")
    if (text or "").strip() not in {"你好", "您好", "嗨", "谢谢", "感谢"}:
        return {
            "text": "抱歉，我暂时没有检索到足够可靠的信息，请换一种问法，或查看景区服务页面。",
            "confidence": 0.0,
            "debug": {
                "source": "knowledge_fallback_unreliable",
                "rag_hit_count": len(rag_results or []),
                "rag_hits": summarize_rag_results(rag_results),
            },
        }

    fallback = await local_fallback_inference(text)
    return {
        **fallback,
        "debug": {
            **fallback.get("debug", {}),
            "source": "knowledge_fallback_to_local",
            "rag_hit_count": len(rag_results or []),
            "rag_hits": summarize_rag_results(rag_results)
        }
    }

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

def wrap_pcm16_to_wav(pcm_bytes: bytes, sample_rate: int = 16000, channels: int = 1) -> bytes:
    bits_per_sample = 16
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8
    data_size = len(pcm_bytes)
    return b"".join([
        b"RIFF",
        struct.pack("<I", 36 + data_size),
        b"WAVE",
        b"fmt ",
        struct.pack("<IHHIIHH", 16, 1, channels, sample_rate, byte_rate, block_align, bits_per_sample),
        b"data",
        struct.pack("<I", data_size),
        pcm_bytes,
    ])

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
        if not speech_text:
            return await local_fallback_tts(request.text)

        if TTS_APP_ID and TTS_API_KEY and TTS_API_SECRET:
            try:
                return await xunfei_tts(speech_text, request.voice)
            except Exception as e:
                print(f"[TTS] 讯飞合成失败，降级到本地方案: {str(e)}")
                return await local_fallback_tts(speech_text)
        else:
            return await local_fallback_tts(speech_text)
    except Exception as e:
        print(f"[TTS] 接口异常，降级到本地方案: {str(e)}")
        return await local_fallback_tts(request.text)

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
                    "aue": "raw",
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
                data = res.get("data", {}) or {}
                audio = data.get("audio")
                if audio:
                    try:
                        audio_data += base64.b64decode(audio)
                    except Exception as decode_error:
                        raise Exception(f'讯飞TTS音频解码失败: {decode_error}')
                if data.get("status") == 2:
                    break

        if not audio_data:
            raise Exception("讯飞TTS返回空音频")

        wav_data = wrap_pcm16_to_wav(audio_data, sample_rate=16000, channels=1)
        audio_data_uri = f"data:audio/wav;base64,{base64.b64encode(wav_data).decode()}"
        source_hash = hashlib.sha256(f"chat|{voice}|{text}|{len(wav_data)}".encode("utf-8")).hexdigest()
        audio_url, audio_path = save_audio_file(0, "chat", voice, source_hash, audio_data_uri)
        result = {
            "audio_data": "",
            "audio_url": audio_url or "",
            "audio_path": audio_path or "",
            "audio_format": "wav",
            "sample_rate": 16000,
            "duration": len(audio_data) / 2 / 16000,
            "speech_text": text
        }
        if not audio_url:
            result["audio_data"] = audio_data_uri
        return result
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
    speech_text = clean_tts_text(text)
    return {
        "audio_data": "",
        "duration": max(0.3, len(speech_text) * 0.18),
        "speech_text": speech_text,
        "note": "TTS已降级"
    }

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

# ======================
# 流式推理
# ======================
async def qwen_stream_inference(text: str, user_id: str, knowledge: str = "", rag_results: list = None, emotion: str = "neutral", emotion_reason: str = "", history: list = None) -> AsyncGenerator[str, None]:
    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json"
    }

    emotion_prompt = f""
    if emotion and emotion != "neutral":
        emotion_desc = {
            "positive": "开心",
            "negative": "难过/焦虑",
            "surprised": "惊讶",
            "shy": "害羞",
            "angry": "生气"
        }.get(emotion, emotion)
        reason_part = f"，原因：{emotion_reason}" if emotion_reason else ""
        emotion_prompt = f"当前游客情绪：{emotion_desc}{reason_part}。请根据情绪调整回应方式。\n\n"

    if knowledge:
        user_prompt = f"{emotion_prompt}参考信息：\n{knowledge}\n\n问题：{text}"
    else:
        user_prompt = f"{emotion_prompt}知识库中未检索到相关信息，请根据你自身的知识回答：{text}"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    if history and isinstance(history, list):
        recent_history = history[-6:]
        for h in recent_history:
            if h.get("role") in ["user", "assistant"]:
                messages.append({
                    "role": h["role"],
                    "content": h.get("content", "")[:200]
                })

    messages.append({"role": "user", "content": user_prompt})

    payload = {
        "model": QWEN_MODEL,
        "messages": messages,
        "max_tokens": 512,
        "stream": True
    }

    print(f"[AI] 开始流式调用Agnes AI: {text[:50]}...")

    max_retries = 0 if agnes_circuit_is_open() else 1
    if max_retries == 0:
        print("[AI] circuit is open; skipping remote stream call")
    stream_timeout = httpx.Timeout(
        connect=AGNES_STREAM_CONNECT_TIMEOUT,
        read=AGNES_STREAM_READ_TIMEOUT,
        write=AGNES_STREAM_READ_TIMEOUT,
        pool=AGNES_STREAM_CONNECT_TIMEOUT,
    )
    partial_content = ""
    request_started_at = time.perf_counter()
    first_token_logged = False

    for attempt in range(max_retries):
        try:
            async with ai_client.stream(
                "POST",
                QWEN_API_URL,
                headers=headers,
                json=payload,
                timeout=stream_timeout,
            ) as response:
                print(f"[AI] AI流式状态码: {response.status_code}")
                response.raise_for_status()

                full_content = ""
                buffer = ""
                stream_done = False
                intent_filter = IntentStreamFilter()
                async for chunk in response.aiter_text():
                    if stream_done:
                        break

                    buffer += chunk

                    while True:
                        line_end = buffer.find("\n")
                        if line_end == -1:
                            break

                        line = buffer[:line_end].strip()
                        buffer = buffer[line_end + 1:]

                        if not line:
                            continue

                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                buffer = ""
                                stream_done = True
                                break
                            try:
                                data = json.loads(data_str)

                                choices = data.get("choices")
                                if not choices or not isinstance(choices, list) or len(choices) == 0:
                                    finish_reason = data.get("finish_reason")
                                    if finish_reason:
                                        print(f"[AI] 流式响应结束标记: finish_reason={finish_reason}")
                                        continue
                                    print(f"[AI] 流式响应无choices: {json.dumps(data)[:100]}")
                                    continue

                                first_choice = choices[0]
                                if not isinstance(first_choice, dict):
                                    print(f"[AI] 流式响应choice格式异常: {type(first_choice)}")
                                    continue

                                delta = first_choice.get("delta")
                                if delta is None:
                                    finish_reason = first_choice.get("finish_reason")
                                    if finish_reason:
                                        print(f"[AI] 流式响应单个结束标记: finish_reason={finish_reason}")
                                        continue
                                    print(f"[AI] 流式响应无delta: {json.dumps(first_choice)[:100]}")
                                    continue

                                content = delta.get("content", "")
                                if content:
                                    if not first_token_logged:
                                        first_token_logged = True
                                        print(
                                            f"[AI] first-token latency: "
                                            f"{time.perf_counter() - request_started_at:.2f}s"
                                        )
                                    full_content += content
                                    partial_content = full_content
                                    clean_content = intent_filter.feed(content)
                                    if clean_content:
                                        yield clean_content
                            except json.JSONDecodeError as e:
                                print(f"[AI] 流式响应JSON解析失败: {data_str[:150]} - {str(e)}")
                                continue
                            except Exception as e:
                                print(f"[AI] 流式响应处理异常: {str(e)} - {data_str[:100]}")
                                continue

                trailing_content = intent_filter.finish()
                if trailing_content:
                    yield trailing_content

                if full_content:
                    record_agnes_success()
                    meta_data = {
                        'intent': parse_service_intent(full_content),
                        'debug': {
                            'source': 'qwen_rag_stream',
                            'knowledge_used': bool(knowledge.strip() if isinstance(knowledge, str) else knowledge),
                            'rag_hit_count': len(rag_results or []),
                            'rag_hits': summarize_rag_results(rag_results),
                        }
                    }
                    yield f"__STREAM_META__{json.dumps(meta_data)}__STREAM_META__"
                    return

            print(f"[AI] AI流式调用失败，尝试降级方案")
        except httpx.TimeoutException:
            print(f"[AI] AI流式超时(第{attempt+1}/{max_retries}次)")
            record_agnes_failure("stream timeout")
            if partial_content:
                yield f"__STREAM_META__{json.dumps({'intent': {'service': None, 'params': {}}, 'debug': {'source': 'qwen_partial_timeout'}})}__STREAM_META__"
                return
        except httpx.HTTPStatusError as e:
            print(f"[AI] AI流式HTTP错误: {str(e)}")
            if e.response.status_code in [500, 502, 503, 504]:
                record_agnes_failure(f"HTTP {e.response.status_code}")
            break
        except Exception as e:
            print(f"[AI] AI流式调用失败: {str(e)}")
            break

    print(f"[AI] AI流式调用失败，使用降级方案")
    fallback_result = await knowledge_fallback_inference(text, rag_results)
    yield fallback_result["text"]
    meta_data = {
        'intent': {'service': None, 'params': {}},
        'debug': {
            **fallback_result.get('debug', {}),
            'source': 'knowledge_fallback_stream',
        }
    }
    yield f"__STREAM_META__{json.dumps(meta_data)}__STREAM_META__"

async def ai_stream_inference(request: AIRequest, db: Session = Depends(get_db)) -> AsyncGenerator[str, None]:
    text = request.text.strip()

    from app.services.knowledge_service import KnowledgeService
    ks = KnowledgeService()
    ks.sync_from_database(db)

    rag_results = ks.search(text, top_k=3)

    knowledge = ""
    if rag_results:
        knowledge = "\n\n".join([f"【来源{idx+1}】\n{r['content']}" for idx, r in enumerate(rag_results)])

    async for chunk in qwen_stream_inference(
        text=text,
        user_id=request.user_id,
        knowledge=knowledge,
        rag_results=rag_results,
        emotion=request.emotion,
        emotion_reason=request.emotion_reason,
        history=request.history
    ):
        yield chunk

@router.post("/stream-inference")
async def stream_inference(request: AIRequest, db: Session = Depends(get_db)):
    async def generate():
        async for chunk in ai_stream_inference(request, db):
            yield f"data: {json.dumps({'content': chunk})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*"
        }
    )
