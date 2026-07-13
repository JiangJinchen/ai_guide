from sqlalchemy.orm import Session
from app.models import Spot, ScenicActivity, TicketProduct

ACTION_PATTERNS = {
    "navigation": {
        "keywords": ["去", "到", "怎么走", "带我去", "导航", "位置", "在哪", "找", "前往"],
        "name": "导航",
        "icon": "🧭"
    },
    "guide": {
        "keywords": ["介绍", "讲讲", "有什么故事", "故事", "文化", "历史", "讲解", "什么", "怎么样"],
        "name": "查看介绍",
        "icon": "📖"
    },
    "ticket": {
        "keywords": ["门票", "多少钱", "买票", "票价", "票", "价格", "购票", "预订"],
        "name": "购票",
        "icon": "🎫"
    },
    "route": {
        "keywords": ["推荐路线", "游览路线", "路线规划", "行程安排"],
        "name": "路线规划",
        "icon": "🗺️"
    },
    "nearby": {
        "keywords": ["附近", "周边", "离我近", "周边景点", "周边设施"],
        "name": "附近景点",
        "icon": "📍"
    },
    "activity": {
        "keywords": ["几点", "演出", "表演", "活动", "时间", "节目", "禅修", "体验"],
        "name": "活动",
        "icon": "🎭"
    },
    "recommendation": {
        "keywords": ["推荐", "偏好", "喜欢", "感兴趣", "适合我", "个性化", "猜你喜欢"],
        "name": "个性化推荐",
        "icon": "⭐"
    },
    "profile": {
        "keywords": ["我的", "收藏", "足迹", "偏好设置", "个人中心", "账号", "信息"],
        "name": "个人中心",
        "icon": "👤"
    },
    "feedback": {
        "keywords": ["评价", "反馈", "建议", "意见", "投诉", "服务评价"],
        "name": "服务评价",
        "icon": "📝"
    }
}

SERVICE_ROUTES = {
    "navigation": {
        "path": "/pages/route-navigation/index",
        "button_name": "开始导航"
    },
    "guide": {
        "path": "/pages/guide/index",
        "button_name": "查看介绍"
    },
    "ticket": {
        "path": "/pages/ticket-assistant/index",
        "button_name": "立即购票"
    },
    "route": {
        "path": "/pages/route-planning/index",
        "button_name": "路线规划"
    },
    "nearby": {
        "path": "/pages/nearby-spots/index",
        "button_name": "附近景点"
    },
    "activity": {
        "path": "/pages/activity-service/index",
        "button_name": "活动安排"
    },
    "recommendation": {
        "path": "/pages/recommendation/index",
        "button_name": "个性化推荐"
    },
    "profile": {
        "path": "/pages/profile/index",
        "button_name": "个人中心"
    },
    "feedback": {
        "path": "/pages/feedback/index",
        "button_name": "服务评价"
    }
}

class EntityRecognitionResult:
    def __init__(self, entity_type: str, entity_id: int, entity_name: str, confidence: float = 0.0):
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.entity_name = entity_name
        self.confidence = confidence
        self.latitude = None
        self.longitude = None

class ActionRecognitionResult:
    def __init__(self, action: str, confidence: float = 0.0):
        self.action = action
        self.confidence = confidence

class IntentResult:
    def __init__(self):
        self.entities = []
        self.actions = []
        self.service_actions = []
        self.overall_confidence = 0.0
        self.should_ask = False
        self.ask_text = ""
        self.facility_type = None
        self.facility_name = ""

FACILITY_TYPE_MAPPING = {
    "toilet": {
        "keywords": ["洗手间", "厕所", "卫生间", "wc", "洗手间在哪", "卫生间在哪"],
        "name": "洗手间",
        "icon": "🚻"
    },
    "parking": {
        "keywords": ["停车场", "停车", "停车场在哪", "哪里停车", "停车位"],
        "name": "停车场",
        "icon": "🅿️"
    },
    "food": {
        "keywords": ["吃饭", "餐厅", "餐饮", "美食", "食堂", "饭店", "吃东西"],
        "name": "餐饮",
        "icon": "🍽️"
    },
    "hotel": {
        "keywords": ["住宿", "酒店", "旅馆", "宾馆", "住的地方"],
        "name": "住宿",
        "icon": "🏨"
    },
    "service_center": {
        "keywords": ["服务中心", "问询处", "咨询台"],
        "name": "服务中心",
        "icon": "ℹ️"
    },
    "bus_stop": {
        "keywords": ["观光车", "候车亭", "乘车点", "接驳车", "电瓶车"],
        "name": "观光车",
        "icon": "🚌"
    },
    "ticket_office": {
        "keywords": ["售票处", "售票点", "购票处"],
        "name": "售票处",
        "icon": "🎫"
    },
    "medical": {
        "keywords": ["医疗", "医务室", "急救", "医生"],
        "name": "医疗点",
        "icon": "🏥"
    }
}

