import math
import re
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models import AppUserBehavior, RouteHistory, ScenicActivity, Spot, TicketProduct, VisitorInteraction


SESSION_MEMORY: Dict[str, deque] = defaultdict(lambda: deque(maxlen=6))
SESSION_MEMORY_TTL = timedelta(minutes=20)
PENDING_LOOKBACK_TURNS = 2


CAPABILITIES = [
    {
        "id": "query_activities",
        "description": "查询景区演出、表演、活动、禅修体验的时间、地点、剩余场次",
        "execution_mode": "direct_answer",
    },
    {
        "id": "query_tickets",
        "description": "查询景区门票、观光车票、价格、购票提示、票务服务点",
        "execution_mode": "direct_answer",
    },
    {
        "id": "spot_guide",
        "description": "查询单个景点介绍、历史、文化、故事、开放信息",
        "execution_mode": "direct_answer",
    },
    {
        "id": "single_spot_navigation",
        "description": "导航到单个景点或服务点，拉起系统地图",
        "execution_mode": "action",
    },
    {
        "id": "route_planning",
        "description": "根据偏好、时间、必去景点规划一条游览路线",
        "execution_mode": "handoff_required",
    },
    {
        "id": "query_visit_history",
        "description": "查询用户游览足迹、看过哪些景点、停留记录",
        "execution_mode": "direct_answer",
    },
    {
        "id": "query_navigation_history",
        "description": "查询用户导航去过哪些地方、导航历史、路线历史",
        "execution_mode": "direct_answer",
    },
    {
        "id": "nearby_food",
        "description": "查询附近餐饮、吃饭、素斋、餐厅、小吃",
        "execution_mode": "direct_answer",
    },
    {
        "id": "nearby_rest_or_cool_place",
        "description": "查询附近休息、避暑、室内、阴凉、服务中心、可停留地点",
        "execution_mode": "direct_answer",
    },
    {
        "id": "nearby_service",
        "description": "查询附近厕所、停车、售票、母婴、医疗、失物招领等服务设施",
        "execution_mode": "direct_answer",
    },
]


SPOT_ALIASES = {
    "灵山大佛": ["大佛", "佛像", "拜佛", "许愿", "灵山那个佛"],
    "灵山梵宫": ["梵宫", "宫殿", "吉祥颂", "看演出的地方"],
    "九龙灌浴": ["九龙", "灌浴", "喷泉", "九龙灌浴广场"],
    "五明桥": ["五明桥", "桥"],
    "五印坛城": ["坛城", "五印坛城"],
}


STATE_PATTERNS = {
    "lost": ["迷路", "找不到", "不知道在哪", "走丢", "怎么出去"],
    "anxious": ["着急", "急", "赶时间", "来不及"],
    "hot": ["热", "晒", "避暑", "凉快", "中暑", "太闷"],
    "tired": ["累", "走不动", "休息", "歇", "坐一会"],
    "hungry": ["饿", "吃", "餐厅", "饭", "素斋", "小吃"],
    "confused": ["不知道", "不清楚", "怎么弄", "去哪", "接下来"],
    "angry": ["投诉", "生气", "不满", "差劲", "太糟"],
    "curious": ["为什么", "故事", "历史", "文化", "讲讲", "介绍"],
}


def contains_any(text: str, words: List[str]) -> bool:
    return any(word and word in text for word in words)


