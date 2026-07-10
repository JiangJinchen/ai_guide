from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Spot, VisitorInteraction, VisitorBehavior, RouteHistory, RouteDistanceCache, SpotVisitMeta, SpotTag, AppUserBehavior
from app.schemas import SpotResponse, VisitorInteractionResponse
from typing import List, Optional
import os
import httpx
import re
import uuid
import json
import math
import itertools
import logging
from dotenv import load_dotenv
load_dotenv(override=True)

logger = logging.getLogger(__name__)

http_client = httpx.AsyncClient(timeout=10)

import time
from collections import deque

AMAP_API_CALLS = deque()
AMAP_QPS_LIMIT = 5
AMAP_TIME_WINDOW = 1

def amap_rate_limited(func):
    def wrapper(*args, **kwargs):
        now = time.time()
        while AMAP_API_CALLS and AMAP_API_CALLS[0] < now - AMAP_TIME_WINDOW:
            AMAP_API_CALLS.popleft()
        if len(AMAP_API_CALLS) >= AMAP_QPS_LIMIT:
            wait_time = AMAP_TIME_WINDOW - (now - AMAP_API_CALLS[0])
            if wait_time > 0:
                time.sleep(wait_time)
                now = time.time()
                while AMAP_API_CALLS and AMAP_API_CALLS[0] < now - AMAP_TIME_WINDOW:
                    AMAP_API_CALLS.popleft()
        AMAP_API_CALLS.append(time.time())
        return func(*args, **kwargs)
    return wrapper

router = APIRouter()

class MessageRequest(BaseModel):
    text: str
    user_id: str

class MessageResponse(BaseModel):
    text: str
    speech_text: str = ""
    reply_id: str = ""
    emotion: str = "neutral"
    emotion_source: str = ""
    emotion_reason: str = ""
    digital_human_action: str = "speak"
    digital_human_expression: str = "Normal"
    digital_human_motion: str = "Idle"

# ======================
# 百度AI密钥（用于情感倾向分析）
# ======================
EMOTION_API_ID = os.getenv("EMOTION_API_ID", "")
EMOTION_API_KEY = os.getenv("EMOTION_API_KEY", "")
EMOTION_SECRET_KEY = os.getenv("EMOTION_SECRET_KEY", "")
AI_API_KEY = os.getenv("AI_API_KEY", "")
QWEN_API_URL = "https://apihub.agnes-ai.com/v1/chat/completions"
QWEN_MODEL = "agnes-2.0-flash"
AMAP_WEB_KEY = os.getenv("AMAP_WEB_KEY", "")
AMAP_DISTANCE_URL = "https://restapi.amap.com/v3/distance"
AMAP_WALKING_URL = "https://restapi.amap.com/v3/direction/walking"
AMAP_GEOCODE_URL = "https://restapi.amap.com/v3/geocode/geo"

EMOTION_EXPRESSION_MAP = {
    "negative": "Sad",
    "positive": "Smile",
    "neutral": "Normal",
    "surprised": "Surprised",
    "shy": "Blushing",
    "angry": "Angry"
}

STATUS_MOTION_MAP = {
    "idle": "Idle",
    "listen": "FlickUp",
    "think": "Flick",
    "speak": "Tap"
}

def resolve_digital_human_expression(emotion: str) -> str:
    return EMOTION_EXPRESSION_MAP.get(emotion or "neutral", "Normal")

async def get_access_token():
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": EMOTION_API_KEY,
        "client_secret": EMOTION_SECRET_KEY
    }
    response = await http_client.post(url, params=params)
    return response.json().get("access_token")

def normalize_reply_text(text: str, max_chars: int = 260) -> str:
    """把大模型回复整理成数字人口播友好的纯文本。"""
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

# ==============================
# 1. 景点列表
# ==============================
@router.get("/spots", response_model=List[SpotResponse])
def get_spots(db: Session = Depends(get_db)):
    return db.query(Spot).all()

# ==============================
# 2. 景点详情
# ==============================
@router.get("/spots/{spot_id}", response_model=SpotResponse)
def get_spot_detail(spot_id: int, db: Session = Depends(get_db)):
    spot = db.query(Spot).filter(Spot.id == spot_id).first()
    if not spot:
        raise HTTPException(status_code=404, detail="景点不存在")
    return spot

# ==============================
# 3. 景点讲解
# ==============================
@router.get("/guide/{spot_id}")
def get_spot_guide(spot_id: int, db: Session = Depends(get_db)):
    spot = db.query(Spot).filter(Spot.id == spot_id).first()
    if not spot:
        raise HTTPException(status_code=404, detail="景点不存在")
    return {
        "spot_id": spot_id,
        "scenic_area": spot.scenic_area_name,
        "name": spot.spot_name,
        "content": spot.description,
        "culture": spot.culture_connotation,
        "highlights": spot.highlights,
        "open_info": spot.open_info
    }

# ==============================
# 4. AI 对话
# ==============================
@router.post("/chat", response_model=MessageResponse)
async def chat(request: MessageRequest, db: Session = Depends(get_db)):
    emotion_result = await analyze_emotion(text=request.text)
    user_emotion = emotion_result.get("emotion", "neutral")
    
    interaction = VisitorInteraction(
        visitor_id=request.user_id,
        interaction_type="chat",
        content=request.text,
        emotion=user_emotion
    )
    db.add(interaction)
    db.commit()

    from app.api.ai import ai_inference, AIRequest
    ai_result = await ai_inference(
        AIRequest(text=request.text, user_id=request.user_id),
        db
    )

    ai_text = ai_result["text"]
    if ai_text == "服务暂时不可用":
        from app.api.ai import local_fallback_inference
        fallback_result = await local_fallback_inference(request.text)
        ai_text = fallback_result["text"]
    if user_emotion == "negative":
        ai_text = f"感受到你有些不开心，我来帮你解决问题。{ai_text}"
    elif user_emotion == "positive":
        ai_text = f"听起来你心情不错。{ai_text}"

    speech_text = normalize_reply_text(ai_text)
    ai_text = speech_text
    reply_id = uuid.uuid4().hex

    return MessageResponse(
        text=ai_text,
        speech_text=speech_text,
        reply_id=reply_id,
        emotion=user_emotion,
        emotion_source=emotion_result.get("source", ""),
        emotion_reason=emotion_result.get("reason", emotion_result.get("note", "")),
        digital_human_action="speak",
        digital_human_expression=resolve_digital_human_expression(user_emotion),
        digital_human_motion=STATUS_MOTION_MAP["speak"]
    )

# ==============================
# 5. 对话历史接口
# ==============================
@router.get("/chat/history", response_model=List[VisitorInteractionResponse])
def get_chat_history(user_id: str, db: Session = Depends(get_db)):
    """获取用户和AI的对话历史"""
    history = db.query(VisitorInteraction)\
        .filter(VisitorInteraction.visitor_id == user_id)\
        .filter(VisitorInteraction.interaction_type == "chat")\
        .order_by(VisitorInteraction.created_at.desc())\
        .all()
    return history

# ==============================
# 6. 反馈评分接口
# ==============================
class FeedbackRequest(BaseModel):
    user_id: str
    chat_content: str
    satisfaction_score: float
    comment: Optional[str] = None

@router.post("/feedback")
def submit_feedback(request: FeedbackRequest, db: Session = Depends(get_db)):
    """用户提交对AI回答的评分和反馈"""
    feedback = VisitorInteraction(
        visitor_id=request.user_id,
        interaction_type="feedback",
        content=request.chat_content,
        satisfaction_score=request.satisfaction_score,
        emotion="satisfied" if request.satisfaction_score >= 4 else "dissatisfied"
    )
    db.add(feedback)
    db.commit()
    return {"status": "ok", "message": "反馈提交成功"}

# ==============================
# 6.5 APP行为记录接口
# ==============================
class AppBehaviorRequest(BaseModel):
    user_id: Optional[str] = None
    behavior_type: str
    spot_id: Optional[int] = None
    spot_name: Optional[str] = None
    keyword: Optional[str] = None
    duration: Optional[int] = None

@router.post("/behavior")
def record_behavior(request: AppBehaviorRequest, db: Session = Depends(get_db), request_obj: Request = None):
    """记录APP内用户行为（搜索、查看、收藏、分享等）"""
    visitor_id = request_obj.headers.get('X-User-Id', request.user_id) if request_obj else request.user_id
    visitor_id = visitor_id or 'guest'
    
    behavior = AppUserBehavior(
        visitor_id=visitor_id,
        behavior_type=request.behavior_type,
        spot_id=request.spot_id,
        spot_name=request.spot_name,
        keyword=request.keyword,
        duration=request.duration
    )
    db.add(behavior)
    db.commit()
    db.refresh(behavior)
    return {"status": "ok", "message": "行为记录成功", "id": behavior.id}


@router.post("/behavior/{behavior_id}/duration")
def update_behavior_duration(behavior_id: int, duration: int, db: Session = Depends(get_db)):
    """更新行为停留时长"""
    behavior = db.query(AppUserBehavior).filter(AppUserBehavior.id == behavior_id).first()
    if behavior:
        behavior.duration = duration
        db.commit()
        return {"status": "ok", "message": "时长更新成功"}
    return {"status": "error", "message": "行为记录不存在"}


@router.get("/behaviors")
def get_user_behaviors(user_id: str = "guest", db: Session = Depends(get_db)):
    behaviors = db.query(AppUserBehavior).filter(
        AppUserBehavior.visitor_id == user_id
    ).order_by(AppUserBehavior.created_at.desc()).limit(20).all()
    return {
        "status": "ok",
        "user_id": user_id,
        "count": len(behaviors),
        "behaviors": [
            {
                "id": b.id,
                "behavior_type": b.behavior_type,
                "spot_id": b.spot_id,
                "spot_name": b.spot_name,
                "keyword": b.keyword,
                "duration": b.duration,
                "created_at": b.created_at.isoformat()
            } for b in behaviors
        ]
    }


