from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, Float, Date, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base

class Knowledge(Base):
    __tablename__ = "knowledge"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class DigitalHumanConfig(Base):
    __tablename__ = "digital_human_config"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    model = Column(String(100))
    voice = Column(String(100))
    clothes = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class TicketProduct(Base):
    __tablename__ = "ticket_products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    ticket_type = Column(String(50), index=True, default="scenic_ticket")
    audience = Column(String(100), default="成人")
    price = Column(Float, nullable=False, default=0)
    official_notice = Column(Text)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ScenicActivity(Base):
    __tablename__ = "scenic_activities"

    id = Column(Integer, primary_key=True, index=True)
    activity_type = Column(String(50), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    schedule_times = Column(Text)
    duration_minutes = Column(Integer)
    content = Column(Text)
    significance = Column(Text)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class VisitorInteraction(Base):
    __tablename__ = "visitor_interaction"
    id = Column(Integer, primary_key=True, index=True)
    visitor_id = Column(String(100), index=True)
    session_id = Column(String(100), index=True)
    interaction_type = Column(String(50))
    content = Column(Text)
    reply_text = Column(Text)
    emotion = Column(String(50))
    satisfaction_score = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class VisitorFeedback(Base):
    __tablename__ = "visitor_feedback"
    id = Column(Integer, primary_key=True, index=True)
    visitor_id = Column(String(100), index=True)
    session_id = Column(String(100), index=True)
    feedback_type = Column(String(50), index=True)
    target_type = Column(String(50), index=True)
    target_id = Column(String(100))
    target_name = Column(String(255))
    source = Column(String(100))
    tags = Column(Text)
    comment = Column(Text)
    satisfaction_score = Column(Float)
    emotion = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class RouteHistory(Base):
    __tablename__ = "route_history"
    id = Column(Integer, primary_key=True, index=True)
    visitor_id = Column(String(100), index=True)
    route_name = Column(String(255), nullable=False)
    route_type = Column(String(100), index=True)
    route_data = Column(Text, nullable=False)
    total_duration = Column(Integer)
    total_distance = Column(Integer)
    spot_count = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class RouteShare(Base):
    __tablename__ = "route_share"
    __table_args__ = (
        UniqueConstraint("share_id", name="uq_route_share_share_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    share_id = Column(String(64), nullable=False, index=True)
    route_name = Column(String(255), nullable=False)
    route_data = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class RouteDistanceCache(Base):
    __tablename__ = "route_distance_cache"

    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(String(255), unique=True, index=True, nullable=False)
    origin_id = Column(Integer, nullable=True)
    destination_id = Column(Integer, nullable=True)
    origin_lng = Column(Float, nullable=False)
    origin_lat = Column(Float, nullable=False)
    destination_lng = Column(Float, nullable=False)
    destination_lat = Column(Float, nullable=False)
    travel_mode = Column(String(50), default="walking", index=True)
    provider = Column(String(50), default="amap", index=True)
    distance_m = Column(Integer, nullable=False)
    duration_sec = Column(Integer, nullable=False)
    raw_data = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class VisitorBehavior(Base):
    __tablename__ = "visitor_behavior"

    id = Column(Integer, primary_key=True, index=True)
    visitor_id = Column(String(50), index=True)         
    age = Column(Integer)                                  
    gender = Column(String(10))                        
    attraction_name = Column(String(255))                 
    attraction_content = Column(Text)                      
    attraction_type = Column(String(100))                  
    visit_date = Column(Date)                            
    stay_duration = Column(Float)                      
    ticket_cost = Column(Float)                        
    food_cost = Column(Float)                          
    shopping_cost = Column(Float)                      
    transport_cost = Column(Float)                       
    entertainment_cost = Column(Float)                    
    total_cost = Column(Float)                           
    group_size = Column(Integer)                           
    satisfaction = Column(Integer)                         
    created_at = Column(DateTime, server_default=func.now())

class Spot(Base):
    __tablename__ = "spots"

    id = Column(Integer, primary_key=True, index=True)
    scenic_area_name = Column(String(255), nullable=False)
    spot_name = Column(String(255), nullable=False)
    location = Column(String(255))
    latitude = Column(Float)  
    longitude = Column(Float) 
    architecture_params = Column(Text)
    core_function = Column(Text)
    culture_connotation = Column(Text)
    description = Column(Text)
    highlights = Column(Text)
    open_info = Column(Text)
    remark = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class SpotGuideAsset(Base):
    __tablename__ = "spot_guide_assets"
    __table_args__ = (
        UniqueConstraint("spot_id", "style", "voice", name="uq_spot_guide_assets_spot_style_voice"),
    )

    id = Column(Integer, primary_key=True, index=True)
    spot_id = Column(Integer, nullable=False, index=True)
    style = Column(String(50), nullable=False, default="standard", index=True)
    voice = Column(String(50), nullable=False, default="female", index=True)
    script_text = Column(Text, nullable=False)
    audio_url = Column(String(500))
    audio_path = Column(String(500))
    source_hash = Column(String(64), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="ready", index=True)
    error_message = Column(Text)
    duration_seconds = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class SpotNearbyCache(Base):
    __tablename__ = "spot_nearby_cache"
    __table_args__ = (
        UniqueConstraint("cache_key", name="uq_spot_nearby_cache_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(String(255), nullable=False, unique=True, index=True)
    spot_id = Column(Integer, nullable=False, index=True)
    scenic_area_name = Column(String(255), index=True)
    center_lat = Column(Float, nullable=False)
    center_lon = Column(Float, nullable=False)
    radius_km = Column(Float, nullable=False, default=1.0)
    payload_json = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="ready", index=True)
    source = Column(String(50), nullable=False, default="local", index=True)
    error_message = Column(Text)
    refreshed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class SpotVisitMeta(Base):
    __tablename__ = "spot_visit_meta"
    id = Column(Integer, primary_key=True, index=True)
    spot_id = Column(Integer, unique=True, nullable=False)
    official_order = Column(Integer, default=999)
    suggested_stay_minutes = Column(Integer, default=25)
    is_must_see = Column(Boolean, default=False)
    is_rest_area = Column(Boolean, default=False)
    is_accessible = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class SpotTag(Base):
    __tablename__ = "spot_tags"
    id = Column(Integer, primary_key=True, index=True)
    spot_id = Column(Integer, nullable=False)
    tag = Column(String(50), nullable=False)
    score = Column(Integer, default=10)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AppUserBehavior(Base):
    __tablename__ = "app_user_behavior"
    
    id = Column(Integer, primary_key=True, index=True)
    visitor_id = Column(String(100), index=True)
    behavior_type = Column(String(50), index=True)
    spot_id = Column(Integer, index=True)
    spot_name = Column(String(255))
    keyword = Column(String(255))
    duration = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SystemLog(Base):
    __tablename__ = "system_logs"
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(20))
    message = Column(Text)
    source = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