SPECIAL_ENTITIES = {
    "游客中心": {
        "entity_type": "entrance",
        "entity_id": 0,
        "entity_name": "灵山胜境游客中心",
        "latitude": 31.42892,
        "longitude": 120.09487
    },
    "停车场": {
        "entity_type": "parking",
        "entity_id": 1,
        "entity_name": "灵山胜境停车场",
        "latitude": 31.42850,
        "longitude": 120.09350
    },
    "出口": {
        "entity_type": "exit",
        "entity_id": 2,
        "entity_name": "灵山胜境出口",
        "latitude": 31.43100,
        "longitude": 120.10300
    }
}

def recognize_entities(text: str, db: Session) -> list:
    results = []
    
    text_lower = text
    
    for keyword, entity_info in SPECIAL_ENTITIES.items():
        if keyword in text_lower:
            confidence = len(keyword) / len(text_lower) if text_lower else 0
            entity = EntityRecognitionResult(
                entity_type=entity_info["entity_type"],
                entity_id=entity_info["entity_id"],
                entity_name=entity_info["entity_name"],
                confidence=min(confidence * 1.5, 1.0)
            )
            entity.latitude = entity_info.get("latitude")
            entity.longitude = entity_info.get("longitude")
            results.append(entity)
    
    spots = db.query(Spot).all()
    for spot in spots:
        spot_name = spot.spot_name
        if spot_name in text_lower:
            confidence = len(spot_name) / len(text_lower) if text_lower else 0
            entity = EntityRecognitionResult(
                entity_type="spot",
                entity_id=spot.id,
                entity_name=spot_name,
                confidence=min(confidence * 1.5, 1.0)
            )
            entity.latitude = spot.latitude
            entity.longitude = spot.longitude
            results.append(entity)
    
    activities = db.query(ScenicActivity).filter(ScenicActivity.is_active == True).all()
    for activity in activities:
        activity_name = activity.name
        if activity_name in text_lower:
            confidence = len(activity_name) / len(text_lower) if text_lower else 0
            entity = EntityRecognitionResult(
                entity_type="activity",
                entity_id=activity.id,
                entity_name=activity_name,
                confidence=min(confidence * 1.5, 1.0)
            )
            entity.latitude = activity.latitude
            entity.longitude = activity.longitude
            results.append(entity)
    
    tickets = db.query(TicketProduct).filter(TicketProduct.is_active == True).all()
    for ticket in tickets:
        ticket_name = ticket.name
        if ticket_name in text_lower:
            confidence = len(ticket_name) / len(text_lower) if text_lower else 0
            results.append(EntityRecognitionResult(
                entity_type="ticket",
                entity_id=ticket.id,
                entity_name=ticket_name,
                confidence=min(confidence * 1.5, 1.0)
            ))
    
    results.sort(key=lambda x: x.confidence, reverse=True)
    return results

def recognize_actions(text: str) -> list:
    results = []
    text_lower = text
    
    for action, config in ACTION_PATTERNS.items():
        for keyword in config["keywords"]:
            if keyword in text_lower:
                confidence = len(keyword) / len(text_lower) if text_lower else 0
                results.append(ActionRecognitionResult(
                    action=action,
                    confidence=min(confidence * 1.2, 1.0)
                ))
    
    results.sort(key=lambda x: x.confidence, reverse=True)
    return results


def recognize_facility_intent(text: str) -> tuple:
    text_lower = text
    
    for facility_type, config in FACILITY_TYPE_MAPPING.items():
        for keyword in config["keywords"]:
            if keyword in text_lower:
                confidence = len(keyword) / len(text_lower) if text_lower else 0
                return (facility_type, config["name"], min(confidence * 1.5, 1.0))
    
    return (None, "", 0.0)

ACTIONS_REQUIRING_ENTITY = ["navigation", "guide", "ticket"]