# ==============================
# 7. 景点推荐接口
# ==============================
# 现有的推荐算法：关键词匹配+标签计数（只能字面匹配，无语义）
# 1.定义标签体系（从knowledge表和spot表中使用聚类算法提取每个类别对应的关键词，然后人工总结形成类标签）
# 2.提前计算所有景点的标签，存入缓存，后续推荐时直接从缓存中读取
# 3.从用户与AI的对话历史中提取用户偏好标签，统计每个标签的出现次数
# 4.根据用户最高分标签，推荐用户可能感兴趣的景点
# 有待改进成基于内容的推荐算法：
# 1.使用TF-IDF向量化用户对话历史和景点描述
# 2.计算用户对话历史与景点描述的余弦相似度
# 3.根据相似度排序，推荐用户可能感兴趣的景点
# 标签体系
TAG_KEYWORDS = {
    "zen_culture": ["灵山", "胜境", "禅意", "佛教文化", "精舍", "游览"],
    "buddha_history": ["佛像", "佛法", "供奉", "唐卡", "塔身", "历史", "传承", "五方", "阿育王"],
    "architecture_art": ["梵宫", "建筑", "木雕", "琉璃", "穹顶", "艺术", "工艺", "科技"],
    "buddha_performance": ["九龙", "灌浴", "莲花", "佛陀", "表演", "诞生"],
    "lake_scenery": ["太湖"],
    "parent_child": ["亲子", "互动", "佛足", "佛光"],
    "ancient_temple": ["祥符", "禅寺", "千年"],
    "leisure_service": ["休憩", "商铺", "品鉴", "免费"]
}

TAG_LABELS = {
    "zen_culture": "禅意文化",
    "buddha_history": "佛教历史",
    "architecture_art": "建筑艺术",
    "buddha_performance": "佛教演艺",
    "lake_scenery": "太湖风光",
    "parent_child": "亲子互动",
    "ancient_temple": "古寺禅修",
    "leisure_service": "休憩服务"
}

ROUTE_TO_RECOMMENDATION_TAGS = {
    "history": ["buddha_history", "zen_culture", "ancient_temple"],
    "scenery": ["lake_scenery"],
    "family": ["parent_child", "leisure_service", "buddha_performance"],
    "architecture": ["architecture_art"],
    "blessing": ["zen_culture", "buddha_history", "ancient_temple"]
}

SPOT_TAG_ALIASES = {
    "history": ["buddha_history", "zen_culture"],
    "scenery": ["lake_scenery"],
    "family": ["parent_child", "leisure_service"],
    "architecture": ["architecture_art"],
    "blessing": ["zen_culture", "buddha_history"]
}

# ==========================
# 缓存机制
# ==========================
spot_tag_cache = {}
spot_name_map_cache = {}
spot_name_map_cache_time = 0
popular_tag_cache = {}
popular_tag_cache_time = 0
spot_popularity_cache = {}
spot_popularity_cache_time = 0
CACHE_EXPIRE_SECONDS = 30

def precompute_all_spot_tags(db: Session):
    global spot_tag_cache
    if spot_tag_cache:
        return

    tag_records = db.query(SpotTag).all()
    for record in tag_records:
        if record.spot_id not in spot_tag_cache:
            spot_tag_cache[record.spot_id] = {}
        for tag in SPOT_TAG_ALIASES.get(record.tag, [record.tag]):
            if tag not in TAG_KEYWORDS:
                continue
            spot_tag_cache[record.spot_id][tag] = max(
                spot_tag_cache[record.spot_id].get(tag, 0),
                record.score or 10
            )

def get_spot_tag_scores(spot_id):
    tags = spot_tag_cache.get(spot_id, {})
    raw_scores = tags if isinstance(tags, dict) else {tag: 10 for tag in tags}
    normalized = {}
    for raw_tag, score in raw_scores.items():
        for tag in SPOT_TAG_ALIASES.get(raw_tag, [raw_tag]):
            if tag not in TAG_KEYWORDS:
                continue
            normalized[tag] = max(normalized.get(tag, 0), score or 10)
    return normalized

def normalize_score_map(scores):
    if not scores:
        return {}
    max_score = max(scores.values()) if scores else 0
    if max_score <= 0:
        return {}
    return {key: round(value / max_score, 4) for key, value in scores.items() if value > 0}

def spot_text(spot):
    return " ".join([
        str(route_spot_value(spot, "spot_name", "") or route_spot_name(spot) or ""),
        str(route_spot_value(spot, "description", "") or ""),
        str(route_spot_value(spot, "culture_connotation", "") or ""),
        str(route_spot_value(spot, "highlights", "") or ""),
        str(route_spot_value(spot, "location", "") or "")
    ])

def build_spot_name_map(db: Session):
    global spot_name_map_cache, spot_name_map_cache_time
    import time
    now = time.time()
    if spot_name_map_cache and (now - spot_name_map_cache_time) < CACHE_EXPIRE_SECONDS:
        return spot_name_map_cache
    
    spot_name_map_cache = {
        spot.spot_name: spot
        for spot in db.query(Spot).all()
        if spot.spot_name
    }
    spot_name_map_cache_time = now
    return spot_name_map_cache

def add_keyword_profile_score(profile, text, weight=1.0):
    if not text:
        return
    for tag, keywords in TAG_KEYWORDS.items():
        for keyword in keywords:
            count = str(text).count(keyword)
            if count:
                profile[tag] += count * weight

def add_spot_tag_profile_score(profile, spot, weight=1.0):
    if not spot:
        return
    for tag, tag_score in get_spot_tag_scores(spot.id).items():
        if tag not in profile:
            continue
        profile[tag] += (tag_score or 10) / 10 * weight

def build_user_tag_profile(db: Session, user_id: str):
    precompute_all_spot_tags(db)
    profile = {tag: 0.0 for tag in TAG_KEYWORDS}
    spot_by_name = build_spot_name_map(db)

    chat_history = db.query(VisitorInteraction)\
        .filter(VisitorInteraction.visitor_id == user_id)\
        .filter(VisitorInteraction.interaction_type == "chat")\
        .all()
    for chat in chat_history:
        add_keyword_profile_score(profile, chat.content or "", 1.0)

    app_behaviors = db.query(AppUserBehavior)\
        .filter(AppUserBehavior.visitor_id == user_id)\
        .order_by(AppUserBehavior.created_at.desc())\
        .limit(100)\
        .all()
    for behavior in app_behaviors:
        behavior_weight = 1.0
        if behavior.behavior_type == 'view':
            behavior_weight += min((behavior.duration or 0) / 30, 3)
        elif behavior.behavior_type == 'favorite':
            behavior_weight += 5.0
        elif behavior.behavior_type == 'share':
            behavior_weight += 3.0
        elif behavior.behavior_type == 'search':
            behavior_weight += 0.5

        spot = spot_by_name.get(behavior.spot_name)
        if spot:
            add_spot_tag_profile_score(profile, spot, behavior_weight)
        if behavior.keyword:
            add_keyword_profile_score(profile, behavior.keyword, behavior_weight * 0.5)

    route_records = db.query(RouteHistory)\
        .filter(RouteHistory.visitor_id == (user_id or "guest"))\
        .order_by(RouteHistory.created_at.desc())\
        .limit(10)\
        .all()
    for record in route_records:
        try:
            route_data = json.loads(record.route_data or "{}")
        except json.JSONDecodeError:
            continue
        for spot_item in route_data.get("route", []):
            spot = spot_by_name.get(spot_item.get("name") or spot_item.get("spot_name"))
            if spot:
                add_spot_tag_profile_score(profile, spot, 0.8)
            add_keyword_profile_score(profile, spot_item.get("description", ""), 0.3)

    if any(profile.values()):
        return profile

    cold_profile = get_app_popular_tags(db)
    if any(cold_profile.values()):
        return cold_profile
    return {"zen_culture": 1.0, **{tag: 0.0 for tag in TAG_KEYWORDS if tag != "zen_culture"}}

def get_popular_tag_scores(db: Session):
    global popular_tag_cache, popular_tag_cache_time
    import time
    now = time.time()
    if popular_tag_cache and (now - popular_tag_cache_time) < CACHE_EXPIRE_SECONDS:
        return popular_tag_cache

    precompute_all_spot_tags(db)
    tag_score = {tag: 0.0 for tag in TAG_KEYWORDS}
    spot_by_name = build_spot_name_map(db)
    
    from datetime import datetime, timedelta
    recent_date = datetime.now() - timedelta(days=30)
    behaviors = db.query(VisitorBehavior)\
        .filter(VisitorBehavior.visit_date >= recent_date)\
        .limit(1000)\
        .all()

    for behavior in behaviors:
        total = (
            (behavior.stay_duration or 0) * 1.0
            + (behavior.satisfaction or 0) * 10.0
            + (behavior.total_cost or 0) * 0.1
        )
        if total <= 0:
            total = 1
        spot = spot_by_name.get(behavior.attraction_name)
        if spot:
            for tag, tag_weight in get_spot_tag_scores(spot.id).items():
                tag_score[tag] += total * ((tag_weight or 10) / 10)
        add_keyword_profile_score(
            tag_score,
            " ".join([
                str(behavior.attraction_name or ""),
                str(behavior.attraction_type or ""),
                str(behavior.attraction_content or "")
            ]),
            total * 0.05
        )

    popular_tag_cache = tag_score
    popular_tag_cache_time = now
    return tag_score

def get_app_popular_tags(db: Session):
    tag_score = {tag: 0.0 for tag in TAG_KEYWORDS}
    spot_by_name = build_spot_name_map(db)
    
    app_behaviors = db.query(AppUserBehavior)\
        .order_by(AppUserBehavior.created_at.desc())\
        .limit(1000)\
        .all()
    
    for behavior in app_behaviors:
        weight = 1.0
        if behavior.behavior_type == 'view':
            weight += min((behavior.duration or 0) / 30, 3)
        elif behavior.behavior_type == 'favorite':
            weight += 5.0
        elif behavior.behavior_type == 'share':
            weight += 3.0
        
        spot = spot_by_name.get(behavior.spot_name)
        if spot:
            for tag, tag_weight in get_spot_tag_scores(spot.id).items():
                tag_score[tag] += weight * ((tag_weight or 10) / 10)
        
        if behavior.keyword:
            add_keyword_profile_score(tag_score, behavior.keyword, weight * 0.5)
    
    return tag_score

def get_spot_popularity_scores(db: Session):
    global spot_popularity_cache, spot_popularity_cache_time
    import time
    now = time.time()
    if spot_popularity_cache and (now - spot_popularity_cache_time) < CACHE_EXPIRE_SECONDS:
        return spot_popularity_cache

    spot_scores = {spot.spot_name: 0.0 for spot in db.query(Spot).all()}
    
    app_behaviors = db.query(AppUserBehavior)\
        .order_by(AppUserBehavior.created_at.desc())\
        .limit(1000)\
        .all()
    for behavior in app_behaviors:
        if behavior.spot_name not in spot_scores:
            continue
        weight = 1.0
        if behavior.behavior_type == 'view':
            weight += min((behavior.duration or 0) / 30, 3)
        elif behavior.behavior_type == 'favorite':
            weight += 4.0
        elif behavior.behavior_type == 'share':
            weight += 3.0
        elif behavior.behavior_type == 'navigate':
            weight += 5.0
        spot_scores[behavior.spot_name] += weight * 10
    
    result = normalize_score_map(spot_scores)
    spot_popularity_cache = result
    spot_popularity_cache_time = now
    return result

