from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Knowledge, DigitalHumanConfig, VisitorInteraction, SystemLog
from datetime import datetime

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