def route_service(entities: list, actions: list) -> list:
    service_actions = []
    
    if not entities and not actions:
        return service_actions
    
    for action in actions[:3]:
        route_info = SERVICE_ROUTES.get(action.action)
        if not route_info:
            continue
        
        if action.action in ACTIONS_REQUIRING_ENTITY and not entities:
            continue
        
        params = {}
        
        for entity in entities[:1]:
            if entity.entity_type == "spot":
                params["spot_id"] = entity.entity_id
                params["spot_name"] = entity.entity_name
                if entity.latitude:
                    params["latitude"] = entity.latitude
                    params["longitude"] = entity.longitude
            elif entity.entity_type == "activity":
                params["activity_id"] = entity.entity_id
                params["activity_name"] = entity.entity_name
                if entity.latitude:
                    params["latitude"] = entity.latitude
                    params["longitude"] = entity.longitude
            elif entity.entity_type == "ticket":
                params["ticket_id"] = entity.entity_id
                params["ticket_name"] = entity.entity_name
            elif entity.entity_type == "entrance":
                params["entity_type"] = "entrance"
                params["entity_name"] = entity.entity_name
                if entity.latitude:
                    params["latitude"] = entity.latitude
                    params["longitude"] = entity.longitude
            elif entity.entity_type in ["parking", "exit"]:
                params["entity_type"] = entity.entity_type
                params["entity_name"] = entity.entity_name
                if entity.latitude:
                    params["latitude"] = entity.latitude
                    params["longitude"] = entity.longitude
        
        if action.action == "navigation":
            if params.get("latitude") and params.get("longitude"):
                service_actions.append({
                    "name": route_info["button_name"],
                    "icon": ACTION_PATTERNS[action.action]["icon"],
                    "action_type": "open_location",
                    "payload": {
                        "latitude": params["latitude"],
                        "longitude": params["longitude"],
                        "name": params.get("entity_name") or params.get("spot_name") or "目的地",
                        "address": ""
                    }
                })
            else:
                service_actions.append({
                    "name": "获取位置后导航",
                    "icon": "📍",
                    "action_type": "request_location"
                })
    
    return service_actions

def calculate_overall_confidence(entities: list, actions: list) -> float:
    if not entities and not actions:
        return 0.0
    
    entity_confidence = entities[0].confidence if entities else 0.0
    action_confidence = actions[0].confidence if actions else 0.0
    
    if entities and actions:
        return (entity_confidence + action_confidence) / 2
    elif entities:
        return entity_confidence * 0.5
    elif actions:
        return action_confidence * 0.5
    return 0.0

def generate_ask_text(entities: list, actions: list) -> str:
    entity_names = [e.entity_name for e in entities[:2]]
    action_names = [ACTION_PATTERNS[a.action]["name"] for a in actions[:3]]
    
    if entity_names and action_names:
        if len(entity_names) == 1:
            if len(action_names) == 1:
                return f"你是想对{entity_names[0]}进行{action_names[0]}吗？"
            else:
                action_options = "、".join(action_names)
                return f"你是想对{entity_names[0]}{action_options}？"
        else:
            entity_options = "、".join(entity_names)
            action_options = "、".join(action_names)
            return f"你是想对{entity_options}进行{action_options}？"
    elif entity_names:
        entity_options = "、".join(entity_names)
        return f"你是想了解{entity_options}吗？"
    elif action_names:
        action_options = "、".join(action_names)
        if any(a.action in ACTIONS_REQUIRING_ENTITY for a in actions[:3]):
            return f"你是想{action_options}吗？请告诉我具体是哪个景点或活动。"
        else:
            return f"你是想{action_options}吗？"
    else:
        return "请问你需要什么帮助？"

def route(text: str, db: Session) -> IntentResult:
    result = IntentResult()
    
    result.entities = recognize_entities(text, db)
    result.actions = recognize_actions(text)
    
    facility_type, facility_name, facility_confidence = recognize_facility_intent(text)
    result.facility_type = facility_type
    result.facility_name = facility_name
    
    has_location_entity = any(e.entity_type == "spot" for e in result.entities)
    
    if facility_type and not has_location_entity and facility_confidence >= 0.3:
        result.should_ask = True
        result.ask_text = f"请问你现在在哪个景点附近呢？我可以帮你找附近的{facility_name}。"
        result.overall_confidence = facility_confidence
        result.service_actions = []
        
        print(f"[IntentRouter] 设施意图识别:")
        print(f"  - 设施类型: {facility_type}")
        print(f"  - 设施名称: {facility_name}")
        print(f"  - 置信度: {facility_confidence}")
        print(f"  - 需要追问位置")
        
        return result
    
    result.service_actions = route_service(result.entities, result.actions)
    result.overall_confidence = calculate_overall_confidence(result.entities, result.actions)
    
    if result.overall_confidence < 0.45:
        result.should_ask = True
        result.ask_text = generate_ask_text(result.entities, result.actions)
        result.service_actions = []
    elif 0.45 <= result.overall_confidence < 0.75:
        result.service_actions = result.service_actions[:3]
    else:
        result.service_actions = result.service_actions[:1]
    
    print(f"[IntentRouter] 意图识别结果:")
    print(f"  - 实体: {[(e.entity_type, e.entity_name, e.confidence) for e in result.entities]}")
    print(f"  - 动作: {[(a.action, a.confidence) for a in result.actions]}")
    print(f"  - 服务动作: {[sa['name'] for sa in result.service_actions]}")
    print(f"  - 总置信度: {result.overall_confidence}")
    print(f"  - 是否追问: {result.should_ask}")
    
    return result