def score_spot_for_recommendation(spot, normalized_profile, popularity_scores):
    tags = get_spot_tag_scores(spot.id)
    tag_score = 0.0
    matched_tags = []
    tag_contributions = []
    
    for tag, user_weight in normalized_profile.items():
        if user_weight <= 0:
            continue
        if tag in tags:
            spot_tag_score = tags[tag] or 10
            contribution = user_weight * (spot_tag_score / 10) * 60
            tag_score += contribution
            matched_tags.append(tag)
            tag_contributions.append({
                'tag': tag,
                'user_weight': user_weight,
                'spot_tag_score': spot_tag_score,
                'contribution': contribution
            })

    content_score = 0.0
    matched_keywords = []
    text = spot_text(spot)
    for tag, user_weight in normalized_profile.items():
        if user_weight <= 0:
            continue
        for keyword in TAG_KEYWORDS[tag]:
            if keyword in text:
                content_score += user_weight * 4
                if keyword not in matched_keywords:
                    matched_keywords.append(keyword)

    popularity_score = popularity_scores.get(spot.spot_name, 0) * 15
    order_score = max(0, 24 - SPOT_ORDER_WEIGHT.get(spot.spot_name, 20)) * 0.25
    total = tag_score + content_score + popularity_score + order_score
    
    breakdown = {
        'tag_score': tag_score,
        'content_score': content_score,
        'popularity_score': popularity_score,
        'order_score': order_score,
        'total': total,
        'tag_contributions': tag_contributions,
        'matched_keywords': matched_keywords,
        'matched_tags': matched_tags
    }
    
    return total, matched_tags, breakdown

TAG_REASON_TEMPLATES = {
    "zen_culture": [
        "您对禅意文化的探索令人赞赏，这里是静心冥想的绝佳场所",
        "禅意文化爱好者必访！在这里感受宁静与智慧的交融",
        "延续您对禅意文化的探索之旅，体验东方哲学的深邃内涵",
        "禅意氛围浓厚，适合在喧嚣中寻找内心的宁静",
        "结合您对禅意文化的兴趣，这里的建筑与意境完美契合"
    ],
    "buddha_history": [
        "佛教历史爱好者的必选之地，感受千年传承的智慧之光",
        "您对佛教历史的探索值得深入，这里珍藏着珍贵的文化遗产",
        "延续您对佛教历史的追寻，了解灵山胜境的深厚底蕴",
        "佛教文化的重要遗址，每一处都诉说着千年故事",
        "结合您对佛教历史的兴趣，这里的历史价值无可比拟"
    ],
    "architecture_art": [
        "建筑艺术的巅峰之作，每一处细节都令人叹为观止",
        "您对建筑艺术的鉴赏力令人钦佩，这里将带给您视觉盛宴",
        "建筑艺术爱好者的天堂，融合了传统与现代的美学精髓",
        "精美的建筑工艺，展现了人类智慧与艺术的完美结合",
        "结合您对建筑艺术的兴趣，这里的设计堪称匠心独运"
    ],
    "buddha_performance": [
        "精彩的佛教演艺不容错过，感受视听双重震撼",
        "您对佛教文化的兴趣值得体验这场精彩演出",
        "沉浸式佛教表演，让您身临其境地感受信仰的力量",
        "独特的演艺形式，将佛教故事生动呈现在您面前",
        "结合您对佛教文化的兴趣，这场演出将给您留下深刻印象"
    ],
    "lake_scenery": [
        "太湖风光美不胜收，湖光山色令人心旷神怡",
        "您对自然风光的热爱，在这里可以得到完美满足",
        "湖景与佛文化的完美融合，展现独特的山水意境",
        "漫步湖边，感受清风拂面的惬意时光",
        "结合您对自然风光的兴趣，这里的湖景堪称一绝"
    ],
    "parent_child": [
        "亲子互动的理想选择，让孩子在游玩中感受文化魅力",
        "您和家人的探索之旅，这里充满了欢乐与惊喜",
        "适合家庭出游的温馨景点，留下美好回忆",
        "亲子同乐的好去处，寓教于乐的完美体验",
        "结合您对亲子互动的需求，这里将带给全家人欢乐时光"
    ],
    "ancient_temple": [
        "古寺禅修的宁静之地，感受千年古刹的庄严与神秘",
        "您对传统文化的热爱，在这里可以得到深刻体验",
        "古寺的宁静氛围，让心灵得到净化与升华",
        "悠久的历史传承，展现了佛教文化的博大精深",
        "结合您对古寺文化的兴趣，这里的历史厚重感令人敬畏"
    ],
    "leisure_service": [
        "疲惫时的理想休憩场所，享受片刻的悠闲时光",
        "游览途中的温馨驿站，为您补充能量继续探索",
        "舒适的休闲环境，让您在游览之余放松身心",
        "贴心的服务设施，让您的旅途更加舒适惬意",
        "结合您的游览节奏，这里是放松身心的理想选择"
    ]
}

SPOT_SPECIAL_FEATURES = {
    "灵山大佛": ["世界最高的露天青铜释迦牟尼立像", "高88米", "祈福圣地"],
    "灵山梵宫": ["东方卢浮宫", "艺术殿堂", "星空穹顶", "琉璃巨制"],
    "九龙灌浴": ["动态喷泉表演", "花开见佛", "每天定时表演"],
    "五印坛城": ["藏传佛教风格", "转经筒长廊", "唐卡艺术"],
    "百子戏弥勒": ["青铜雕塑", "百子嬉戏", "寓意多子多福"],
    "五智门": ["汉白玉牌坊", "佛教六度智慧", "进入核心区的标志"],
    "阿育王柱": ["印度风格石柱", "记载佛教历史", "高16.9米"],
    "祥符禅寺": ["千年古刹", "佛教圣地", "历史悠久"],
    "佛足坛": ["佛足印", "摸佛足祈福", "亲子互动"],
    "五明桥": ["五座石桥", "佛教五明智慧", "香水海倒影"],
    "灵山大照壁": ["全国最大照壁", "赵朴初题字", "太湖风光"],
    "拈花广场": ["大型休闲广场", "夜景灯光秀", "喷泉表演"],
    "梵天花海": ["四季花海", "拍照打卡", "亲子游玩"],
    "鹿鸣谷": ["自然生态", "山林步道", "亲近自然"]
}

import random

def recommendation_reason(spot, matched_tags, normalized_profile, popularity_scores, breakdown=None):
    spot_name = getattr(spot, 'spot_name', '')
    reasons = []
    
    if breakdown and breakdown.get('tag_contributions'):
        tag_contributions = sorted(breakdown['tag_contributions'], key=lambda x: x['contribution'], reverse=True)
        for tc in tag_contributions[:2]:
            tag_label = TAG_LABELS.get(tc['tag'], tc['tag'])
            user_weight_pct = int(tc['user_weight'] * 100)
            spot_tag_score = tc['spot_tag_score']
            if user_weight_pct >= 60:
                reasons.append(f"您对{tag_label}兴趣很高（{user_weight_pct}%），该景点此项评分{spot_tag_score}/10")
            elif user_weight_pct >= 40:
                reasons.append(f"您对{tag_label}有兴趣（{user_weight_pct}%），该景点此项评分{spot_tag_score}/10")
            else:
                reasons.append(f"您对{tag_label}略有兴趣（{user_weight_pct}%）")
    
    if breakdown and breakdown.get('matched_keywords'):
        keywords = breakdown['matched_keywords'][:3]
        if keywords:
            reasons.append(f"景点描述包含您关注的'{keywords[0]}'等内容")
    
    if breakdown and breakdown.get('popularity_score', 0) > 5:
        popularity = popularity_scores.get(spot_name, 0)
        if popularity > 0.5:
            reasons.append(f"近期人气较高，很多游客关注")
        elif popularity > 0.2:
            reasons.append(f"近期有不少游客浏览")
    
    if breakdown and breakdown.get('order_score', 0) > 2:
        order = SPOT_ORDER_WEIGHT.get(spot_name, 20)
        if order <= 5:
            reasons.append(f"位于经典游览路线的核心位置")
        elif order <= 10:
            reasons.append(f"是游览路线中的重要景点")
    
    if spot_name in SPOT_SPECIAL_FEATURES:
        features = SPOT_SPECIAL_FEATURES[spot_name]
        feature = random.choice(features)
        reasons.append(f"特色亮点：{feature}")
    
    if not reasons:
        if matched_tags:
            labels = [TAG_LABELS.get(tag, tag) for tag in matched_tags[:2]]
            reasons.append(f"匹配您关注的{'、'.join(labels)}偏好")
        else:
            top_tag = next(iter(sorted(normalized_profile, key=normalized_profile.get, reverse=True)), "zen_culture")
            reasons.append(f"根据您的{TAG_LABELS.get(top_tag, '游览')}偏好推荐")
    
    return "；".join(reasons[:3])

def basic_recommendation_response(db: Session, user_id: str, reason="推荐系统正在使用基础景点排序。"):
    try:
        spots = db.query(Spot).all()[:5]
    except Exception as exc:
        logger.exception("[RECOMMENDATION] 基础推荐读取景点失败: %s", exc)
        spots = []
    if not spots:
        spots = DEFAULT_SPOT_ROWS[:5]

    return {
        "user_id": user_id,
        "user_preferred_tag": "zen_culture",
        "user_preferred_tags": ["zen_culture"],
        "user_profile": {"zen_culture": 1.0},
        "recommendations": [
            {
                "id": route_spot_value(spot, "id"),
                "spot_id": route_spot_value(spot, "id"),
                "name": route_spot_name(spot),
                "spot_name": route_spot_name(spot),
                "description": route_spot_value(spot, "description", ""),
                "reason": reason,
                "score": 0,
                "tags": ["禅意文化"]
            } for spot in spots
        ]
    }

# ==========================
# 冷启动
# ==========================
def get_top_popular_tag(db: Session):
    """
    冷启动：根据 VisitorBehavior 统计
    停留最长 + 满意度最高 + 消费最高 → 综合得出最受欢迎标签
    """
    tag_score = get_popular_tag_scores(db)
    if not any(tag_score.values()):
        return "zen_culture"  # 兜底默认：禅意文化
    return max(tag_score, key=tag_score.get)

