from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional

# ======================
# 知识库
# ======================
class KnowledgeBase(BaseModel):
    title: str
    content: str
    category: Optional[str] = None

class KnowledgeCreate(KnowledgeBase):
    pass

class KnowledgeUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None

class KnowledgeResponse(KnowledgeBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# ======================
# 数字人配置
# ======================
class DigitalHumanConfigBase(BaseModel):
    name: str
    model: Optional[str] = None
    voice: Optional[str] = None
    clothes: Optional[str] = None
    is_active: bool = True

class DigitalHumanConfigCreate(DigitalHumanConfigBase):
    pass

class DigitalHumanConfigUpdate(BaseModel):
    name: Optional[str] = None
    model: Optional[str] = None
    voice: Optional[str] = None
    clothes: Optional[str] = None
    is_active: Optional[bool] = None

class DigitalHumanConfigResponse(DigitalHumanConfigBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# ======================
# 游客交互
# ======================
class VisitorInteractionBase(BaseModel):
    visitor_id: str
    session_id: Optional[str] = None
    interaction_type: Optional[str] = None
    content: Optional[str] = None
    emotion: Optional[str] = None
    satisfaction_score: Optional[float] = None

class VisitorInteractionCreate(VisitorInteractionBase):
    pass

class VisitorInteractionResponse(VisitorInteractionBase):
    id: int
    reply_text: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# ======================
# 游客反馈
# ======================
class VisitorFeedbackBase(BaseModel):
    visitor_id: str
    session_id: Optional[str] = None
    feedback_type: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    target_name: Optional[str] = None
    source: Optional[str] = None
    tags: Optional[str] = None
    comment: Optional[str] = None
    satisfaction_score: Optional[float] = None
    emotion: Optional[str] = None

class VisitorFeedbackCreate(VisitorFeedbackBase):
    pass

class VisitorFeedbackResponse(VisitorFeedbackBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ChatSessionResponse(BaseModel):
    session_id: str
    title: str
    preview: str
    turn_count: int
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    latest_message_at: Optional[datetime] = None

class VisitorBehaviorBase(BaseModel):
    visitor_id: str
    age: int | None = None
    gender: str | None = None
    attraction_name: str | None = None
    attraction_type: str | None = None
    satisfaction: int | None = None

class VisitorBehaviorCreate(VisitorBehaviorBase):
    pass

class VisitorBehaviorResponse(VisitorBehaviorBase):
    id: int
    visit_date: date | None = None
    total_cost: float | None = None
    stay_duration: float | None = None

    class Config:
        from_attributes = True

# ======================
# 景点 
# ======================
class SpotBase(BaseModel):
    scenic_area_name: str          # 景区名称
    spot_name: str                 # 景点名称
    location: Optional[str] = None
    latitude: Optional[float] = None 
    longitude: Optional[float] = None 
    architecture_params: Optional[str] = None
    core_function: Optional[str] = None
    culture_connotation: Optional[str] = None
    description: Optional[str] = None
    highlights: Optional[str] = None
    open_info: Optional[str] = None
    remark: Optional[str] = None

class SpotCreate(SpotBase):
    pass

class SpotUpdate(BaseModel):
    scenic_area_name: Optional[str] = None
    spot_name: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    architecture_params: Optional[str] = None
    core_function: Optional[str] = None
    culture_connotation: Optional[str] = None
    description: Optional[str] = None
    highlights: Optional[str] = None
    open_info: Optional[str] = None
    remark: Optional[str] = None

class SpotResponse(SpotBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# ======================
# 系统日志
# ======================
class SystemLogBase(BaseModel):
    level: str
    message: str
    source: Optional[str] = None

class SystemLogCreate(SystemLogBase):
    pass

class SystemLogResponse(SystemLogBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
