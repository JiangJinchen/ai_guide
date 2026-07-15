from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    Knowledge,
    FAQItem,
    DigitalHumanConfig,
    VisitorInteraction,
    VisitorFeedback,
    SystemLog,
    TicketProduct,
    ScenicActivity,
    Spot,
)
from app.services.guide_asset_service import generate_assets_for_spots, get_spot_guide_detail
from app.services.retrieval_cache import clear_retrieval_cache
from datetime import datetime, timedelta
import json
import re

router = APIRouter()


def _record_admin_action(
    db: Session,
    *,
    source: str,
    action: str,
    resource_type: str,
    resource_id: int,
    resource_name: str,
    details: dict | None = None,
) -> None:
    db.add(SystemLog(
        level="info",
        source=source,
        message=json.dumps({
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "resource_name": resource_name,
            "actor_id": db.info.get("admin_user_id"),
            "actor_name": db.info.get("admin_username"),
            "details": details or {},
        }, ensure_ascii=False),
    ))

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


class FAQItemCreate(BaseModel):
    question: str
    answer: str
    category: str | None = None
    sort_order: int = 100
    is_active: bool = True
    source_name: str | None = None


class FAQItemUpdate(BaseModel):
    question: str | None = None
    answer: str | None = None
    category: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    source_name: str | None = None


class SpotItem(BaseModel):
    scenic_area_name: str
    spot_name: str
    location: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    architecture_params: str | None = None
    core_function: str | None = None
    culture_connotation: str | None = None
    description: str | None = None
    highlights: str | None = None
    open_info: str | None = None
    remark: str | None = None


class SpotUpdate(BaseModel):
    scenic_area_name: str | None = None
    spot_name: str | None = None
    location: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    architecture_params: str | None = None
    core_function: str | None = None
    culture_connotation: str | None = None
    description: str | None = None
    highlights: str | None = None
    open_info: str | None = None
    remark: str | None = None

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

class SpotGuideAssetGenerateRequest(BaseModel):
    spot_id: int | None = None
    spot_ids: list[int] | None = None
    style: str = "standard"
    voice: str = "female"
    force: bool = False

def validate_activity_type(activity_type: str):
    if activity_type not in {"intro", "performance", "zen"}:
        raise HTTPException(status_code=400, detail="活动类型只能是 intro、performance 或 zen")

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
        db.flush()
        _record_admin_action(
            db, source="admin.knowledge", action="create", resource_type="knowledge",
            resource_id=new_knowledge.id, resource_name=new_knowledge.title,
            details={"category": new_knowledge.category},
        )
        db.commit()
        db.refresh(new_knowledge)
        clear_retrieval_cache()
        return {"message": "知识库条目创建成功", "item": new_knowledge}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")