# ==========================
# 推荐接口
# ==========================
@router.get("/recommendation")
def get_recommendation(user_id: str, db: Session = Depends(get_db)):
    try:
        precompute_all_spot_tags(db)

        # =============== 1. 构建多标签用户画像 ===============
        user_profile = build_user_tag_profile(db, user_id)
        normalized_profile = normalize_score_map(user_profile)
        preferred_tags = [
            tag for tag, score in sorted(
                normalized_profile.items(),
                key=lambda item: item[1],
                reverse=True
            )[:3]
            if score > 0
        ]
        preferred_tag = preferred_tags[0] if preferred_tags else get_top_popular_tag(db)

        # =============== 2. 综合评分：画像匹配 + 内容相似 + 热度 + 顺序 ===============
        popularity_scores = get_spot_popularity_scores(db)
        all_spots = db.query(Spot).all()
        if not all_spots:
            return basic_recommendation_response(
                db,
                user_id,
                "景点数据尚未入库，已为您展示内置经典景点。"
            )
        scored = []
        for spot in all_spots:
            score, matched_tags, breakdown = score_spot_for_recommendation(spot, normalized_profile, popularity_scores)
            scored.append((spot, score, matched_tags, breakdown))

        scored.sort(key=lambda x: x[1], reverse=True)
        top_spots = scored[:5]
        if not top_spots:
            return basic_recommendation_response(db, user_id)

        # =============== 3. 返回可解释推荐结果 ===============
        return {
            "user_id": user_id,
            "user_preferred_tag": preferred_tag,
            "user_preferred_tags": preferred_tags,
            "user_profile": normalized_profile,
            "recommendations": [
                {
                    "id": spot.id,
                    "spot_id": spot.id,
                    "name": spot.spot_name,
                    "spot_name": spot.spot_name,
                    "description": spot.description,
                    "reason": recommendation_reason(spot, matched_tags, normalized_profile, popularity_scores, breakdown),
                    "score": round(score, 2),
                    "tags": [
                        TAG_LABELS.get(tag, tag)
                        for tag in (matched_tags or list(get_spot_tag_scores(spot.id).keys())[:2])
                    ],
                    "score_breakdown": breakdown
                } for spot, score, matched_tags, breakdown in top_spots
            ]
        }
    except Exception as exc:
        logger.exception("[RECOMMENDATION] 个性推荐计算失败，使用基础推荐: %s", exc)
        db.rollback()
        return basic_recommendation_response(
            db,
            user_id,
            "个性画像暂时不可用，已为您推荐景区经典景点。"
        )

# ==============================
# 8. 游览路线规划接口
# ==============================
# 现在和7.基于偏好推荐的景点深度绑定，预计流程是，大模型先推荐景点，然后用户从中选择要游览的景点，然后大模型基于用户选择的景点生成规划路线
# 此外，项目中还有另一种常规游览路线推荐，即数据库中存储的三条写好的路线，当用户模糊提问游览路线时触发，大模型从中读取并返回
# 这两种方式的切换依赖于大模型函数调用，之后有待实现
# 但是现在的路线规划由于没有接入百度地图API，只能基于spot表中的location判断景点之间的粗略游览顺序
# 之后考虑接入百度地图API，实现前端地图显示、用时和距离计算等
# ==========================
# 22个景点权重（越靠近入口，权重越高）
# ==========================
SPOT_ORDER_WEIGHT = {
    "灵山大照壁": 0,
    "五明桥": 1,
    "佛足坛": 2,
    "五智门": 3,
    "菩提大道": 4,
    "九龙灌浴": 5,
    "降魔浮雕": 6,
    "阿育王柱": 7,
    "百子戏弥勒": 8,
    "祥符禅寺": 9,
    "灵山大佛": 10,
    "佛教文化博览馆": 11,
    "无尽意斋": 12,
    "灵山梵宫": 13,
    "五印坛城": 14,
    "曼飞龙塔": 15,
    "拈花广场": 16,
    "香月花街": 17,
    "拈花堂": 18,
    "五灯湖": 19,
    "梵天花海": 20,
    "鹿鸣谷": 21
}

SPOT_COORDS = {
    "灵山大照壁": {"latitude": 31.42892, "longitude": 120.09487},
    "五明桥": {"latitude": 31.42924, "longitude": 120.09542},
    "佛足坛": {"latitude": 31.42966, "longitude": 120.09586},
    "五智门": {"latitude": 31.43003, "longitude": 120.09628},
    "菩提大道": {"latitude": 31.43048, "longitude": 120.09684},
    "九龙灌浴": {"latitude": 31.43102, "longitude": 120.09726},
    "降魔浮雕": {"latitude": 31.43142, "longitude": 120.09782},
    "阿育王柱": {"latitude": 31.43184, "longitude": 120.09822},
    "百子戏弥勒": {"latitude": 31.43218, "longitude": 120.09876},
    "祥符禅寺": {"latitude": 31.43272, "longitude": 120.09910},
    "灵山大佛": {"latitude": 31.43334, "longitude": 120.09958},
    "佛教文化博览馆": {"latitude": 31.43235, "longitude": 120.10028},
    "无尽意斋": {"latitude": 31.43156, "longitude": 120.10066},
    "灵山梵宫": {"latitude": 31.43072, "longitude": 120.10116},
    "五印坛城": {"latitude": 31.42998, "longitude": 120.10174},
    "曼飞龙塔": {"latitude": 31.42940, "longitude": 120.10208},
    "拈花广场": {"latitude": 31.42876, "longitude": 120.10242},
    "香月花街": {"latitude": 31.42822, "longitude": 120.10282},
    "拈花堂": {"latitude": 31.42774, "longitude": 120.10318},
    "五灯湖": {"latitude": 31.42728, "longitude": 120.10362},
    "梵天花海": {"latitude": 31.42688, "longitude": 120.10418},
    "鹿鸣谷": {"latitude": 31.42636, "longitude": 120.10462}
}

ROUTE_PROFILES = {
    "history": {
        "label": "历史文化",
        "keywords": ["历史", "文化", "佛教", "禅寺", "博览", "大佛", "坛城", "传承", "典故"],
        "description": "串联佛教文化、历史建筑与核心礼佛节点。"
    },
    "scenery": {
        "label": "风景拍照",
        "keywords": ["太湖", "山水", "花海", "湖", "广场", "远眺", "鹿鸣", "风景", "拍照", "打卡"],
        "description": "以开阔视野、山水景观和拍照点为主。"
    },
    "family": {
        "label": "亲子轻松",
        "keywords": ["亲子", "互动", "表演", "九龙", "灌浴", "广场", "休憩", "餐饮", "轻松"],
        "description": "节奏轻松，兼顾演出、休憩和亲子体验。"
    },
    "architecture": {
        "label": "建筑艺术",
        "keywords": ["建筑", "梵宫", "塔", "坛城", "木雕", "壁画", "艺术", "工艺", "穹顶"],
        "description": "聚焦建筑空间、艺术细节和视觉打卡。"
    },
    "blessing": {
        "label": "礼佛祈福",
        "keywords": ["祈福", "礼佛", "大佛", "佛足", "禅寺", "佛教", "供奉", "祥符"],
        "description": "优先安排礼佛、祈福与佛教文化体验点。"
    }
}

DEFAULT_SPOT_ROWS = [
    {"id": 1, "spot_name": "灵山大照壁", "description": "进入灵山胜境后的第一处标志性打卡点。", "location": "景区入口"},
    {"id": 2, "spot_name": "五智门", "description": "通向核心礼佛区域的重要门楼。", "location": "菩提大道前段"},
    {"id": 3, "spot_name": "九龙灌浴", "description": "经典动态演出场景，适合家庭游客。", "location": "景区中轴"},
    {"id": 4, "spot_name": "灵山大佛", "description": "太湖之滨的地标佛像，适合祈福与远眺。", "location": "大佛广场"},
    {"id": 5, "spot_name": "灵山梵宫", "description": "佛教艺术殿堂，建筑、壁画与演出皆值得停留。", "location": "梵宫片区"},
    {"id": 6, "spot_name": "五印坛城", "description": "藏传佛教文化空间，色彩浓烈，适合拍照打卡。", "location": "梵宫东侧"},
    {"id": 7, "spot_name": "香月花街", "description": "餐饮与休憩街区，适合中途补给。", "location": "花街片区"},
    {"id": 8, "spot_name": "梵天花海", "description": "开阔花境与拍照点，适合轻松漫游。", "location": "景区东南"}
]

STANDARD_STAY_MINUTES = {
    "灵山大佛": 35,
    "灵山梵宫": 55,
    "九龙灌浴": 25,
    "五印坛城": 35,
    "祥符禅寺": 30,
    "佛教文化博览馆": 30,
    "香月花街": 25,
    "梵天花海": 25
}

TRAVEL_MODE_CONFIG = {
    "walking": {
        "label": "步行",
        "speed_m_per_min": 70,
        "distance_factor": 1.25,
        "segment_extra_minutes": 0
    },
    "sightseeing_bus": {
        "label": "观光车",
        "speed_m_per_min": 180,
        "distance_factor": 1.35,
        "segment_extra_minutes": 4
    },
    "accessible": {
        "label": "无障碍慢行",
        "speed_m_per_min": 55,
        "distance_factor": 1.35,
        "segment_extra_minutes": 1
    }
}

class RouteLocation(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class RouteGenerateRequest(RouteLocation):
    user_id: str = "guest"
    preferences: List[str] = Field(default_factory=list)
    duration_minutes: Optional[int] = 120
    must_spot_ids: List[int] = Field(default_factory=list)
    start_spot_id: Optional[int] = None
    travel_mode: str = "walking"

class SaveRouteRequest(BaseModel):
    user_id: str = "guest"
    route: dict

class NavigationPoint(BaseModel):
    id: Optional[int | str] = None
    spot_id: Optional[int | str] = None
    name: Optional[str] = None
    latitude: float
    longitude: float
    location: Optional[str] = None
    address: Optional[str] = None
    order: Optional[int] = None

class NavigationRouteRequest(BaseModel):
    user_id: str = "guest"
    provider: str = "amap"
    travel_mode: str = "walking"
    route_name: str = "游览路线"
    start: NavigationPoint
    waypoints: List[NavigationPoint] = Field(default_factory=list)

def route_spot_name(spot):
    if isinstance(spot, dict):
        return spot.get("spot_name") or spot.get("name") or "灵山景点"
    return getattr(spot, "spot_name", None) or "灵山景点"

def route_spot_value(spot, field, default=None):
    if isinstance(spot, dict):
        return spot.get(field, default)
    return getattr(spot, field, default)

def get_route_source_spots(db: Session):
    spots = db.query(Spot).all()
    return spots if spots else DEFAULT_SPOT_ROWS

def calc_distance_m(lat1, lon1, lat2, lon2):
    if not all([lat1, lon1, lat2, lon2]):
        return 0
    radius = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2 +
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
        math.sin(dlon / 2) ** 2
    )
    return int(round(radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))))

def normalize_travel_mode(value):
    return value if value in TRAVEL_MODE_CONFIG else "walking"

