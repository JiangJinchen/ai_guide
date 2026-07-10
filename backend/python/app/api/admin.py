from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Knowledge, DigitalHumanConfig, VisitorInteraction, SystemLog, TicketProduct, ScenicActivity
from datetime import datetime
import json
import re

router = APIRouter()

class KnowledgeItem(BaseModel):
    title: str
    content: str
    category: str

class DigitalHumanConfigItem(BaseModel):
    name: str
    model: str
    voice: str
    clothes: str
    is_active: Optional[bool] = True 

class KnowledgeItemUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    category: str | None = None

class DigitalHumanConfigUpdate(BaseModel):
    name: str | None = None
    model: str | None = None
    voice: str | None = None
    clothes: str | None = None
    is_active: bool | None = None

class TicketProductItem(BaseModel):
    name: str
    ticket_type: str = "scenic_ticket"
    audience: str = "成人"
    price: float = 0
    official_notice: str | None = None
    is_active: bool = True

class TicketProductUpdate(BaseModel):
    name: str | None = None
    ticket_type: str | None = None
    audience: str | None = None
    price: float | None = None
    official_notice: str | None = None
    is_active: bool | None = None

class ScenicActivityItem(BaseModel):
    activity_type: str
    name: str
    location: str
    latitude: float | None = None
    longitude: float | None = None
    schedule_times: str | None = None
    duration_minutes: int | None = None
    content: str | None = None
    significance: str | None = None
    is_active: bool = True

class ScenicActivityUpdate(BaseModel):
    activity_type: str | None = None
    name: str | None = None
    location: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    schedule_times: str | None = None
    duration_minutes: int | None = None
    content: str | None = None
    significance: str | None = None
    is_active: bool | None = None

def validate_activity_type(activity_type: str):
    if activity_type not in {"performance", "zen"}:
        raise HTTPException(status_code=400, detail="活动类型只能是 performance（演出）或 zen（禅修体验）")

def normalize_activity_schedule(value: str | None):
    if not value:
        return None
    times = []
    for item in re.split(r"[,，、\s]+", value):
        text = item.strip()
        if not text:
            continue
        if not re.match(r"^\d{1,2}:\d{2}$", text):
            raise HTTPException(status_code=400, detail="演出时间格式请使用 HH:MM，多个时间用逗号分隔")
        hour, minute = text.split(":")
        times.append(f"{int(hour):02d}:{minute}")
    return json.dumps(sorted(set(times)), ensure_ascii=False)

@router.post("/knowledge")
async def create_knowledge(item: KnowledgeItem, db: Session = Depends(get_db)):
    try:
        new_knowledge = Knowledge(
            title=item.title,
            content=item.content,
            category=item.category
        )
        db.add(new_knowledge)
        db.commit()
        db.refresh(new_knowledge)
        return {"message": "知识库条目创建成功", "item": new_knowledge}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")

@router.get("/knowledge")
async def get_knowledge(category: str = None, db: Session = Depends(get_db)):
    try:
        query = db.query(Knowledge)
        if category:
            query = query.filter(Knowledge.category == category)
        items = query.all()
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

@router.put("/knowledge/{item_id}")
async def update_knowledge(item_id: int, item: KnowledgeItemUpdate, db: Session = Depends(get_db)):
    try:
        knowledge = db.query(Knowledge).filter(Knowledge.id == item_id).first()
        if not knowledge:
            raise HTTPException(status_code=404, detail="知识库条目不存在")

        if item.title is not None:
            knowledge.title = item.title
        if item.content is not None:
            knowledge.content = item.content
        if item.category is not None:
            knowledge.category = item.category

        db.commit()
        db.refresh(knowledge)
        return {"message": "知识库条目更新成功", "item": knowledge}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")

