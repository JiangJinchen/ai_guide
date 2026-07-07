import psycopg2

SPOT_ORDER = {
    "灵山大照壁": 1,
    "五明桥": 2,
    "佛足坛": 3,
    "五智门": 4,
    "菩提大道": 5,
    "九龙灌浴": 6,
    "降魔浮雕": 7,
    "阿育王柱": 8,
    "百子戏弥勒": 9,
    "祥符禅寺": 10,
    "灵山大佛": 11,
    "佛教文化博览馆": 12,
    "无尽意斋": 13,
    "灵山梵宫": 14,
    "五印坛城": 15,
    "曼飞龙塔": 16,
    "拈花广场": 17,
    "香月花街": 18,
    "拈花堂": 19,
    "五灯湖": 20,
    "梵天花海": 21,
    "鹿鸣谷": 22
}

STANDARD_STAY_MINUTES = {
    "灵山大佛": 35,
    "灵山梵宫": 55,
    "九龙灌浴": 25,
    "五印坛城": 35,
    "祥符禅寺": 30,
    "佛教文化博览馆": 30,
    "香月花街": 25,
    "梵天花海": 25,
    "灵山大照壁": 15,
    "五明桥": 10,
    "佛足坛": 15,
    "五智门": 10,
    "菩提大道": 15,
    "降魔浮雕": 15,
    "阿育王柱": 10,
    "百子戏弥勒": 15,
    "无尽意斋": 20,
    "曼飞龙塔": 15,
    "拈花广场": 20,
    "拈花堂": 20,
    "五灯湖": 20,
    "鹿鸣谷": 30
}

MUST_SEE_SPOTS = ["灵山大佛", "灵山梵宫", "九龙灌浴", "五印坛城"]
REST_AREAS = ["香月花街", "拈花广场", "五灯湖"]

SPOT_TAGS = {
    "灵山大照壁": [("architecture_art", 10), ("zen_culture", 8)],
    "五明桥": [("architecture_art", 8), ("zen_culture", 6)],
    "佛足坛": [("buddha_history", 10), ("parent_child", 8)],
    "五智门": [("architecture_art", 9), ("zen_culture", 7)],
    "菩提大道": [("zen_culture", 9), ("scenery", 7)],
    "九龙灌浴": [("buddha_performance", 10), ("parent_child", 9)],
    "降魔浮雕": [("buddha_history", 9), ("architecture_art", 8)],
    "阿育王柱": [("buddha_history", 10), ("architecture_art", 7)],
    "百子戏弥勒": [("buddha_history", 8), ("parent_child", 9)],
    "祥符禅寺": [("ancient_temple", 10), ("buddha_history", 9)],
    "灵山大佛": [("buddha_history", 10), ("blessing", 10), ("scenery", 8)],
    "佛教文化博览馆": [("buddha_history", 9), ("architecture_art", 7)],
    "无尽意斋": [("architecture_art", 7), ("leisure_service", 6)],
    "灵山梵宫": [("architecture_art", 10), ("buddha_history", 9), ("scenery", 8)],
    "五印坛城": [("architecture_art", 10), ("buddha_history", 8), ("scenery", 9)],
    "曼飞龙塔": [("architecture_art", 8), ("buddha_history", 7)],
    "拈花广场": [("scenery", 9), ("leisure_service", 8)],
    "香月花街": [("leisure_service", 10), ("scenery", 7)],
    "拈花堂": [("zen_culture", 8), ("architecture_art", 7)],
    "五灯湖": [("scenery", 9), ("leisure_service", 8)],
    "梵天花海": [("scenery", 10), ("parent_child", 7)],
    "鹿鸣谷": [("scenery", 9), ("parent_child", 8)]
}

def init_data():
    conn = None
    try:
        conn = psycopg2.connect(
            database='ai_guide',
            user='postgres',
            password='456jlqwxhn',
            host='localhost',
            port='5432'
        )
        conn.set_client_encoding('UTF8')
        cur = conn.cursor()
        
        print("=" * 60)
        print("初始化 spot_visit_meta 数据")
        print("=" * 60)
        
        cur.execute("DELETE FROM spot_visit_meta")
        
        cur.execute("SELECT id, spot_name FROM spots")
        spots = {row[1]: row[0] for row in cur.fetchall()}
        
        for spot_name, order in SPOT_ORDER.items():
            spot_id = spots.get(spot_name)
            if not spot_id:
                print(f"  ⚠️ 景点 '{spot_name}' 在spots表中不存在")
                continue
            
            stay_minutes = STANDARD_STAY_MINUTES.get(spot_name, 25)
            is_must_see = spot_name in MUST_SEE_SPOTS
            is_rest_area = spot_name in REST_AREAS
            
            cur.execute("""
                INSERT INTO spot_visit_meta (spot_id, official_order, suggested_stay_minutes, is_must_see, is_rest_area)
                VALUES (%s, %s, %s, %s, %s)
            """, (spot_id, order, stay_minutes, is_must_see, is_rest_area))
            
            print(f"  ✅ {spot_name}: 顺序={order}, 停留={stay_minutes}分钟, 必看={is_must_see}, 休息区={is_rest_area}")
        
        print("\n" + "=" * 60)
        print("初始化 spot_tags 数据")
        print("=" * 60)
        
        cur.execute("DELETE FROM spot_tags")
        
        for spot_name, tags in SPOT_TAGS.items():
            spot_id = spots.get(spot_name)
            if not spot_id:
                print(f"  ⚠️ 景点 '{spot_name}' 在spots表中不存在")
                continue
            
            for tag, score in tags:
                cur.execute("""
                    INSERT INTO spot_tags (spot_id, tag, score)
                    VALUES (%s, %s, %s)
                """, (spot_id, tag, score))
            
            tag_names = ", ".join([t[0] for t in tags])
            print(f"  ✅ {spot_name}: [{tag_names}]")
        
        conn.commit()
        
        print("\n" + "=" * 60)
        print("✅ 数据初始化完成")
        print("=" * 60)
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 初始化失败: {e}")
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    init_data()