def estimate_segment_distance_m(lat1, lon1, lat2, lon2, travel_mode):
    straight_distance = calc_distance_m(lat1, lon1, lat2, lon2)
    if not straight_distance:
        return 0
    config = TRAVEL_MODE_CONFIG[normalize_travel_mode(travel_mode)]
    return int(round(straight_distance * config["distance_factor"]))

def estimate_segment_minutes(distance_m, travel_mode):
    if not distance_m:
        return 0
    config = TRAVEL_MODE_CONFIG[normalize_travel_mode(travel_mode)]
    moving_minutes = math.ceil(distance_m / config["speed_m_per_min"])
    return int(moving_minutes + config["segment_extra_minutes"])

def route_cache_key(origin_lat, origin_lng, destination_lat, destination_lng, travel_mode, provider="amap"):
    return (
        f"{provider}:{normalize_travel_mode(travel_mode)}:"
        f"{round(float(origin_lng), 6)},{round(float(origin_lat), 6)}>"
        f"{round(float(destination_lng), 6)},{round(float(destination_lat), 6)}"
    )

def local_segment_metrics(lat1, lon1, lat2, lon2, travel_mode):
    straight_distance = calc_distance_m(lat1, lon1, lat2, lon2)
    distance = estimate_segment_distance_m(lat1, lon1, lat2, lon2, travel_mode)
    travel_minutes = estimate_segment_minutes(distance, travel_mode)
    return {
        "provider": "haversine_estimate",
        "straight_distance": straight_distance,
        "distance": distance,
        "duration_sec": travel_minutes * 60,
        "travel_minutes": travel_minutes,
        "raw_data": None
    }

def get_cached_segment_metrics(db: Optional[Session], cache_key: str):
    if not db:
        return None
    try:
        cached = db.query(RouteDistanceCache).filter(RouteDistanceCache.cache_key == cache_key).first()
        if not cached:
            return None
        return {
            "provider": cached.provider,
            "straight_distance": None,
            "distance": int(cached.distance_m or 0),
            "duration_sec": int(cached.duration_sec or 0),
            "travel_minutes": math.ceil((cached.duration_sec or 0) / 60),
            "raw_data": json.loads(cached.raw_data) if cached.raw_data else None
        }
    except Exception as e:
        db.rollback()
        print(f"[ROUTE] 距离缓存读取失败，使用实时计算: {str(e)}")
        return None

def save_segment_metrics_cache(
    db: Optional[Session],
    cache_key: str,
    origin,
    destination,
    travel_mode: str,
    metrics: dict
):
    if not db or not metrics.get("distance"):
        return
    try:
        existing = db.query(RouteDistanceCache).filter(RouteDistanceCache.cache_key == cache_key).first()
        if existing:
            existing.distance_m = int(metrics["distance"])
            existing.duration_sec = int(metrics["duration_sec"])
            existing.provider = metrics["provider"]
            existing.raw_data = json.dumps(metrics.get("raw_data"), ensure_ascii=False) if metrics.get("raw_data") else None
        else:
            db.add(RouteDistanceCache(
                cache_key=cache_key,
                origin_id=origin.get("spot_id"),
                destination_id=destination.get("spot_id"),
                origin_lng=float(origin["longitude"]),
                origin_lat=float(origin["latitude"]),
                destination_lng=float(destination["longitude"]),
                destination_lat=float(destination["latitude"]),
                travel_mode=normalize_travel_mode(travel_mode),
                provider=metrics["provider"],
                distance_m=int(metrics["distance"]),
                duration_sec=int(metrics["duration_sec"]),
                raw_data=json.dumps(metrics.get("raw_data"), ensure_ascii=False) if metrics.get("raw_data") else None
            ))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[ROUTE] 距离缓存写入失败，跳过缓存: {str(e)}")

def fetch_amap_walking_distance(origin_lat, origin_lng, destination_lat, destination_lng):
    if not AMAP_WEB_KEY:
        return None

    params = {
        "key": AMAP_WEB_KEY,
        "origins": f"{origin_lng},{origin_lat}",
        "destination": f"{destination_lng},{destination_lat}",
        "type": "3"
    }
    
    for attempt in range(3):
        try:
            with httpx.Client(timeout=10, verify=False) as client:
                response = client.get(AMAP_DISTANCE_URL, params=params)
                response.raise_for_status()
                payload = response.json()
            if payload.get("status") != "1":
                print(f"[ROUTE] 高德距离接口失败: {payload.get('info') or payload}")
                return None
            results = payload.get("results") or []
            if not results:
                return None
            result = results[0]
            distance = int(float(result.get("distance") or 0))
            duration = int(float(result.get("duration") or 0))
            if distance <= 0:
                return None
            if duration <= 0:
                duration = estimate_segment_minutes(distance, "walking") * 60
            return {
                "provider": "amap_distance",
                "straight_distance": None,
                "distance": distance,
                "duration_sec": duration,
                "travel_minutes": math.ceil(duration / 60) if duration else 0,
                "raw_data": result
            }
        except Exception as e:
            print(f"[ROUTE] 高德距离接口异常(第{attempt+1}次): {str(e)}")
            if attempt < 2:
                import time
                time.sleep(1)
                continue
            return None

def resolve_segment_metrics(origin, destination, travel_mode, db=None, distance_memo=None):
    if not origin or not destination:
        return local_segment_metrics(None, None, None, None, travel_mode)
    if not all([origin.get("latitude"), origin.get("longitude"), destination.get("latitude"), destination.get("longitude")]):
        return local_segment_metrics(None, None, None, None, travel_mode)

    travel_mode = normalize_travel_mode(travel_mode)
    key = route_cache_key(
        origin["latitude"],
        origin["longitude"],
        destination["latitude"],
        destination["longitude"],
        travel_mode
    )
    if distance_memo is not None and key in distance_memo:
        return distance_memo[key]

    cached = get_cached_segment_metrics(db, key)
    if cached:
        cached["straight_distance"] = calc_distance_m(
            origin["latitude"],
            origin["longitude"],
            destination["latitude"],
            destination["longitude"]
        )
        if travel_mode != "walking":
            cached["travel_minutes"] = estimate_segment_minutes(cached["distance"], travel_mode)
            cached["duration_sec"] = cached["travel_minutes"] * 60
        if distance_memo is not None:
            distance_memo[key] = cached
        return cached

    amap_metrics = fetch_amap_walking_distance(
        origin["latitude"],
        origin["longitude"],
        destination["latitude"],
        destination["longitude"]
    )
    if amap_metrics:
        amap_metrics["straight_distance"] = calc_distance_m(
            origin["latitude"],
            origin["longitude"],
            destination["latitude"],
            destination["longitude"]
        )
        if travel_mode != "walking":
            amap_metrics["travel_minutes"] = estimate_segment_minutes(amap_metrics["distance"], travel_mode)
            amap_metrics["duration_sec"] = amap_metrics["travel_minutes"] * 60
        save_segment_metrics_cache(db, key, origin, destination, travel_mode, amap_metrics)
        if distance_memo is not None:
            distance_memo[key] = amap_metrics
        return amap_metrics

    fallback = local_segment_metrics(
        origin["latitude"],
        origin["longitude"],
        destination["latitude"],
        destination["longitude"],
        travel_mode
    )
    if distance_memo is not None:
        distance_memo[key] = fallback
    return fallback

def coordinate_payload(latitude, longitude, name="当前位置", spot_id=None):
    return {
        "spot_id": spot_id,
        "name": name,
        "latitude": latitude,
        "longitude": longitude
    }

def parse_amap_polyline(polyline: str):
    points = []
    for pair in (polyline or "").split(";"):
        if not pair or "," not in pair:
            continue
        lng, lat = pair.split(",", 1)
        try:
            points.append({"latitude": float(lat), "longitude": float(lng)})
        except ValueError:
            continue
    return points

def append_polyline(target: list, points: list):
    for point in points:
        if target and target[-1]["latitude"] == point["latitude"] and target[-1]["longitude"] == point["longitude"]:
            continue
        target.append(point)

def nav_point_payload(point):
    return {
        "id": point.id,
        "spot_id": point.spot_id or point.id,
        "name": point.name or "导航点",
        "latitude": point.latitude,
        "longitude": point.longitude,
        "location": point.location or point.address or "灵山胜境景区内",
        "order": point.order
    }

def local_navigation_segment(origin, destination, travel_mode):
    distance = estimate_segment_distance_m(
        origin["latitude"],
        origin["longitude"],
        destination["latitude"],
        destination["longitude"],
        travel_mode
    )
    duration = estimate_segment_minutes(distance, travel_mode) * 60
    mid = {
        "latitude": round((origin["latitude"] + destination["latitude"]) / 2, 6),
        "longitude": round((origin["longitude"] + destination["longitude"]) / 2, 6)
    }
    polyline = [
        {"latitude": origin["latitude"], "longitude": origin["longitude"]},
        mid,
        {"latitude": destination["latitude"], "longitude": destination["longitude"]}
    ]
    return {
        "provider": "haversine_navigation",
        "distance_m": distance,
        "duration_sec": duration,
        "polyline": polyline,
        "steps": [{
            "instruction": f"前往{destination.get('name') or '下一站'}",
            "distance_m": distance,
            "duration_sec": duration,
            "polyline": polyline
        }],
        "raw_data": None
    }

