"""Seed the default customer-service FAQ entries without overwriting edits."""

from app.database import Base, SessionLocal, engine
from app.models import FAQItem


DEFAULT_FAQS = [
    ("门票有效期是多久？", "门票当日有效，入园后可全天游览。如需二次入园，请在出口处办理入园登记。", "票务"),
    ("景区内可以使用无人机吗？", "为保障游客安全及文物保护，景区内禁止使用无人机等飞行设备。", "入园须知"),
    ("景区提供行李寄存服务吗？", "游客中心设有行李寄存处，提供免费寄存服务，营业时间与景区同步。", "服务设施"),
    ("园内观光车如何收费？", "观光车单次乘坐15元/人，全天通票30元/人，可在各站点自由上下车。", "交通"),
    ("景区内有餐饮服务吗？", "景区内设有素斋馆、咖啡厅及多个小吃售卖点，提供素食、简餐及特色小吃。", "餐饮"),
    ("儿童和老人有优惠政策吗？", "6周岁以下或身高1.4米以下儿童免费；60-69周岁老人半价；70周岁以上老人免费。", "票务"),
    ("遇到紧急情况怎么办？", "请立即拨打景区急救电话400-828-8888转1，或联系就近的工作人员寻求帮助。", "安全"),
    ("可以携带宠物入园吗？", "除导盲犬外，景区内禁止携带宠物入园。", "入园须知"),
]


def seed_faqs() -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        created = 0
        for index, (question, answer, category) in enumerate(DEFAULT_FAQS, start=1):
            exists = db.query(FAQItem).filter(FAQItem.question == question).first()
            if exists:
                continue
            db.add(
                FAQItem(
                    question=question,
                    answer=answer,
                    category=category,
                    sort_order=index * 10,
                    source_name="景区客服默认内容",
                )
            )
            created += 1
        db.commit()
        return created
    finally:
        db.close()


if __name__ == "__main__":
    print(f"已新增 {seed_faqs()} 条 FAQ")