@router.get("/knowledge")
async def get_knowledge(
    category: str | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
):
    try:
        query = db.query(Knowledge)
        if category:
            query = query.filter(Knowledge.category == category)
        if keyword:
            pattern = f"%{keyword.strip()}%"
            query = query.filter(
                (Knowledge.title.ilike(pattern)) | (Knowledge.content.ilike(pattern))
            )
        items = query.order_by(Knowledge.id.desc()).all()
        return {"items": items, "total": len(items)}
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

        _record_admin_action(
            db, source="admin.knowledge", action="update", resource_type="knowledge",
            resource_id=knowledge.id, resource_name=knowledge.title,
            details={"fields": sorted(item.model_dump(exclude_unset=True).keys())},
        )
        db.commit()
        db.refresh(knowledge)
        clear_retrieval_cache()
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
        _record_admin_action(
            db, source="admin.knowledge", action="delete", resource_type="knowledge",
            resource_id=knowledge.id, resource_name=knowledge.title,
        )
        db.delete(knowledge)
        db.commit()
        clear_retrieval_cache()
        return {"message": "知识库条目删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.get("/faqs")
async def get_faqs(
    keyword: str | None = None,
    category: str | None = None,
    include_inactive: bool = True,
    db: Session = Depends(get_db),
):
    query = db.query(FAQItem)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(
            (FAQItem.question.ilike(pattern)) | (FAQItem.answer.ilike(pattern))
        )
    if category:
        query = query.filter(FAQItem.category == category)
    if not include_inactive:
        query = query.filter(FAQItem.is_active.is_(True))
    items = query.order_by(FAQItem.sort_order.asc(), FAQItem.id.asc()).all()
    return {"items": items, "total": len(items)}


@router.post("/faqs")
async def create_faq(item: FAQItemCreate, db: Session = Depends(get_db)):
    if not item.question.strip() or not item.answer.strip():
        raise HTTPException(status_code=400, detail="问题和答案不能为空")
    faq = FAQItem(**item.model_dump())
    db.add(faq)
    db.flush()
    _record_admin_action(
        db, source="admin.faq", action="create", resource_type="faq",
        resource_id=faq.id, resource_name=faq.question,
        details={"is_active": faq.is_active, "category": faq.category},
    )
    db.commit()
    db.refresh(faq)
    return {"message": "FAQ 创建成功", "item": faq}


@router.get("/faqs/{faq_id}")
async def get_faq(faq_id: int, db: Session = Depends(get_db)):
    faq = db.query(FAQItem).filter(FAQItem.id == faq_id).first()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ 不存在")
    return {"item": faq}


@router.put("/faqs/{faq_id}")
async def update_faq(faq_id: int, item: FAQItemUpdate, db: Session = Depends(get_db)):
    faq = db.query(FAQItem).filter(FAQItem.id == faq_id).first()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ 不存在")
    updates = item.model_dump(exclude_unset=True)
    if "question" in updates and (not updates["question"] or not updates["question"].strip()):
        raise HTTPException(status_code=400, detail="问题不能为空")
    if "answer" in updates and (not updates["answer"] or not updates["answer"].strip()):
        raise HTTPException(status_code=400, detail="答案不能为空")
    for key, value in updates.items():
        setattr(faq, key, value)
    _record_admin_action(
        db, source="admin.faq", action="update", resource_type="faq",
        resource_id=faq.id, resource_name=faq.question,
        details={"fields": sorted(updates.keys())},
    )
    db.commit()
    db.refresh(faq)
    return {"message": "FAQ 更新成功", "item": faq}


@router.delete("/faqs/{faq_id}")
async def delete_faq(faq_id: int, db: Session = Depends(get_db)):
    faq = db.query(FAQItem).filter(FAQItem.id == faq_id).first()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ 不存在")
    _record_admin_action(
        db, source="admin.faq", action="delete", resource_type="faq",
        resource_id=faq.id, resource_name=faq.question,
    )
    db.delete(faq)
    db.commit()
    return {"message": "FAQ 删除成功"}


@router.put("/faqs/{faq_id}/status")
async def update_faq_status(faq_id: int, is_active: bool, db: Session = Depends(get_db)):
    faq = db.query(FAQItem).filter(FAQItem.id == faq_id).first()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ 不存在")
    faq.is_active = is_active
    _record_admin_action(
        db, source="admin.faq", action="publish" if is_active else "unpublish", resource_type="faq",
        resource_id=faq.id, resource_name=faq.question,
        details={"is_active": is_active},
    )
    db.commit()
    db.refresh(faq)
    return {"message": "FAQ 状态已更新", "item": faq}


@router.get("/spots")
async def get_managed_spots(
    keyword: str | None = None,
    scenic_area_name: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Spot)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(
            (Spot.spot_name.ilike(pattern))
            | (Spot.description.ilike(pattern))
            | (Spot.highlights.ilike(pattern))
        )
    if scenic_area_name:
        query = query.filter(Spot.scenic_area_name == scenic_area_name)
    items = query.order_by(Spot.id.asc()).all()
    return {"items": items, "total": len(items)}


@router.post("/spots")
async def create_managed_spot(item: SpotItem, db: Session = Depends(get_db)):
    if not item.scenic_area_name.strip() or not item.spot_name.strip():
        raise HTTPException(status_code=400, detail="景区名称和景点名称不能为空")
    spot = Spot(**item.model_dump())
    db.add(spot)
    db.flush()
    _record_admin_action(
        db, source="admin.spots", action="create", resource_type="spot",
        resource_id=spot.id, resource_name=spot.spot_name,
        details={"scenic_area_name": spot.scenic_area_name},
    )
    db.commit()
    db.refresh(spot)
    return {"message": "景点创建成功", "item": spot}


@router.get("/spots/{spot_id}")
async def get_managed_spot(spot_id: int, db: Session = Depends(get_db)):
    spot = db.query(Spot).filter(Spot.id == spot_id).first()
    if not spot:
        raise HTTPException(status_code=404, detail="景点不存在")
    return {"item": spot}


@router.put("/spots/{spot_id}")
async def update_managed_spot(spot_id: int, item: SpotUpdate, db: Session = Depends(get_db)):
    spot = db.query(Spot).filter(Spot.id == spot_id).first()
    if not spot:
        raise HTTPException(status_code=404, detail="景点不存在")
    updates = item.model_dump(exclude_unset=True)
    for key in ("scenic_area_name", "spot_name"):
        if key in updates and (not updates[key] or not updates[key].strip()):
            raise HTTPException(status_code=400, detail="景区名称和景点名称不能为空")
    for key, value in updates.items():
        setattr(spot, key, value)
    _record_admin_action(
        db, source="admin.spots", action="update", resource_type="spot",
        resource_id=spot.id, resource_name=spot.spot_name,
        details={"fields": sorted(updates.keys())},
    )
    db.commit()
    db.refresh(spot)
    return {"message": "景点更新成功", "item": spot}


@router.delete("/spots/{spot_id}")
async def delete_managed_spot(spot_id: int, db: Session = Depends(get_db)):
    spot = db.query(Spot).filter(Spot.id == spot_id).first()
    if not spot:
        raise HTTPException(status_code=404, detail="景点不存在")
    _record_admin_action(
        db, source="admin.spots", action="delete", resource_type="spot",
        resource_id=spot.id, resource_name=spot.spot_name,
    )
    db.delete(spot)
    db.commit()
    return {"message": "景点删除成功"}

@router.post("/digital-human")
async def create_digital_human_config(config: DigitalHumanConfigItem, db: Session = Depends(get_db)):
    try:
        if config.is_active:
            db.query(DigitalHumanConfig).filter(DigitalHumanConfig.is_active.is_(True)).update(
                {DigitalHumanConfig.is_active: False}, synchronize_session=False
            )
        new_config = DigitalHumanConfig(
            name=config.name,
            model=config.model,
            voice=config.voice,
            clothes=config.clothes,
            is_active=config.is_active
        )
        db.add(new_config)
        db.flush()
        _record_admin_action(
            db,
            source="admin.digital-human",
            action="create_and_publish" if config.is_active else "create",
            resource_type="digital_human_config",
            resource_id=new_config.id,
            resource_name=new_config.name,
            details={"is_active": bool(config.is_active), "voice": config.voice, "model": config.model},
        )
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
        updates = config.model_dump(exclude_unset=True)
        if "name" in updates and not (updates["name"] or "").strip():
            raise HTTPException(status_code=400, detail="数字人名称不能为空")
        snapshot_id = None
        profile_fields = {"name", "model", "voice", "clothes"}
        if existing_config.is_active and profile_fields.intersection(updates):
            snapshot = DigitalHumanConfig(
                name=f"{existing_config.name}（历史 {datetime.now():%m-%d %H:%M}）"[:100],
                model=existing_config.model,
                voice=existing_config.voice,
                clothes=existing_config.clothes,
                is_active=False,
            )
            db.add(snapshot)
            db.flush()
            snapshot_id = snapshot.id
        if updates.get("is_active") is True:
            db.query(DigitalHumanConfig).filter(
                DigitalHumanConfig.id != config_id,
                DigitalHumanConfig.is_active.is_(True),
            ).update({DigitalHumanConfig.is_active: False}, synchronize_session=False)
        for key, value in updates.items():
            setattr(existing_config, key, value)
        _record_admin_action(
            db,
            source="admin.digital-human",
            action="update" if updates.get("is_active") is not True else "update_and_publish",
            resource_type="digital_human_config",
            resource_id=existing_config.id,
            resource_name=existing_config.name,
            details={"fields": sorted(updates.keys()), "snapshot_id": snapshot_id},
        )
        db.commit()
        db.refresh(existing_config)
        return {"message": "数字人配置更新成功", "config": existing_config}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.put("/digital-human/{config_id}/activate")
async def activate_digital_human_config(config_id: int, db: Session = Depends(get_db)):
    """Publish one configuration as the sole active visitor-facing profile."""
    try:
        existing_config = db.query(DigitalHumanConfig).filter(DigitalHumanConfig.id == config_id).first()
        if not existing_config:
            raise HTTPException(status_code=404, detail="数字人配置不存在")
        db.query(DigitalHumanConfig).filter(DigitalHumanConfig.id != config_id).update(
            {DigitalHumanConfig.is_active: False}, synchronize_session=False
        )
        existing_config.is_active = True
        _record_admin_action(
            db,
            source="admin.digital-human",
            action="publish",
            resource_type="digital_human_config",
            resource_id=existing_config.id,
            resource_name=existing_config.name,
        )
        db.commit()
        db.refresh(existing_config)
        return {"message": "数字人配置已发布", "config": existing_config}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"发布失败: {str(e)}")