def normalize_name(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


def action(
    name: str,
    action_type: str,
    icon: str = "",
    path: str = "",
    params: Optional[dict] = None,
    payload: Optional[dict] = None,
    confidence: float = 0.8,
) -> dict:
    return {
        "name": name,
        "icon": icon,
        "action_type": action_type,
        "path": path,
        "params": params or {},
        "payload": payload or {},
        "confidence": confidence,
    }


SERVICE_CENTER_KEYWORDS = ["游客中心", "游客服务中心", "服务中心", "接待中心", "问询处", "咨询台"]


def prioritize_service_center_items(items: List[dict]) -> List[dict]:
    ranked = []
    seen = set()
    for item in items:
        name = item.get("name", "")
        desc = item.get("desc", "")
        key = normalize_name(f"{name}|{desc}|{item.get('latitude')}|{item.get('longitude')}")
        if key in seen:
            continue
        seen.add(key)
        text = name + desc
        exact_score = 0 if any(keyword in name for keyword in ["游客服务中心", "游客中心"]) else 1
        text_score = 0 if contains_any(text, SERVICE_CENTER_KEYWORDS) else 1
        distance = item.get("distance")
        distance_score = distance if isinstance(distance, (int, float)) else float("inf")
        ranked.append((text_score, exact_score, distance_score, item))
    ranked.sort(key=lambda item: (item[0], item[1], item[2]))
    return [item for _, _, _, item in ranked]


def distance_m(lat1: Any, lon1: Any, lat2: Any, lon2: Any) -> float:
    try:
        lat1 = float(lat1)
        lon1 = float(lon1)
        lat2 = float(lat2)
        lon2 = float(lon2)
    except (TypeError, ValueError):
        return float("inf")

    radius = 6371000
    p1 = lat1 * 3.141592653589793 / 180
    p2 = lat2 * 3.141592653589793 / 180
    dlat = (lat2 - lat1) * 3.141592653589793 / 180
    dlon = (lon2 - lon1) * 3.141592653589793 / 180
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def sort_by_user_location(points: List[dict], user_location: Optional[dict]) -> List[dict]:
    if not user_location:
        return points
    return sorted(
        points,
        key=lambda point: distance_m(
            user_location.get("latitude"),
            user_location.get("longitude"),
            point.get("latitude"),
            point.get("longitude"),
        ),
    )


class OrchestrationResult:
    def __init__(
        self,
        handled: bool = False,
        reply_text: str = "",
        actions: Optional[List[dict]] = None,
        reply_mode: str = "direct_answer",
        context: Optional[dict] = None,
    ):
        self.handled = handled
        self.reply_text = reply_text
        self.actions = actions or []
        self.reply_mode = reply_mode
        self.context = context or {}


def conversation_key(user_id: str, session_id: Optional[str] = None) -> str:
    return f"{user_id or 'guest'}:{session_id or 'default'}"


def parse_memory_time(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def is_memory_fresh(item: dict) -> bool:
    created_at = parse_memory_time(item.get("created_at"))
    return bool(created_at and datetime.now() - created_at <= SESSION_MEMORY_TTL)


def remember(memory_key: str, item: dict) -> None:
    key = memory_key or "guest:default"
    SESSION_MEMORY[key].append({**item, "created_at": datetime.now().isoformat()})


def get_memory(memory_key: str) -> List[dict]:
    key = memory_key or "guest:default"
    fresh_items = [item for item in SESSION_MEMORY[key] if is_memory_fresh(item)]
    if len(fresh_items) != len(SESSION_MEMORY[key]):
        SESSION_MEMORY[key] = deque(fresh_items, maxlen=6)
    return fresh_items


def detect_user_states(text: str) -> List[str]:
    return [state for state, words in STATE_PATTERNS.items() if contains_any(text, words)]


def detect_conditions(text: str) -> dict:
    return {
        "nearby": contains_any(text, ["附近", "周围", "旁边", "离我近", "最近"]),
        "today": "今天" in text or "今日" in text,
        "remaining_today": contains_any(text, ["还有", "接下来", "后面", "未开始", "剩下"]),
        "now": contains_any(text, ["现在", "当前", "此刻", "马上"]),
        "preference": contains_any(text, ["偏好", "喜欢", "适合我", "个性化", "按我的"]),
        "route": contains_any(text, ["路线", "行程", "规划", "怎么游", "怎么玩"]),
        "history": contains_any(text, ["去过", "游览过", "足迹", "浏览记录", "导航记录", "路线历史", "游览历史"]),
    }


def resolve_spot(text: str, db: Session) -> Optional[Spot]:
    normalized_text = normalize_name(text)
    spots = db.query(Spot).all()
    best = None
    best_score = 0

    for spot in spots:
        names = [spot.spot_name or ""]
        names.extend(SPOT_ALIASES.get(spot.spot_name or "", []))
        for name in names:
            normalized = normalize_name(name)
            if normalized and normalized in normalized_text and len(normalized) > best_score:
                best = spot
                best_score = len(normalized)

    return best


def serialize_spot_location(spot: Spot) -> dict:
    return {
        "spot_id": spot.id,
        "name": spot.spot_name,
        "latitude": spot.latitude,
        "longitude": spot.longitude,
        "address": spot.location or "灵山胜境景区内",
    }


def spot_service_actions(spot: Spot, include_navigation: bool = True) -> List[dict]:
    actions = []
    if include_navigation:
        if spot.latitude and spot.longitude:
            actions.append(action(
                "开始导航",
                "open_location",
                "导",
                payload=serialize_spot_location(spot),
            ))
        else:
            actions.append(action(
                "获取位置后导航",
                "request_location",
                "📍",
            ))
    actions.append(action(
        f"查看{spot.spot_name}介绍",
        "navigate_to",
        "介",
        path="/pages/guide/index",
        params={"spot_id": spot.id},
        confidence=0.7,
    ))
    return actions


SPOT_OVERVIEW_WORDS = ["介绍", "讲讲", "是什么", "怎么样", "概况", "简介"]
SPOT_CULTURE_WORDS = ["历史", "文化", "故事", "典故", "由来", "内涵", "寓意"]
SPOT_HIGHLIGHT_WORDS = ["看点", "亮点", "特色", "值得", "好玩", "推荐", "拍照", "打卡", "游览"]
SPOT_OPEN_WORDS = ["开放", "开放时间", "几点开", "几点关", "开门", "关门", "营业", "时间"]
SPOT_LOCATION_WORDS = ["位置", "在哪", "哪里", "交通", "怎么走", "怎么去", "路线", "乘车"]
SCENIC_OPEN_WORDS = ["景区开放", "景区开放时间", "开放时间", "几点开门", "几点开放", "营业时间"]


def compact_text(value: str, max_chars: Optional[int] = None) -> str:
    text = re.sub(r"\s+", " ", value or "").strip(" ，。；")
    if max_chars and len(text) > max_chars:
        text = text[:max_chars].rstrip("，。； ") + "。"
    return text


def spot_question_type(text: str) -> str:
    if contains_any(text, SPOT_OPEN_WORDS):
        return "open"
    if contains_any(text, SPOT_LOCATION_WORDS):
        return "location"
    if contains_any(text, SPOT_CULTURE_WORDS):
        return "culture"
    if contains_any(text, SPOT_HIGHLIGHT_WORDS):
        return "highlight"
    if contains_any(text, SPOT_OVERVIEW_WORDS):
        return "overview"
    return "overview"


def build_spot_direct_answer(spot: Spot, text: str) -> str:
    question_type = spot_question_type(text)
    if question_type == "open":
        content = compact_text(spot.open_info or "")
        if content:
            return f"{spot.spot_name}的开放信息是：{content}。具体以景区当日公告为准。"
        return f"{spot.spot_name}暂无单独开放时间信息，建议以灵山胜境景区当日公告为准。"

    if question_type == "location":
        content = compact_text(spot.location or "")
        if content:
            return f"{spot.spot_name}位于{content}。你可以点击下方按钮导航过去，也可以查看完整介绍。"
        return f"{spot.spot_name}位于灵山胜境景区内。你可以点击下方按钮导航过去，也可以查看完整介绍。"

    if question_type == "culture":
        content = compact_text(spot.culture_connotation or spot.description or "")
        if content:
            return f"{spot.spot_name}的文化看点是：{content}"

    if question_type == "highlight":
        content = compact_text(spot.highlights or spot.description or spot.culture_connotation or "")
        if content:
            return f"{spot.spot_name}值得关注的是：{content}"

    content = compact_text(spot.description or spot.culture_connotation or spot.highlights or "")
    return content or f"{spot.spot_name}是灵山胜境的重要景点，适合结合现场导览慢慢游览。"


def spot_answer_debug(spot: Spot, text: str) -> dict:
    question_type = spot_question_type(text)
    candidates = {
        "open": ["open_info"],
        "location": ["location"],
        "culture": ["culture_connotation", "description"],
        "highlight": ["highlights", "description", "culture_connotation"],
        "overview": ["description", "culture_connotation", "highlights"],
    }.get(question_type, ["description", "culture_connotation", "highlights"])
    used_field = next((field for field in candidates if getattr(spot, field, None)), "")
    return {
        "question_type": question_type,
        "field_candidates": candidates,
        "field_used": used_field,
        "field_has_value": bool(used_field),
    }


def activity_items(db: Session, activity_type: Optional[str] = None) -> List[dict]:
    from app.api.visitor import get_activity_source, serialize_activity

    return [serialize_activity(item) for item in get_activity_source(db, activity_type)]


def upcoming_activity_items(db: Session, limit: int = 8) -> List[dict]:
    now_text = datetime.now().strftime("%H:%M")
    upcoming = []
    for activity in activity_items(db, "performance"):
        for time_text in activity.get("schedule_times", []):
            if time_text >= now_text:
                upcoming.append({**activity, "event_time": time_text})
    upcoming.sort(key=lambda item: (item.get("event_time") or "", item.get("id") or 0))
    return upcoming[:limit]


def infer_pending_service_type_from_history(
    user_id: str,
    db: Optional[Session] = None,
    session_id: Optional[str] = None,
    memory_key: Optional[str] = None,
) -> Optional[str]:
    memory = get_memory(memory_key or conversation_key(user_id, session_id))
    for offset, item in enumerate(reversed(memory)):
        if offset >= PENDING_LOOKBACK_TURNS:
            break
        service_type = item.get("pending_service_type")
        if service_type:
            return service_type

    if not db:
        return None

    query = (
        db.query(VisitorInteraction)
        .filter(VisitorInteraction.visitor_id == user_id)
        .filter(VisitorInteraction.interaction_type == "chat")
    )
    if session_id:
        query = query.filter(VisitorInteraction.session_id == session_id)
    rows = query.order_by(VisitorInteraction.created_at.desc()).limit(3).all()
    for row in rows:
        combined = f"{row.content or ''} {row.reply_text or ''}"
        if contains_any(combined, SERVICE_CENTER_KEYWORDS):
            return "service_center"
        if contains_any(combined, ["观光车", "候车亭", "乘车点", "接驳车", "电瓶车"]):
            return "bus_stop"
        if contains_any(combined, ["售票处", "售票点", "购票处", "票务中心"]):
            return "ticket_office"
        if contains_any(combined, ["医疗", "医务室", "急救", "医生", "红十字"]):
            return "medical"
        if contains_any(combined, ["洗手间", "厕所", "卫生间", "wc"]):
            return "toilet"
        if contains_any(combined, ["停车场", "停车", "停车位"]):
            return "parking"
        if contains_any(combined, ["酒店", "住宿", "住的地方", "宾馆"]):
            return "hotel"
        if contains_any(combined, ["吃", "餐厅", "饭", "素斋", "小吃"]):
            return "food"
    return None


def handle_activities(text: str, db: Session, conditions: dict) -> Optional[OrchestrationResult]:
    if not contains_any(text, ["表演", "演出", "活动", "节目", "禅修", "体验", "几点"]):
        return None

    if conditions["remaining_today"] or conditions["now"]:
        items = upcoming_activity_items(db)
        if not items:
            return OrchestrationResult(True, "今天后面暂时没有查询到未开始的演出场次，请以景区现场公告为准。")
        lines = [f"{item.get('event_time')} {item.get('name')}，地点：{item.get('location') or '以现场为准'}" for item in items]
        reply = "今天接下来还有这些演出：" + "；".join(lines) + "。具体安排以景区现场公告为准。"
        first = items[0]
        actions = []
        if first.get("latitude") and first.get("longitude"):
            actions.append(action(
                "开始导航",
                "open_location",
                "导",
                payload={
                    "name": first.get("name"),
                    "latitude": first.get("latitude"),
                    "longitude": first.get("longitude"),
                    "address": first.get("location") or "",
                },
            ))
        return OrchestrationResult(True, reply, actions)

    activity_type = "zen" if contains_any(text, ["禅修", "体验"]) else "performance"
    items = activity_items(db, activity_type)
    if not items:
        return OrchestrationResult(True, "暂时没有查询到相关活动信息，请以景区当日公告为准。")
    lines = []
    for item in items[:5]:
        times = "、".join(item.get("schedule_times") or []) or "以现场安排为准"
        lines.append(f"{item.get('name')}：{times}，地点：{item.get('location')}")
    label = "禅修体验" if activity_type == "zen" else "演出"
    return OrchestrationResult(True, f"目前可查询到的{label}有：" + "；".join(lines) + "。")


def handle_tickets(text: str, db: Session) -> Optional[OrchestrationResult]:
    if not contains_any(text, ["门票", "票价", "买票", "购票", "观光车票", "多少钱"]):
        return None

    tickets = db.query(TicketProduct).filter(TicketProduct.is_active == True).all()
    if not tickets:
        from app.api.visitor import DEFAULT_TICKET_PRODUCTS

        tickets = DEFAULT_TICKET_PRODUCTS

    lines = []
    for ticket in tickets[:5]:
        if isinstance(ticket, dict):
            name = ticket.get("name")
            price = ticket.get("price")
            notice = ticket.get("official_notice") or ""
        else:
            name = ticket.name
            price = ticket.price
            notice = ticket.official_notice or ""
        price_text = "以公告为准" if price is None else f"{price:g}元"
        lines.append(f"{name}：{price_text}")
    return OrchestrationResult(True, "我查到的票务信息是：" + "；".join(lines) + "。票价和优惠政策请以官方渠道或现场公告为准。")


def handle_scenic_general_info(text: str, db: Session) -> Optional[OrchestrationResult]:
    if resolve_spot(text, db):
        return None
    if not contains_any(text, ["景区开放", "景区开放时间", "开放时间", "景区几点开", "几点开放", "营业时间", "交通方式", "怎么到", "怎么坐车"]):
        return None

    scenic_info = [
        "灵山胜境开放时间通常为7:30-17:30，实际以景区当日公告为准。",
        "如需到达景区，可优先查看景区入口、停车场或观光车信息。",
        "如果你想问的是某个具体景点，我也可以直接按景点名帮你查开放信息、位置和介绍。"
    ]
    return OrchestrationResult(
        True,
        " ".join(scenic_info),
        context={
            "debug_info": {
                "decision_path": "orchestrator_scenic_general",
                "answer_source": "rule",
                "db_used": False,
                "matched_intent": "scenic_general_info"
            }
        }
    )


def handle_spot_navigation_or_guide(text: str, db: Session, states: List[str]) -> Optional[OrchestrationResult]:
    spot = resolve_spot(text, db)
    if not spot:
        return None

    wants_navigation = contains_any(text, ["我想去", "想去", "要去", "导航", "带我", "前往", "找", "迷路"]) or normalize_name(text).startswith("去")
    wants_guide = contains_any(text, ["介绍", "讲讲", "故事", "文化", "历史", "什么", "看点", "开放", "在哪", "哪里", "交通", "怎么走", "怎么去", "位置", "开放时间"])

    if wants_navigation:
        prefix = "别着急，我来帮你定位。" if "lost" in states or "anxious" in states else ""
        actions = spot_service_actions(spot, include_navigation=True)
        reply = f"{prefix}{spot.spot_name}我找到了，下面可以直接导航过去，也可以先看景点介绍。"
        return OrchestrationResult(True, reply, actions, context={
            "pending": "spot_action",
            "spot_id": spot.id,
            "spot_name": spot.spot_name,
            "last_actions": actions,
            "debug_info": {
                "decision_path": "orchestrator_spot_navigation",
                "answer_source": "spot_db",
                "db_used": True,
                "matched_spot": spot.spot_name,
                "spot_id": spot.id,
                "fields_checked": ["latitude", "longitude", "location"],
            },
        })

    if wants_guide:
        content = build_spot_direct_answer(spot, text)
        actions = spot_service_actions(spot, include_navigation=True)
        return OrchestrationResult(
            True,
            content or f"{spot.spot_name}是灵山胜境的重要景点，适合结合现场导览慢慢游览。",
            actions,
            context={
                "pending": "spot_action",
                "spot_id": spot.id,
                "spot_name": spot.spot_name,
                "last_actions": actions,
                "debug_info": {
                    "decision_path": "orchestrator_spot_db",
                    "answer_source": "spot_db",
                    "db_used": True,
                    "matched_spot": spot.spot_name,
                    "spot_id": spot.id,
                    **spot_answer_debug(spot, text),
                    "fields_checked": ["description", "culture_connotation", "highlights", "open_info", "location"],
                },
            },
        )

    answer_text = build_spot_direct_answer(spot, text)
    actions = spot_service_actions(spot, include_navigation=True)
    return OrchestrationResult(
        True,
        answer_text,
        actions,
        context={
            "pending": "spot_action",
            "spot_id": spot.id,
            "spot_name": spot.spot_name,
            "last_actions": actions,
            "debug_info": {
                "decision_path": "orchestrator_spot_db",
                "answer_source": "spot_db",
                "db_used": True,
                "matched_spot": spot.spot_name,
                "spot_id": spot.id,
                **spot_answer_debug(spot, text),
                "fields_checked": ["description", "culture_connotation", "highlights", "open_info", "location"],
            },
        },
    )


def nearby_points_from_spot(db: Session, point_type: Optional[str] = None) -> List[dict]:
    from app.api.visitor import NEARBY_SERVICE_POINTS

    points = NEARBY_SERVICE_POINTS
    if point_type:
        points = [point for point in points if point.get("type") == point_type]
    return points


def resolve_recent_spot(memory_key: str, db: Session) -> Optional[Spot]:
    for offset, item in enumerate(reversed(get_memory(memory_key))):
        if offset >= PENDING_LOOKBACK_TURNS:
            break
        spot_id = item.get("spot_id")
        if spot_id:
            spot = db.query(Spot).filter(Spot.id == spot_id).first()
            if spot:
                return spot
        spot_name = item.get("spot_name")
        if spot_name:
            spot = resolve_spot(spot_name, db)
            if spot:
                return spot
    key_parts = (memory_key or "").split(":", 1)
    if len(key_parts) == 2:
        user_id, session_id = key_parts
        rows = (
            db.query(VisitorInteraction)
            .filter(VisitorInteraction.visitor_id == user_id)
            .filter(VisitorInteraction.session_id == session_id)
            .filter(VisitorInteraction.interaction_type == "chat")
            .order_by(VisitorInteraction.created_at.desc())
            .limit(4)
            .all()
        )
        for row in rows:
            combined = f"{row.content or ''} {row.reply_text or ''}"
            spot = resolve_spot(combined, db)
            if spot:
                return spot
    return None


CONTEXTUAL_SPOT_PRONOUNS = ["它", "这个", "这个景点", "该景点", "这里", "那边", "刚才", "上面", "之前说的"]
EXPLICIT_SCENIC_SCOPE_WORDS = ["景区", "灵山胜境", "整个景区", "全园", "园区"]


def is_contextual_spot_question(text: str, db: Session) -> bool:
    if resolve_spot(text, db):
        return False
    if contains_any(text, EXPLICIT_SCENIC_SCOPE_WORDS):
        return False
    if contains_any(text, ["附近", "周边", "旁边", "路线规划", "推荐路线", "门票", "购票", "演出", "表演"]):
        return False

    spot_info_words = (
        SPOT_OVERVIEW_WORDS
        + SPOT_CULTURE_WORDS
        + SPOT_HIGHLIGHT_WORDS
        + SPOT_OPEN_WORDS
        + SPOT_LOCATION_WORDS
        + ["开放信息", "详细信息", "更多信息"]
    )
    return contains_any(text, CONTEXTUAL_SPOT_PRONOUNS) or contains_any(text, spot_info_words)


def handle_contextual_spot_question(text: str, db: Session, memory_key: str) -> Optional[OrchestrationResult]:
    if not is_contextual_spot_question(text, db):
        return None

    spot = resolve_recent_spot(memory_key, db)
    if not spot:
        return None

    content = build_spot_direct_answer(spot, text)
    actions = spot_service_actions(spot, include_navigation=True)
    return OrchestrationResult(
        True,
        content or f"{spot.spot_name}是灵山胜境的重要景点，适合结合现场导览慢慢游览。",
        actions,
        context={
            "pending": "spot_action",
            "spot_id": spot.id,
            "spot_name": spot.spot_name,
            "last_actions": actions,
            "debug_info": {
                "decision_path": "orchestrator_contextual_spot_db",
                "answer_source": "spot_db",
                "db_used": True,
                "matched_spot": spot.spot_name,
                "spot_id": spot.id,
                "context_resolution": "recent_spot",
                **spot_answer_debug(spot, text),
                "fields_checked": ["description", "culture_connotation", "highlights", "open_info", "location"],
            },
        },
    )


def service_type_from_text(text: str, states: List[str]) -> str:
    if contains_any(text, ["游客中心", "服务中心", "问询处", "咨询台"]):
        return "service_center"
    if contains_any(text, ["观光车", "候车亭", "乘车点", "接驳车", "电瓶车"]):
        return "bus_stop"
    if contains_any(text, ["售票处", "售票点", "购票处", "票务中心"]):
        return "ticket_office"
    if contains_any(text, ["医疗", "医务室", "急救", "医生", "红十字"]):
        return "medical"
    if "hungry" in states or contains_any(text, ["吃", "餐厅", "饭", "素斋", "小吃"]):
        return "food"
    if contains_any(text, ["酒店", "住宿", "住的地方", "宾馆"]):
        return "hotel"
    if contains_any(text, ["停车", "停车场", "停车位"]):
        return "parking"
    if contains_any(text, ["厕所", "洗手间", "卫生间", "wc"]):
        return "toilet"
    return "service"


def resolve_pending_service_type(memory_key: str) -> Optional[str]:
    for offset, item in enumerate(reversed(get_memory(memory_key))):
        if offset >= PENDING_LOOKBACK_TURNS:
            break
        service_type = item.get("pending_service_type")
        if service_type:
            return service_type
    return None


SERVICE_TYPE_LABELS = {
    "food": "餐饮",
    "hotel": "住宿",
    "parking": "停车场",
    "service_center": "游客中心",
    "toilet": "洗手间",
    "bus_stop": "观光车站",
    "ticket_office": "售票处",
    "medical": "医疗点",
    "service": "服务点",
}


NEW_TASK_WORDS = [
    "路线", "行程", "规划", "推荐", "偏好", "适合我", "演出", "表演", "活动", "节目",
    "门票", "票价", "买票", "购票", "介绍", "讲讲", "故事", "历史", "文化", "开放",
    "几点", "今天", "还有", "去过", "足迹", "记录",
]


PURE_CONFIRMATION_WORDS = ["是", "对", "好", "好的", "可以", "行", "嗯", "嗯嗯", "就这个", "就它", "按我的偏好"]


def has_new_explicit_target(text: str, db: Optional[Session] = None) -> bool:
    normalized = normalize_name(text)
    if not normalized:
        return False

    if db and resolve_spot(text, db) is not None:
        return True

    if service_type_from_text(normalized, []) != "service":
        return True

    if contains_any(normalized, NEW_TASK_WORDS):
        return True

    return False


def is_location_followup(text: str, db: Optional[Session] = None) -> bool:
    normalized = normalize_name(text)
    if not normalized or has_new_explicit_target(text, db):
        return False

    direct_location_words = [
        "当前位置", "当前位置附近", "现在位置", "我的位置", "定位", "就在这里", "就在这",
        "在这里", "在这边", "我在这里", "我在这", "这里附近", "这附近", "身边", "我附近",
    ]
    if contains_any(normalized, direct_location_words):
        return True

    if contains_any(normalized, ["我在", "现在在", "目前在", "人在", "位于"]):
        return len(normalized) <= 24 or contains_any(normalized, ["附近", "旁边", "周边"])

    if db and contains_any(normalized, ["附近", "旁边", "周边"]):
        return resolve_spot(text, db) is not None

    return False


def nearby_items_for_type(nearby_result: dict, service_type: str) -> List[dict]:
    if service_type == "food":
        return nearby_result.get("food", [])
    if service_type == "hotel":
        return nearby_result.get("hotel", [])

    services = nearby_result.get("services", [])
    if service_type == "service_center":
        return prioritize_service_center_items([
            item for item in services
            if contains_any(item.get("name", "") + item.get("desc", ""), SERVICE_CENTER_KEYWORDS)
        ])
    if service_type == "toilet":
        return [item for item in services if item.get("type") == "toilet"]
    if service_type == "parking":
        return [item for item in services if item.get("type") == "parking"]
    if service_type in ["ticket_office", "medical", "bus_stop"]:
        return [item for item in services if item.get("type") == service_type]
    return services


def handle_nearby(
    text: str,
    db: Session,
    states: List[str],
    conditions: dict,
    user_location: Optional[dict],
    user_id: str,
    session_id: Optional[str],
    memory_key: str,
) -> Optional[OrchestrationResult]:
    requested_service_type = service_type_from_text(text, states)
    pending_service_type = (
        infer_pending_service_type_from_history(user_id, db, session_id, memory_key)
        if is_location_followup(text, db)
        else None
    )
    service_type = requested_service_type if requested_service_type != "service" else (pending_service_type or requested_service_type)
    is_facility_query = service_type != "service"

    if not conditions["nearby"] and not any(state in states for state in ["hot", "tired", "hungry"]) and not is_facility_query:
        return None

    anchor_spot = resolve_spot(text, db) or resolve_recent_spot(memory_key, db)
    if anchor_spot:
        if service_type != "service":
            from app.api.visitor import find_facilities_near_spot

            items = find_facilities_near_spot(anchor_spot.id, db, service_type, max_distance_km=1.0)
        else:
            from app.api.visitor import get_spot_nearby

            nearby_result = get_spot_nearby(anchor_spot.id, db, max_distance_km=1.0)
            items = nearby_items_for_type(nearby_result, service_type)

        if items:
            service_label = SERVICE_TYPE_LABELS.get(service_type, "服务点")
            lines = [f"{item.get('name')}，{item.get('desc') or f'附近{service_label}'}" for item in items[:3]]
            first = items[0]
            nav_note = f"下方按钮默认导航到{first.get('name')}。" if len(items) > 1 else "你可以点击下方按钮导航过去。"
            actions = [action("开始导航", "open_location", "导", payload={
                "name": first.get("name"),
                "latitude": first.get("latitude"),
                "longitude": first.get("longitude"),
                "address": first.get("desc") or "",
            })]
            return OrchestrationResult(
                True,
                f"我查到{anchor_spot.spot_name}附近的{service_label}有：" + "；".join(lines) + f"。{nav_note}",
                actions,
                context={
                    "pending": "nearby_service",
                    "pending_service_type": service_type,
                    "spot_id": anchor_spot.id,
                    "spot_name": anchor_spot.spot_name,
                    "last_actions": actions,
                },
            )

        return OrchestrationResult(
            True,
            f"抱歉，我暂时没有查到{anchor_spot.spot_name}附近合适的服务点。你也可以打开定位后，我再按你当前坐标查一次。",
            [action("获取当前位置", "request_location", "位")],
            context={"spot_id": anchor_spot.id, "spot_name": anchor_spot.spot_name},
        )

    if is_facility_query and user_location:
        from app.api.visitor import find_facilities_around

        items = find_facilities_around(
            user_location.get("latitude"),
            user_location.get("longitude"),
            service_type,
            radius=1000,
        )
        if items:
            service_label = SERVICE_TYPE_LABELS.get(service_type, "服务点")
            lines = [f"{item.get('name')}，{item.get('desc') or f'附近{service_label}'}" for item in items[:3]]
            first = items[0]
            nav_note = f"下方按钮默认导航到{first.get('name')}。" if len(items) > 1 else "你可以点击下方按钮导航过去。"
            actions = [action("开始导航", "open_location", "导", payload={
                "name": first.get("name"),
                "latitude": first.get("latitude"),
                "longitude": first.get("longitude"),
                "address": first.get("desc") or "",
            })]
            return OrchestrationResult(
                True,
                f"我按你的当前位置查到附近的{service_label}有：" + "；".join(lines) + f"。{nav_note}",
                actions,
                context={
                    "pending": "nearby_service",
                    "pending_service_type": service_type,
                    "last_actions": actions,
                },
            )
        return OrchestrationResult(
            True,
            f"抱歉，我暂时没有查到你附近合适的{SERVICE_TYPE_LABELS.get(service_type, '服务点')}。你也可以告诉我你在哪个景点附近，我再换锚点查一次。",
            [action("获取当前位置", "request_location", "位")],
            context={
                "pending": "nearby_service",
                "pending_service_type": service_type,
            },
        )

    if not user_location:
        ask_text = "可以，我需要先知道你当前位置，或者你告诉我在哪个景点附近，才能更准确地找附近的餐饮、休息点或服务设施。"
        if is_facility_query:
            ask_text = f"可以，我需要先知道你现在在哪个景点附近，或者允许定位，我才能帮你找附近的{SERVICE_TYPE_LABELS.get(service_type, '服务点')}。"
        return OrchestrationResult(
            True,
            ask_text,
            [action("获取当前位置", "request_location", "位")],
            context={
                "pending": "nearby_service",
                "pending_service_type": service_type,
            },
        )

    if "hungry" in states or contains_any(text, ["吃", "餐厅", "饭", "素斋", "小吃"]):
        points = sort_by_user_location(nearby_points_from_spot(db, "food"), user_location)
        if not points:
            return OrchestrationResult(True, "我暂时没有查到附近餐饮点，可以到服务中心咨询现场推荐。")
        lines = [f"{point.get('name')}，{point.get('desc') or '餐饮点'}" for point in points[:3]]
        first = points[0]
        actions = [action("开始导航", "open_location", "导", payload={
            "name": first.get("name"),
            "latitude": first.get("latitude"),
            "longitude": first.get("longitude"),
            "address": first.get("desc") or "",
        })]
        return OrchestrationResult(True, "附近可以考虑：" + "；".join(lines) + "。", actions)

    if contains_any(text, ["游客中心", "服务中心", "问询处", "咨询台"]):
        points = sort_by_user_location(nearby_points_from_spot(db), user_location)
        matched = [
            point for point in points
            if contains_any(point.get("name", "") + point.get("desc", ""), ["游客中心", "服务中心", "接待中心", "问询处", "咨询台"])
        ]
        matched = matched[:3] or points[:3]
        if not matched:
            return OrchestrationResult(
                True,
                "我暂时没有查到附近游客中心。你可以告诉我你现在在哪个景点附近，我再帮你细查。",
                [action("获取当前位置", "request_location", "位")],
            )
        lines = [f"{point.get('name')}，{point.get('desc') or '服务中心'}" for point in matched]
        first = matched[0]
        actions = [action("开始导航", "open_location", "导", payload={
            "name": first.get("name"),
            "latitude": first.get("latitude"),
            "longitude": first.get("longitude"),
            "address": first.get("desc") or "",
        })]
        return OrchestrationResult(True, "我查到附近游客中心有：" + "；".join(lines) + "。", actions)

    if "hot" in states or "tired" in states or contains_any(text, ["避暑", "凉快", "休息", "歇"]):
        candidates = [
            point for point in sort_by_user_location(nearby_points_from_spot(db), user_location)
            if contains_any(point.get("name", "") + point.get("desc", ""), ["服务", "中心", "梵宫", "售票", "餐", "休息", "禅"])
        ][:3]
        if not candidates:
            candidates = sort_by_user_location(nearby_points_from_spot(db), user_location)[:3]
        lines = [f"{point.get('name')}，{point.get('desc') or '可作为临时停留点'}" for point in candidates]
        actions = []
        if candidates:
            first = candidates[0]
            actions.append(action("开始导航", "open_location", "导", payload={
                "name": first.get("name"),
                "latitude": first.get("latitude"),
                "longitude": first.get("longitude"),
                "address": first.get("desc") or "",
            }))
        return OrchestrationResult(True, "天气热的话先别急着赶路，我帮你找了几个附近可停留的地方：" + "；".join(lines) + "。", actions)

    if contains_any(text, ["厕所", "洗手间", "停车", "售票", "母婴", "医疗", "失物"]):
        points = sort_by_user_location(nearby_points_from_spot(db), user_location)
        words = ["厕所", "洗手", "停车", "售票", "母婴", "医疗", "失物"]
        matched = [point for point in points if contains_any(point.get("name", "") + point.get("desc", ""), words)]
        matched = matched[:3] or points[:3]
        lines = [f"{point.get('name')}，{point.get('desc') or '服务点'}" for point in matched]
        return OrchestrationResult(True, "我查到附近服务点有：" + "；".join(lines) + "。")

    return None


def handle_route_request(text: str, conditions: dict) -> Optional[OrchestrationResult]:
    if not conditions["route"] and not conditions["preference"] and not contains_any(text, ["推荐路线", "游览路线"]):
        return None

    reply = "路线需要结合你的游玩偏好、停留时间和必去景点来生成。我建议先进入路线规划选择条件，这样生成结果会比直接口头推荐更可靠。"
    actions = [
        action("去路线规划", "navigate_to", "线", path="/pages/route-planning/index"),
        action("个性化推荐", "navigate_to", "荐", path="/pages/recommendation/index", confidence=0.7),
    ]
    return OrchestrationResult(True, reply, actions, context={"pending": "route_planning"})


def handle_history(text: str, user_id: str, db: Session, conditions: dict) -> Optional[OrchestrationResult]:
    if not conditions["history"] and not contains_any(text, ["我去过", "导航过", "路线历史"]):
        return None

    if contains_any(text, ["路线", "行程"]):
        rows = db.query(RouteHistory).filter(RouteHistory.visitor_id == user_id).order_by(RouteHistory.created_at.desc()).limit(5).all()
        if not rows:
            return OrchestrationResult(True, "我还没有查到你的路线历史。")
        lines = [f"{row.route_name}，约{row.total_duration or 0}分钟，{row.spot_count or 0}个景点" for row in rows]
        return OrchestrationResult(True, "你最近保存或导航过的路线有：" + "；".join(lines) + "。")

    behavior_type = "navigate" if contains_any(text, ["导航", "去过"]) else "view"
    rows = (
        db.query(AppUserBehavior)
        .filter(AppUserBehavior.visitor_id == user_id)
        .filter(AppUserBehavior.behavior_type == behavior_type)
        .order_by(AppUserBehavior.created_at.desc())
        .limit(8)
        .all()
    )
    names = []
    for row in rows:
        name = row.spot_name or row.keyword
        if name and name not in names:
            names.append(name)
    if not names:
        label = "导航" if behavior_type == "navigate" else "游览"
        return OrchestrationResult(True, f"我还没有查到你的{label}记录。")
    label = "导航去过" if behavior_type == "navigate" else "游览过"
    return OrchestrationResult(True, f"你最近{label}这些地方：" + "、".join(names[:6]) + "。")


def is_confirmation_text(text: str, db: Optional[Session] = None) -> bool:
    normalized = normalize_name(text)
    if not normalized or has_new_explicit_target(text, db):
        return False
    if normalized in PURE_CONFIRMATION_WORDS:
        return True
    if contains_any(normalized, ["就这个", "按我的偏好"]):
        return True
    return len(normalized) <= 8 and contains_any(normalized, ["导航", "去", "介绍", "详情"])


def resolve_confirmation(text: str, memory_key: str, db: Session) -> Optional[OrchestrationResult]:
    if not is_confirmation_text(text, db):
        return None
    memory = get_memory(memory_key)
    if not memory:
        return None
    last = memory[-1]
    last_actions = last.get("last_actions") or []

    if last.get("pending") == "spot_action" and last_actions:
        if contains_any(text, ["介绍", "详情"]):
            actions = [item for item in last_actions if item.get("action_type") == "navigate_to"] or last_actions
            return OrchestrationResult(
                True,
                f"好的，我帮你打开{last.get('spot_name') or '这个景点'}的介绍。",
                actions[:1],
                context=last,
            )

        actions = [item for item in last_actions if item.get("action_type") == "open_location"] or last_actions
        return OrchestrationResult(
            True,
            f"好的，我继续帮你处理{last.get('spot_name') or '这个景点'}。",
            actions[:1],
            context=last,
        )

    if last.get("pending") == "route_planning":
        return OrchestrationResult(
            True,
            "好的，那我建议进入路线规划页选择偏好和时间，我会根据这些条件生成更可靠的路线。",
            [action("去路线规划", "navigate_to", "线", path="/pages/route-planning/index")],
        )
    return None


async def orchestrate_chat(
    text: str,
    user_id: str,
    db: Session,
    emotion_result: Optional[dict] = None,
    user_location: Optional[dict] = None,
    session_id: Optional[str] = None,
) -> OrchestrationResult:
    user_id = user_id or "guest"
    memory_key = conversation_key(user_id, session_id)
    text = (text or "").strip()
    states = detect_user_states(text)
    conditions = detect_conditions(text)

    handlers = [
        lambda: resolve_confirmation(text, memory_key, db),
        lambda: handle_activities(text, db, conditions),
        lambda: handle_tickets(text, db),
        lambda: handle_contextual_spot_question(text, db, memory_key),
        lambda: handle_scenic_general_info(text, db),
        lambda: handle_history(text, user_id, db, conditions),
        lambda: handle_route_request(text, conditions),
        lambda: handle_nearby(text, db, states, conditions, user_location, user_id, session_id, memory_key),
        lambda: handle_spot_navigation_or_guide(text, db, states),
    ]

    for handler in handlers:
        result = handler()
        if result and result.handled:
            remember(memory_key, {
                "text": text,
                "states": states,
                "conditions": conditions,
                **result.context,
            })
            return result

    remember(memory_key, {"text": text, "states": states, "conditions": conditions})
    return OrchestrationResult(False, context={"states": states, "conditions": conditions})