@amap_rate_limited
def fetch_amap_walking_navigation(origin, destination):
    if not AMAP_WEB_KEY:
        logger.info("[AMAP] 高德API密钥未配置，跳过高德导航")
        return None

    params = {
        "key": AMAP_WEB_KEY,
        "origin": f"{origin['longitude']},{origin['latitude']}",
        "destination": f"{destination['longitude']},{destination['latitude']}"
    }

    try:
        with httpx.Client(timeout=10, verify=False) as client:
            response = client.get(AMAP_WALKING_URL, params=params)
            response.raise_for_status()
            payload = response.json()

        status = payload.get("status")
        if status != "1":
            err_code = payload.get("infocode")
            err_msg = payload.get("info")
            logger.warning(f"[AMAP] 高德API返回错误 - status={status}, infocode={err_code}, info={err_msg}")
            if err_code == "10001":
                logger.error("[AMAP] 高德API密钥无效或已过期")
            elif err_code == "10002":
                logger.error("[AMAP] 高德API服务未开通")
            elif err_code == "10003":
                logger.error("[AMAP] 高德API QPS超限，请检查密钥配额")
            elif err_code == "10004":
                logger.error("[AMAP] 高德API当日请求量超限")
            return None

        paths = (payload.get("route") or {}).get("paths") or []
        if not paths:
            logger.warning("[AMAP] 高德API未返回路线数据")
            return None

        path = paths[0]
        all_points = []
        steps = []
        for step in path.get("steps") or []:
            step_points = parse_amap_polyline(step.get("polyline", ""))
            append_polyline(all_points, step_points)
            distance = int(float(step.get("distance") or 0))
            duration = int(float(step.get("duration") or 0))
            steps.append({
                "instruction": step.get("instruction") or "沿路线前行",
                "road": step.get("road") or "",
                "orientation": step.get("orientation") or "",
                "distance_m": distance,
                "duration_sec": duration,
                "polyline": step_points
            })

        if not all_points:
            all_points = [
                {"latitude": origin["latitude"], "longitude": origin["longitude"]},
                {"latitude": destination["latitude"], "longitude": destination["longitude"]}
            ]

        logger.info(f"[AMAP] 高德API调用成功 - 距离={int(float(path.get('distance') or 0))}m, 耗时={int(float(path.get('duration') or 0))}s, 步骤数={len(steps)}")
        return {
            "provider": "amap_walking",
            "distance_m": int(float(path.get("distance") or 0)),
            "duration_sec": int(float(path.get("duration") or 0)),
            "polyline": all_points,
            "steps": steps,
            "raw_data": {
                "distance": path.get("distance"),
                "duration": path.get("duration")
            }
        }
    except httpx.TimeoutException:
        logger.error("[AMAP] 高德API请求超时")
        return None
    except httpx.HTTPStatusError as e:
        logger.error(f"[AMAP] 高德API HTTP错误 - {e.response.status_code}: {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"[AMAP] 高德API调用异常 - {str(e)}")
        return None

def fetch_amap_geocode(address):
    if not AMAP_WEB_KEY:
        logger.info("[AMAP] 高德API密钥未配置，跳过地理编码")
        return None

    params = {
        "key": AMAP_WEB_KEY,
        "address": address,
        "city": "无锡"
    }

    try:
        with httpx.Client(timeout=10, verify=False) as client:
            response = client.get(AMAP_GEOCODE_URL, params=params)
            response.raise_for_status()
            payload = response.json()

        if payload.get("status") != "1":
            err_code = payload.get("infocode")
            err_msg = payload.get("info")
            logger.warning(f"[AMAP] 地理编码失败 - status={status}, infocode={err_code}, info={err_msg}")
            return None

        geocodes = payload.get("geocodes") or []
        if not geocodes:
            logger.warning(f"[AMAP] 地理编码未返回结果 - address={address}")
            return None

        result = geocodes[0]
        location = result.get("location", "")
        if not location:
            logger.warning(f"[AMAP] 地理编码结果无坐标 - address={address}")
            return None

        lng, lat = location.split(",")
        logger.info(f"[AMAP] 地理编码成功 - address={address}, location=({lat}, {lng})")
        return {
            "latitude": float(lat),
            "longitude": float(lng),
            "address": result.get("formatted_address", ""),
            "level": result.get("level", ""),
            "city": result.get("city", "")
        }
    except Exception as e:
        logger.error(f"[AMAP] 地理编码调用异常 - {str(e)}")
        return None

def build_navigation_route(request: NavigationRouteRequest):
    travel_mode = normalize_travel_mode(request.travel_mode)
    travel_config = TRAVEL_MODE_CONFIG[travel_mode]
    start = nav_point_payload(request.start)
    waypoints = [nav_point_payload(point) for point in request.waypoints]
    
    waypoints = reorder_waypoints(start, waypoints)
    
    for index, point in enumerate(waypoints):
        point["order"] = index + 1

    total_distance = 0
    total_duration = 0
    all_polyline = []
    all_steps = []
    segments = []
    providers = []
    previous = start

    for index, destination in enumerate(waypoints):
        segment = fetch_amap_walking_navigation(previous, destination)
        if not segment:
            segment = local_navigation_segment(previous, destination, travel_mode)

        providers.append(segment["provider"])
        total_distance += int(segment.get("distance_m") or 0)
        total_duration += int(segment.get("duration_sec") or 0)
        append_polyline(all_polyline, segment.get("polyline") or [])

        segment_steps = []
        for step in segment.get("steps") or []:
            step_payload = {
                **step,
                "segment_order": index + 1,
                "from_name": previous.get("name"),
                "to_name": destination.get("name")
            }
            segment_steps.append(step_payload)
            all_steps.append(step_payload)

        segments.append({
            "order": index + 1,
            "from": previous,
            "to": destination,
            "provider": segment["provider"],
            "distance_m": int(segment.get("distance_m") or 0),
            "duration_sec": int(segment.get("duration_sec") or 0),
            "polyline": segment.get("polyline") or [],
            "steps": segment_steps
        })
        previous = destination

    provider_type = "amap_walking" if providers and all(item == "amap_walking" for item in providers) else (
        "amap_walking_with_fallback" if "amap_walking" in providers else "haversine_navigation"
    )

    return {
        "route_name": request.route_name,
        "provider": "amap",
        "provider_type": provider_type,
        "coordinate_system": "gcj02",
        "travel_mode": travel_mode,
        "travel_mode_label": travel_config["label"],
        "start": start,
        "start_location": start,
        "waypoints": waypoints,
        "total_distance_m": total_distance,
        "total_duration_sec": total_duration,
        "total_distance": total_distance,
        "total_duration": math.ceil(total_duration / 60) if total_duration else 0,
        "polyline": all_polyline,
        "steps": all_steps,
        "segments": segments
    }

def reorder_waypoints(start, waypoints):
    if not waypoints:
        return []
    
    remaining = list(waypoints)
    ordered = []
    current = start
    
    while remaining:
        nearest = None
        min_distance = float('inf')
        nearest_index = -1
        
        for i, point in enumerate(remaining):
            dist = haversine_distance(
                current.get("latitude"),
                current.get("longitude"),
                point.get("latitude"),
                point.get("longitude")
            )
            if dist < min_distance:
                min_distance = dist
                nearest = point
                nearest_index = i
        
        if nearest is not None:
            ordered.append(nearest)
            remaining.pop(nearest_index)
            current = nearest
    
    return ordered

def haversine_distance(lat1, lon1, lat2, lon2):
    if None in [lat1, lon1, lat2, lon2]:
        return float('inf')
    radius = 6371000
    dlat = (lat2 - lat1) * math.pi / 180
    dlon = (lon2 - lon1) * math.pi / 180
    a = math.sin(dlat / 2) ** 2 + \
        math.cos(lat1 * math.pi / 180) * \
        math.cos(lat2 * math.pi / 180) * \
        math.sin(dlon / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def spot_payload(spot, db: Session = None):
    name = route_spot_name(spot)
    spot_id = route_spot_value(spot, "id", 0)
    coord = SPOT_COORDS.get(name, {})
    
    stay_minutes = 25
    weight = 999
    if db and spot_id:
        meta = db.query(SpotVisitMeta).filter(SpotVisitMeta.spot_id == spot_id).first()
        if meta:
            stay_minutes = meta.suggested_stay_minutes or 25
            weight = meta.official_order or 999
    
    return {
        "id": spot_id,
        "name": name,
        "description": route_spot_value(spot, "description", "") or route_spot_value(spot, "culture_connotation", ""),
        "location": route_spot_value(spot, "location", "") or "灵山胜境景区内",
        "open_status": route_spot_value(spot, "open_info", "") or "以景区当日公告为准",
        "latitude": route_spot_value(spot, "latitude", None) or coord.get("latitude"),
        "longitude": route_spot_value(spot, "longitude", None) or coord.get("longitude"),
        "weight": weight,
        "stay_minutes": stay_minutes
    }

def score_spot_for_profile(spot, profile):
    name = route_spot_name(spot)
    text = " ".join([
        name,
        str(route_spot_value(spot, "description", "") or ""),
        str(route_spot_value(spot, "culture_connotation", "") or ""),
        str(route_spot_value(spot, "highlights", "") or "")
    ])
    score = 0
    for keyword in profile["keywords"]:
        if keyword in text:
            score += 3
    score += max(0, 24 - SPOT_ORDER_WEIGHT.get(name, 20)) * 0.08
    return score

def score_spot_tags_for_route_preferences(spot, preferences):
    spot_id = route_spot_value(spot, "id", 0)
    tag_scores = get_spot_tag_scores(spot_id)
    score = 0.0
    for preference in preferences:
        for tag in ROUTE_TO_RECOMMENDATION_TAGS.get(preference, []):
            if tag in tag_scores:
                score += ((tag_scores[tag] or 10) / 10) * 4
    return score

def order_route_by_distance(route, latitude=None, longitude=None, start_spot_id=None):
    if not route:
        return []

    remaining = sorted(route, key=lambda item: item["weight"])
    ordered = []

    start_spot = None
    if start_spot_id:
        start_spot = next((item for item in remaining if item["id"] == start_spot_id), None)
        if start_spot:
            ordered.append(start_spot)
            remaining = [item for item in remaining if item["id"] != start_spot_id]

    current = start_spot or (
        {"latitude": latitude, "longitude": longitude}
        if latitude and longitude else None
    )

    def segment_distance(origin, destination):
        if not origin or not origin.get("latitude") or not origin.get("longitude"):
            return 10**9
        if not destination.get("latitude") or not destination.get("longitude"):
            return 10**9
        return estimate_segment_distance_m(
            origin["latitude"],
            origin["longitude"],
            destination["latitude"],
            destination["longitude"],
            "walking"
        )

    def route_distance(origin, spots):
        total = 0
        prev = origin
        for spot in spots:
            total += segment_distance(prev, spot)
            prev = spot
        return total

    if current and len(remaining) <= 8:
        best_tail = min(
            itertools.permutations(remaining),
            key=lambda spots: (
                route_distance(current, spots),
                [item["weight"] for item in spots]
            ),
            default=()
        )
        return ordered + list(best_tail)

    while remaining:
        if not current or not current.get("latitude") or not current.get("longitude"):
            ordered.extend(remaining)
            break
        next_spot = min(
            remaining,
            key=lambda item: (
                segment_distance(current, item),
                item["weight"]
            )
        )
        ordered.append(next_spot)
        remaining.remove(next_spot)
        current = next_spot

    return ordered

def build_route(
    name,
    route_type,
    description,
    selected_spots,
    latitude=None,
    longitude=None,
    travel_mode="walking",
    db: Optional[Session] = None,
    distance_memo=None,
    start_spot_id=None
):
    travel_mode = normalize_travel_mode(travel_mode)
    travel_config = TRAVEL_MODE_CONFIG[travel_mode]
    route = order_route_by_distance(
        [spot_payload(spot, db) for spot in selected_spots],
        latitude,
        longitude,
        start_spot_id
    )
    total_distance = 0
    prev_lat = latitude
    prev_lon = longitude
    prev_name = "当前位置"
    prev_id = None
    segments = []
    segment_providers = []
    for index, item in enumerate(route):
        origin = coordinate_payload(prev_lat, prev_lon, prev_name, prev_id) if prev_lat and prev_lon else None
        destination = coordinate_payload(item["latitude"], item["longitude"], item["name"], item["id"])
        metrics = resolve_segment_metrics(origin, destination, travel_mode, db, distance_memo) if origin else {
            "provider": "no_start_location",
            "straight_distance": 0,
            "distance": 0,
            "duration_sec": 0,
            "travel_minutes": 0,
            "raw_data": None
        }
        straight_distance = metrics.get("straight_distance") or 0
        distance = int(metrics.get("distance") or 0)
        travel_minutes = int(metrics.get("travel_minutes") or 0)
        segment_providers.append(metrics.get("provider", "unknown"))
        total_distance += distance
        segments.append({
            "order": index + 1,
            "from": origin,
            "to": destination,
            "spot_id": item["id"],
            "name": item["name"],
            "provider": metrics.get("provider"),
            "straight_distance_from_previous": straight_distance,
            "distance_from_previous": distance,
            "duration_sec": int(metrics.get("duration_sec") or travel_minutes * 60),
            "travel_minutes": travel_minutes,
            "walk_minutes": travel_minutes,
            "stay_minutes": item["stay_minutes"]
        })
        prev_lat = item["latitude"]
        prev_lon = item["longitude"]
        prev_name = item["name"]
        prev_id = item["id"]

    stay_total = sum(item["stay_minutes"] for item in route)
    travel_total = sum(item["travel_minutes"] for item in segments)
    if route and latitude is None and longitude is None:
        travel_total = max(travel_total, len(route) * 6)
    used_amap = any(provider == "amap_distance" for provider in segment_providers)
    used_fallback = any(provider == "haversine_estimate" for provider in segment_providers)
    if used_amap and used_fallback:
        model_type = "amap_distance_with_haversine_fallback"
        model_note = "优先使用高德步行距离接口，部分分段失败时回退到经纬度估算。"
    elif used_amap:
        model_type = "amap_distance"
        model_note = "使用高德地图步行距离接口返回的路网距离和耗时。"
    else:
        model_type = "haversine_estimate"
        model_note = "未配置高德Key或接口不可用，使用球面直线距离乘以园区道路系数估算。"
    crowd_note = "已从当前起点按距离优先安排游览顺序，优先选择估算总距离最短的走法以减少折返；移动中不自动重算整条路线。"
    return {
        "route_id": uuid.uuid4().hex,
        "route_name": name,
        "route_type": route_type,
        "travel_mode": travel_mode,
        "travel_mode_label": travel_config["label"],
        "description": description,
        "strategy": crowd_note,
        "total_spots": len(route),
        "total_distance": total_distance,
        "total_duration": stay_total + travel_total,
        "travel_duration": travel_total,
        "walk_duration": travel_total,
        "stay_duration": stay_total,
        "distance_model": {
            "type": model_type,
            "providers": sorted(set(segment_providers)),
            "distance_factor": travel_config["distance_factor"],
            "speed_m_per_min": travel_config["speed_m_per_min"],
            "segment_extra_minutes": travel_config["segment_extra_minutes"],
            "coordinate_system": "gcj02",
            "note": model_note
        },
        "route": route,
        "segments": segments
    }

def save_route_history(db: Session, user_id: str, route: dict):
    history = RouteHistory(
        visitor_id=user_id or "guest",
        route_name=route.get("route_name", "游览路线"),
        route_type=route.get("route_type", "custom"),
        route_data=json.dumps(route, ensure_ascii=False),
        total_duration=route.get("total_duration"),
        total_distance=route.get("total_distance"),
        spot_count=route.get("total_spots") or len(route.get("route", []))
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    return history

def normalize_duration_budget(value):
    if not value:
        return 120
    return max(30, min(int(value), 180))

def find_spots_by_ids(spots, spot_ids):
    id_set = set(spot_ids or [])
    return [spot for spot in spots if route_spot_value(spot, "id") in id_set]

def score_spot_for_preferences(spot, preferences, popularity_scores=None):
    valid_preferences = [item for item in preferences if item in ROUTE_PROFILES]
    if not valid_preferences:
        valid_preferences = ["history", "scenery", "family", "architecture", "blessing"]

    score = 0.0
    for preference in valid_preferences:
        score += score_spot_for_profile(spot, ROUTE_PROFILES[preference])
    score += score_spot_tags_for_route_preferences(spot, valid_preferences)
    name = route_spot_name(spot)
    if popularity_scores:
        score += popularity_scores.get(name, 0) * 3
    score += max(0, 24 - SPOT_ORDER_WEIGHT.get(name, 20)) * 0.12
    return score

def route_description(preferences, must_count, over_time):
    labels = [ROUTE_PROFILES[item]["label"] for item in preferences if item in ROUTE_PROFILES]
    parts = []
    if labels:
        parts.append("匹配" + "、".join(labels))
    if must_count:
        parts.append(f"包含{must_count}个必去景点")
    if not parts:
        parts.append("按经典游览顺序推荐")
    timing = "，但必去点较多，预计会超过当前时间预算" if over_time else "，控制在当前时间预算内"
    return "根据" + "，".join(parts) + timing + "，并从当前起点按距离优先安排顺序，尽量减少折返。"

def select_route_spots(
    spots,
    required_spots,
    preferences,
    budget,
    target_count,
    latitude,
    longitude,
    travel_mode,
    db: Optional[Session] = None,
    distance_memo=None,
    start_spot_id=None
):
    selected = list(required_spots)
    selected_ids = {route_spot_value(spot, "id") for spot in selected}
    popularity_scores = {}
    if db:
        try:
            precompute_all_spot_tags(db)
            popularity_scores = get_spot_popularity_scores(db)
        except Exception as exc:
            logger.exception("[ROUTE] 偏好标签/热度评分失败，降级为关键词评分: %s", exc)
            db.rollback()
    candidates = [
        spot for spot in sorted(
            spots,
            key=lambda item: score_spot_for_preferences(item, preferences, popularity_scores),
            reverse=True
        )
        if route_spot_value(spot, "id") not in selected_ids
    ]

    for spot in candidates:
        if len(selected) >= target_count:
            break
        next_selected = selected + [spot]
        next_route = build_route(
            "候选路线",
            "generated",
            "",
            next_selected,
            latitude,
            longitude,
            travel_mode,
            db,
            distance_memo,
            start_spot_id
        )
        if next_route["total_duration"] <= budget or len(selected) < max(1, min(2, target_count)):
            selected = next_selected
            selected_ids.add(route_spot_value(spot, "id"))

    if not selected and candidates:
        selected = candidates[:1]

    return selected

@router.post("/routes/generate")
def generate_routes(request: RouteGenerateRequest, db: Session = Depends(get_db)):
    spots = get_route_source_spots(db)
    budget = normalize_duration_budget(request.duration_minutes)
    travel_mode = normalize_travel_mode(request.travel_mode)
    distance_memo = {}
    preferences = [item for item in request.preferences if item in ROUTE_PROFILES]
    required_spots = find_spots_by_ids(spots, request.must_spot_ids)

    if request.must_spot_ids and not required_spots:
        raise HTTPException(status_code=404, detail="未找到选中的必去景点")

    variants = [
        ("轻松线", 3),
        ("经典线", 5),
        ("深度线", 7)
    ]
    routes = []
    seen_signatures = set()
    base_label = "偏好路线" if preferences else "经典路线"
    if required_spots and preferences:
        base_label = "必去补充路线"
    elif required_spots:
        base_label = "必去景点路线"

    for variant_name, target_count in variants:
        if required_spots and not preferences:
            selected = required_spots
        else:
            selected = select_route_spots(
                spots,
                required_spots,
                preferences,
                budget,
                target_count,
                request.latitude,
                request.longitude,
                travel_mode,
                db,
                distance_memo,
                request.start_spot_id
            )
        route = build_route(
            f"{base_label}{variant_name}",
            "generated",
            "",
            selected,
            request.latitude,
            request.longitude,
            travel_mode,
            db,
            distance_memo,
            request.start_spot_id
        )
        signature = tuple(item["id"] for item in route["route"])
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        route["time_budget"] = budget
        route["is_over_time"] = route["total_duration"] > budget
        route["must_spot_ids"] = request.must_spot_ids
        route["preferences"] = preferences
        route["start_location"] = {
            "latitude": request.latitude,
            "longitude": request.longitude,
            "spot_id": request.start_spot_id
        }
        route["description"] = route_description(preferences, len(required_spots), route["is_over_time"])
        route["strategy"] = f"先锁定生成时的起点，若起点景点在路线中则作为第一站，其余景点按估算总距离优先排序，尽量减少总距离和折返；距离与耗时按{route['travel_mode_label']}和{route['distance_model']['type']}计算，移动中不自动重算整条路线。"
        routes.append(route)

    routes.sort(key=lambda item: (item["is_over_time"], item["total_duration"], -item["total_spots"]))
    return {
        "routes": routes[:3],
        "input": {
            "preferences": preferences,
            "duration_minutes": budget,
            "travel_mode": travel_mode,
            "must_spot_ids": request.must_spot_ids,
            "start_spot_id": request.start_spot_id,
            "start": {
                "latitude": request.latitude,
                "longitude": request.longitude
            }
        }
    }

@router.post("/routes/history")
def save_route(request: SaveRouteRequest, db: Session = Depends(get_db)):
    history = save_route_history(db, request.user_id, request.route)
    return {"id": history.id, "status": "ok"}

@router.get("/routes/history")
def get_route_history(user_id: str = "guest", limit: int = 20, db: Session = Depends(get_db)):
    records = db.query(RouteHistory)\
        .filter(RouteHistory.visitor_id == user_id)\
        .order_by(RouteHistory.created_at.desc())\
        .limit(limit)\
        .all()
    return [
        {
            "id": item.id,
            "route_name": item.route_name,
            "route_type": item.route_type,
            "total_duration": item.total_duration,
            "total_distance": item.total_distance,
            "spot_count": item.spot_count,
            "created_at": item.created_at.isoformat() if item.created_at else "",
            "route": json.loads(item.route_data)
        }
        for item in records
    ]

@router.post("/routes/navigation")
def generate_navigation_route(request: NavigationRouteRequest, db: Session = Depends(get_db)):
    if not request.waypoints:
        raise HTTPException(status_code=400, detail="请至少选择一个导航目的地")
    
    visitor_id = request.user_id or 'guest'
    
    for waypoint in request.waypoints:
        spot_name = waypoint.name
        spot_id = waypoint.spot_id
        if spot_name:
            behavior = AppUserBehavior(
                visitor_id=visitor_id,
                behavior_type='navigate',
                spot_id=spot_id,
                spot_name=spot_name
            )
            db.add(behavior)
    db.commit()
    
    return build_navigation_route(request)

from time import sleep

# ======================
# 本地情绪分析关键词（降级方案）
# ======================
NEGATIVE_WORDS = ["累", "烦", "糟糕", "失望", "找不到", "不好", "生气", "愤怒", "讨厌", "烦人", "烦躁", "难过", "伤心", "郁闷", "沮丧"]
POSITIVE_WORDS = ["开心", "喜欢", "不错", "好看", "满意", "推荐", "谢谢", "太棒了", "太好了", "厉害", "赞", "漂亮"]
SURPRISED_WORDS = ["惊讶", "哇", "真的吗", "居然", "没想到"]
SHY_WORDS = ["害羞", "不好意思", "尴尬"]
ANGRY_WORDS = ["滚", "闭嘴", "傻", "笨", "废物", "垃圾", "白痴", "骂", "打人", "投诉你", "你不行", "没用"]
SCENIC_WORDS = [
    "灵山", "大佛", "梵宫", "九龙灌浴", "五印坛城", "祥符禅寺", "景区", "景点", "门票", "路线", "演出", "开放",
    "停车", "餐饮", "祈福", "导游", "讲解", "游览", "无锡", "佛", "禅", "游客", "拍照", "交通",
    "厕所", "洗手间", "服务中心", "出口", "入口", "观光车", "母婴", "医疗", "失物", "储物", "行李", "轮椅"
]
GENERAL_CHAT_WORDS = ["你好", "您好", "谢谢", "再见", "早上好", "下午好", "晚上好", "你是谁", "叫什么", "名字", "自我介绍"]

def is_question(text: str) -> bool:
    question_words = ["？", "?", "吗", "呢", "谁", "什么", "怎么", "如何", "哪里", "在哪", "多久", "几点", "多少", "能不能", "可不可以"]
    return any(q in text for q in question_words)

def is_scenic_related(text: str) -> bool:
    return any(word in text for word in SCENIC_WORDS) or any(word in text for word in GENERAL_CHAT_WORDS)

def is_disrespectful(text: str) -> bool:
    return any(word in text for word in ANGRY_WORDS)

def analyze_emotion_local(text: str) -> dict:
    """本地关键词匹配情绪分析（降级方案）"""
    text_lower = text

    if is_disrespectful(text_lower):
        return {"emotion": "angry", "score": 0.9, "source": "local_rule", "reason": "检测到不尊重或攻击性表达"}
    if is_question(text_lower) and not is_scenic_related(text_lower):
        return {"emotion": "angry", "score": 0.75, "source": "local_rule", "reason": "问题与灵山胜境导览场景无关"}
    if any(word in text_lower for word in NEGATIVE_WORDS):
        return {"emotion": "negative", "score": 0.8, "source": "local_rule", "reason": "检测到负面情绪词"}
    if any(word in text_lower for word in POSITIVE_WORDS):
        return {"emotion": "positive", "score": 0.8, "source": "local_rule", "reason": "检测到正面情绪词"}
    if any(word in text_lower for word in SURPRISED_WORDS):
        return {"emotion": "surprised", "score": 0.7, "source": "local_rule", "reason": "检测到惊讶表达"}
    if any(word in text_lower for word in SHY_WORDS):
        return {"emotion": "shy", "score": 0.7, "source": "local_rule", "reason": "检测到害羞表达"}
    
    return {"emotion": "neutral", "score": 1.0, "source": "local_rule", "reason": "未检测到明显情绪"}

import asyncio

async def analyze_emotion_with_llm(text: str) -> Optional[dict]:
    if not AI_API_KEY:
        return None

    prompt = f"""
你是景区数字人的情绪与意图分类器。请只输出JSON，不要解释。
可选emotion只能是：positive, negative, neutral, surprised, shy, angry。
分类规则：
1. 用户开心、感谢、满意、夸奖时为positive。
2. 用户难过、焦虑、失望、疲惫、求助受挫时为negative。
3. 用户惊讶、强烈意外时为surprised。
4. 用户害羞、不好意思、尴尬时为shy。
5. 用户不尊重、辱骂、挑衅，或提出与灵山胜境导览完全无关的问题时为angry。
6. 正常询问灵山胜境景点、路线、演出、门票、交通、餐饮、祈福等导览问题时为neutral。
用户输入：{text}
输出格式：{{"emotion":"neutral","score":0.0,"reason":"简短原因"}}
"""

    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": QWEN_MODEL,
        "messages": [
            {"role": "system", "content": "你只输出合法JSON。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0
    }

    try:
        response = await http_client.post(QWEN_API_URL, headers=headers, json=payload, timeout=8)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        match = re.search(r"\{.*\}", content, re.S)
        if not match:
            return None
        result = json.loads(match.group(0))
        emotion = result.get("emotion", "neutral")
        if emotion not in EMOTION_EXPRESSION_MAP:
            emotion = "neutral"
        return {
            "emotion": emotion,
            "score": float(result.get("score", 0.8) or 0.8),
            "reason": str(result.get("reason", "")),
            "source": "llm"
        }
    except Exception as e:
        print(f"[EMOTION] LLM情绪分类失败，准备降级: {str(e)}")
        return None

# ======================
# 9.景区入口位置
# ======================
@router.get("/scenic/entrance")
def get_scenic_entrance():
    geocode_result = fetch_amap_geocode("无锡灵山胜境游客中心")
    
    if geocode_result:
        return {
            "success": True,
            "latitude": geocode_result["latitude"],
            "longitude": geocode_result["longitude"],
            "name": "灵山胜境游客中心",
            "address": geocode_result["address"],
            "source": "amap_geocode"
        }
    
    return {
        "success": False,
        "latitude": 31.42892,
        "longitude": 120.09487,
        "name": "灵山胜境游客中心",
        "source": "fallback"
    }

# ======================
# 10.情感分析
# ======================
@router.post("/emotion")
async def analyze_emotion(text: str = Body(..., embed=True)):
    local_result = analyze_emotion_local(text)
    if local_result["emotion"] in ("angry", "surprised", "shy"):
        print(f"[EMOTION] 本地高优先级规则命中: {local_result}")
        return local_result

    llm_result = await analyze_emotion_with_llm(text)
    if llm_result:
        print(f"[EMOTION] LLM情绪分类完成: {llm_result}")
        return llm_result

    try:
        print(f"[EMOTION] 开始调用百度API分析: {text}")
        access_token = await get_access_token()
        print(f"[EMOTION] 获取到access_token")

        url = "https://aip.baidubce.com/rpc/2.0/nlp/v1/sentiment_classify"
        params = {
            "access_token": access_token,
            "charset": "UTF-8"
        }

        body = {
            "text": text
        }

        headers = {
            "Content-Type": "application/json"
        }

        response = await http_client.post(url, json=body, params=params, headers=headers)
        result = response.json()
        print(f"[EMOTION] 百度API返回: {result}")

        if "error_code" in result:
            error_code = result["error_code"]
            error_msg = result.get("error_msg", "")
            print(f"[EMOTION] 百度API错误: code={error_code}, msg={error_msg}")
            
            if error_code == 18:
                await asyncio.sleep(0.5)
                response = await http_client.post(url, json=body, params=params, headers=headers)
                result = response.json()
                print(f"[EMOTION] 重试后百度API返回: {result}")

        items = result.get("items", [])
        if items:
            item = items[0]
            sentiment = item["sentiment"]
            confidence = item["confidence"]
            positive_prob = item["positive_prob"]
            negative_prob = item["negative_prob"]

            if sentiment == 0:
                emotion = "negative"
            elif sentiment == 1:
                emotion = "neutral"
            else:
                emotion = "positive"

            print(f"[EMOTION] 百度API分析完成: emotion={emotion}, confidence={confidence}")

            return {
                "emotion": emotion,
                "score": round(confidence, 2),
                "positive_prob": round(positive_prob, 2),
                "negative_prob": round(negative_prob, 2),
                "log_id": result.get("log_id"),
                "source": "baidu_api"
            }
        
        print(f"[EMOTION] 百度API无结果，使用本地降级方案")
        return analyze_emotion_local(text)

    except Exception as e:
        print(f"[EMOTION] 百度API调用失败，使用本地降级方案: {str(e)}")
        return analyze_emotion_local(text)

# ==============================
# 10. GPS 附近景点
# ==============================
@router.get("/gps")
def get_gps_location(
    lat: float, 
    lon: float, 
    max_results: int = 5,           # 限制返回数量
    max_distance_km: float = 3.0,   # 最大距离过滤
    mode: str = "walking",          # 出行方式
    db: Session = Depends(get_db)
):
    travel_mode = normalize_travel_mode(mode)
    origin = coordinate_payload(lat, lon, "当前位置", None)
    spots = db.query(Spot).all()
    nearby = []
    distance_memo = {}

    for s in spots:
        if not s.latitude or not s.longitude:
            continue

        destination = coordinate_payload(s.latitude, s.longitude, s.spot_name, s.id)
        metrics = resolve_segment_metrics(origin, destination, travel_mode, db, distance_memo)
        distance = int(metrics.get("distance") or 0)
        duration_sec = int(metrics.get("duration_sec") or 0)
        if not distance or distance > max_distance_km * 1000:
            continue

        nearby.append({
            "id": s.id,
            "name": s.spot_name,
            "description": s.description,
            "distance": distance,
            "distance_text": f"{distance}米" if distance < 1000 else f"{round(distance / 1000, 1)}公里",
            "walk_time": f"{math.ceil(duration_sec / 60)}分钟",
            "provider": metrics.get("provider"),
            "location": {
                "latitude": s.latitude,
                "longitude": s.longitude
            }
        })

    nearby.sort(key=lambda x: x["distance"])
    return {
        "your_location": {"latitude": lat, "longitude": lon},
        "coordinate_system": "gcj02",
        "travel_mode": travel_mode,
        "nearby_spots": nearby[:max_results]
    }

# ==============================
# 11. 游客行为分析接口
# ==============================
from app.schemas import VisitorBehaviorResponse
from app.models import VisitorBehavior
from typing import List

# 获取所有游客行为数据
@router.get("/behavior", response_model=List[VisitorBehaviorResponse])
def get_visitor_behavior(db: Session = Depends(get_db)):
    data = db.query(VisitorBehavior).all()
    return data

# 根据游客ID获取行为数据
@router.get("/behavior/{visitor_id}", response_model=List[VisitorBehaviorResponse])
def get_visitor_behavior_by_user(visitor_id: str, db: Session = Depends(get_db)):
    data = db.query(VisitorBehavior).filter(VisitorBehavior.visitor_id == visitor_id).all()
    return data