@router.delete("/digital-human/{config_id}")
async def delete_digital_human_config(config_id: int, db: Session = Depends(get_db)):
    try:
        existing_config = db.query(DigitalHumanConfig).filter(DigitalHumanConfig.id == config_id).first()
        if not existing_config:
            raise HTTPException(status_code=404, detail="数字人配置不存在")
        if existing_config.is_active:
            raise HTTPException(status_code=409, detail="当前生效配置不能删除，请先发布其他配置")
        _record_admin_action(
            db,
            source="admin.digital-human",
            action="delete",
            resource_type="digital_human_config",
            resource_id=existing_config.id,
            resource_name=existing_config.name,
        )
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
        items = query.order_by(TicketProduct.id.asc()).all()
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询票务信息失败: {str(e)}")

@router.post("/tickets")
async def create_ticket_product(item: TicketProductItem, db: Session = Depends(get_db)):
    try:
        ticket = TicketProduct(**item.model_dump())
        db.add(ticket)
        db.flush()
        _record_admin_action(
            db, source="admin.tickets", action="create", resource_type="ticket",
            resource_id=ticket.id, resource_name=ticket.name,
            details={"ticket_type": ticket.ticket_type, "is_active": ticket.is_active},
        )
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

        _record_admin_action(
            db, source="admin.tickets", action="update", resource_type="ticket",
            resource_id=ticket.id, resource_name=ticket.name,
            details={"fields": sorted(updates.keys())},
        )
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
        _record_admin_action(
            db, source="admin.tickets", action="delete", resource_type="ticket",
            resource_id=ticket.id, resource_name=ticket.name,
        )
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
        db.flush()
        _record_admin_action(
            db, source="admin.activities", action="create", resource_type="activity",
            resource_id=activity.id, resource_name=activity.name,
            details={"activity_type": activity.activity_type, "is_active": activity.is_active},
        )
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

        _record_admin_action(
            db, source="admin.activities", action="update", resource_type="activity",
            resource_id=activity.id, resource_name=activity.name,
            details={"fields": sorted(updates.keys())},
        )
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
        _record_admin_action(
            db, source="admin.activities", action="delete", resource_type="activity",
            resource_id=activity.id, resource_name=activity.name,
        )
        db.delete(activity)
        db.commit()
        return {"message": "活动信息已删除"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除活动信息失败: {str(e)}")

@router.post("/spot-guide-assets/generate")
async def generate_spot_guide_assets(request: SpotGuideAssetGenerateRequest, db: Session = Depends(get_db)):
    try:
        target_ids = set(request.spot_ids or [])
        if request.spot_id is not None:
            target_ids.add(request.spot_id)

        query = db.query(Spot)
        if target_ids:
            query = query.filter(Spot.id.in_(sorted(target_ids)))
        spots = query.order_by(Spot.id.asc()).all()

        if not spots:
            raise HTTPException(status_code=404, detail="未找到需要生成讲解资产的景点")

        results = await generate_assets_for_spots(
            db,
            spots,
            style=request.style,
            voice=request.voice,
            force=request.force,
        )
        _record_admin_action(
            db, source="admin.spot-guide-assets", action="generate", resource_type="spot_guide_assets",
            resource_id=request.spot_id or 0, resource_name="批量景点讲解资产",
            details={"spot_ids": sorted(target_ids), "style": request.style, "voice": request.voice, "force": request.force},
        )
        db.commit()
        return {
            "message": "讲解资产生成完成",
            "total": len(results),
            "ready_count": sum(1 for item in results if item.get("status") == "ready"),
            "text_only_count": sum(1 for item in results if item.get("status") == "text_only"),
            "failed_count": sum(1 for item in results if item.get("status") == "failed"),
            "items": results,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"生成讲解资产失败: {str(e)}")

@router.get("/spot-guide-assets/{spot_id}")
async def get_spot_guide_asset(spot_id: int, style: str = "standard", voice: str = "female", db: Session = Depends(get_db)):
    guide = get_spot_guide_detail(db, spot_id, style, voice)
    if not guide:
        raise HTTPException(status_code=404, detail="景点不存在")
    return guide

@router.get("/report")
async def get_visitor_report(start_date: str, end_date: str, db: Session = Depends(get_db)):
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        feedbacks = db.query(VisitorFeedback).filter(
            VisitorFeedback.created_at >= start,
            VisitorFeedback.created_at <= end
        ).all()
        
        satisfaction_rate = 85.5
        comments = []
        if feedbacks:
            total = len(feedbacks)
            positive = sum(1 for f in feedbacks if (f.satisfaction_score or 0) >= 4)
            satisfaction_rate = (positive / total) * 100 if total > 0 else 0
            comments = [{"id": f.id, "comment": f.comment, "score": f.satisfaction_score, "created_at": f.created_at.isoformat()} 
                       for f in feedbacks if f.comment]
        
        return {"report": {"satisfaction_rate": satisfaction_rate, "comments": comments}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成报告失败: {str(e)}")

@router.get("/logs")
async def get_logs(
    start_date: str,
    end_date: str,
    level: str = None,
    source: str = None,
    db: Session = Depends(get_db),
):
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        if start > end:
            raise HTTPException(status_code=400, detail="开始日期不能晚于结束日期")
        query = db.query(SystemLog).filter(
            SystemLog.created_at >= start,
            SystemLog.created_at < end + timedelta(days=1),
        )
        if level:
            query = query.filter(SystemLog.level == level)
        if source:
            query = query.filter(SystemLog.source == source)
        logs = query.order_by(SystemLog.created_at.desc(), SystemLog.id.desc()).all()
        return {"logs": logs, "total": len(logs)}
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式必须为 YYYY-MM-DD")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询日志失败: {str(e)}")