@router.delete("/knowledge/{item_id}")
async def delete_knowledge(item_id: int, db: Session = Depends(get_db)):
    try:
        knowledge = db.query(Knowledge).filter(Knowledge.id == item_id).first()
        if not knowledge:
            raise HTTPException(status_code=404, detail="知识库条目不存在")
        db.delete(knowledge)
        db.commit()
        return {"message": "知识库条目删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@router.post("/digital-human")
async def create_digital_human_config(config: DigitalHumanConfigItem, db: Session = Depends(get_db)):
    try:
        new_config = DigitalHumanConfig(
            name=config.name,
            model=config.model,
            voice=config.voice,
            clothes=config.clothes,
            is_active=config.is_active
        )
        db.add(new_config)
        db.commit()
        db.refresh(new_config)
        return {"message": "数字人配置创建成功", "config": new_config}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")

@router.get("/digital-human")
async def get_digital_human_configs(db: Session = Depends(get_db)):
    try:
        configs = db.query(DigitalHumanConfig).all()
        return {"configs": configs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

@router.put("/digital-human/{config_id}")
async def update_digital_human_config(config_id: int, config: DigitalHumanConfigUpdate, db: Session = Depends(get_db)):
    try:
        existing_config = db.query(DigitalHumanConfig).filter(DigitalHumanConfig.id == config_id).first()
        if not existing_config:
            raise HTTPException(status_code=404, detail="数字人配置不存在")
        existing_config.name = config.name
        existing_config.model = config.model
        existing_config.voice = config.voice
        existing_config.clothes = config.clothes
        db.commit()
        db.refresh(existing_config)
        return {"message": "数字人配置更新成功", "config": existing_config}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")

@router.delete("/digital-human/{config_id}")
async def delete_digital_human_config(config_id: int, db: Session = Depends(get_db)):
    try:
        existing_config = db.query(DigitalHumanConfig).filter(DigitalHumanConfig.id == config_id).first()
        if not existing_config:
            raise HTTPException(status_code=404, detail="数字人配置不存在")
        db.delete(existing_config)
        db.commit()
        return {"message": "数字人配置删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@router.get("/tickets")
async def get_ticket_products(db: Session = Depends(get_db), ticket_type: str = None, include_inactive: bool = True):
    try:
        query = db.query(TicketProduct)
        if ticket_type:
            query = query.filter(TicketProduct.ticket_type == ticket_type)
        if not include_inactive:
            query = query.filter(TicketProduct.is_active == True)
        items = query.order_by(TicketProduct.sort_order.asc(), TicketProduct.id.asc()).all()
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询票务信息失败: {str(e)}")

@router.post("/tickets")
async def create_ticket_product(item: TicketProductItem, db: Session = Depends(get_db)):
    try:
        ticket = TicketProduct(**item.model_dump())
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        return {"message": "票务信息已创建", "item": ticket}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建票务信息失败: {str(e)}")

@router.put("/tickets/{ticket_id}")
async def update_ticket_product(ticket_id: int, item: TicketProductUpdate, db: Session = Depends(get_db)):
    try:
        ticket = db.query(TicketProduct).filter(TicketProduct.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="票务信息不存在")

        updates = item.model_dump(exclude_unset=True)
        for key, value in updates.items():
            setattr(ticket, key, value)

        db.commit()
        db.refresh(ticket)
        return {"message": "票务信息已更新", "item": ticket}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新票务信息失败: {str(e)}")

@router.delete("/tickets/{ticket_id}")
async def delete_ticket_product(ticket_id: int, db: Session = Depends(get_db)):
    try:
        ticket = db.query(TicketProduct).filter(TicketProduct.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="票务信息不存在")
        db.delete(ticket)
        db.commit()
        return {"message": "票务信息已删除"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除票务信息失败: {str(e)}")

@router.get("/activities")
async def get_scenic_activities(db: Session = Depends(get_db), activity_type: str = None, include_inactive: bool = True):
    try:
        query = db.query(ScenicActivity)
        if activity_type:
            query = query.filter(ScenicActivity.activity_type == activity_type)
        if not include_inactive:
            query = query.filter(ScenicActivity.is_active == True)
        items = query.order_by(ScenicActivity.id.asc()).all()
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询活动信息失败: {str(e)}")

@router.post("/activities")
async def create_scenic_activity(item: ScenicActivityItem, db: Session = Depends(get_db)):
    try:
        validate_activity_type(item.activity_type)
        payload = item.model_dump()
        payload["schedule_times"] = normalize_activity_schedule(item.schedule_times)
        activity = ScenicActivity(**payload)
        db.add(activity)
        db.commit()
        db.refresh(activity)
        return {"message": "活动信息已创建", "item": activity}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建活动信息失败: {str(e)}")

@router.put("/activities/{activity_id}")
async def update_scenic_activity(activity_id: int, item: ScenicActivityUpdate, db: Session = Depends(get_db)):
    try:
        activity = db.query(ScenicActivity).filter(ScenicActivity.id == activity_id).first()
        if not activity:
            raise HTTPException(status_code=404, detail="活动信息不存在")

        updates = item.model_dump(exclude_unset=True)
        if "activity_type" in updates:
            validate_activity_type(updates["activity_type"])
        if "schedule_times" in updates:
            updates["schedule_times"] = normalize_activity_schedule(updates["schedule_times"])

        for key, value in updates.items():
            setattr(activity, key, value)

        db.commit()
        db.refresh(activity)
        return {"message": "活动信息已更新", "item": activity}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新活动信息失败: {str(e)}")

@router.delete("/activities/{activity_id}")
async def delete_scenic_activity(activity_id: int, db: Session = Depends(get_db)):
    try:
        activity = db.query(ScenicActivity).filter(ScenicActivity.id == activity_id).first()
        if not activity:
            raise HTTPException(status_code=404, detail="活动信息不存在")
        db.delete(activity)
        db.commit()
        return {"message": "活动信息已删除"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除活动信息失败: {str(e)}")

@router.get("/report")
async def get_visitor_report(start_date: str, end_date: str, db: Session = Depends(get_db)):
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        interactions = db.query(VisitorInteraction).filter(
            VisitorInteraction.created_at >= start,
            VisitorInteraction.created_at <= end
        ).all()
        
        satisfaction_rate = 85.5  # 示例数据
        if interactions:
            # 计算满意度
            total = len(interactions)
            positive = sum(1 for i in interactions if (i.satisfaction_score or 0) >= 4)
            satisfaction_rate = (positive / total) * 100 if total > 0 else 0
        
        return {"report": {"satisfaction_rate": satisfaction_rate, "comments": []}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成报告失败: {str(e)}")

@router.get("/logs")
async def get_logs(start_date: str, end_date: str, level: str = None, db: Session = Depends(get_db)):
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        query = db.query(SystemLog).filter(
            SystemLog.created_at >= start,
            SystemLog.created_at <= end
        )
        if level:
            query = query.filter(SystemLog.level == level)
        logs = query.all()
        return {"logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询日志失败: {str(e)}")
