# 高德地图路线规划数据库适配方案

## 现有表是否可用

当前 `spots` 表已经具备接入高德步行距离接口的最小条件：

- `id`
- `spot_name`
- `location`
- `latitude`
- `longitude`
- `description`
- `culture_connotation`
- `highlights`

其中 `latitude` / `longitude` 是路线规划的关键字段。前端定位使用 `gcj02`，高德坐标体系与之匹配，后端会按 `longitude,latitude` 的顺序调用高德接口。

## 已接入的缓存表

后端已经新增 SQLAlchemy 模型 `RouteDistanceCache`，应用重启时会由 `Base.metadata.create_all` 自动创建表。

推荐手动 SQL 如下：

```sql
CREATE TABLE IF NOT EXISTS route_distance_cache (
  id SERIAL PRIMARY KEY,
  cache_key VARCHAR(255) UNIQUE NOT NULL,
  origin_id INTEGER NULL,
  destination_id INTEGER NULL,
  origin_lng DOUBLE PRECISION NOT NULL,
  origin_lat DOUBLE PRECISION NOT NULL,
  destination_lng DOUBLE PRECISION NOT NULL,
  destination_lat DOUBLE PRECISION NOT NULL,
  travel_mode VARCHAR(50) DEFAULT 'walking',
  provider VARCHAR(50) DEFAULT 'amap',
  distance_m INTEGER NOT NULL,
  duration_sec INTEGER NOT NULL,
  raw_data TEXT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS ix_route_distance_cache_cache_key
  ON route_distance_cache (cache_key);

CREATE INDEX IF NOT EXISTS ix_route_distance_cache_travel_mode
  ON route_distance_cache (travel_mode);

CREATE INDEX IF NOT EXISTS ix_route_distance_cache_provider
  ON route_distance_cache (provider);
```

这个表用于缓存：

- 当前位置到景点
- 景点到景点
- 不同出行方式下的距离与耗时

缓存命中后不会重复调用高德，能减少延迟和配额消耗。

## 建议新增景点元数据表

当前后端仍然用内置字典维护官方游览顺序和建议停留时间。更稳的方式是落库：

```sql
CREATE TABLE IF NOT EXISTS spot_visit_meta (
  id SERIAL PRIMARY KEY,
  spot_id INTEGER NOT NULL UNIQUE,
  official_order INTEGER DEFAULT 999,
  suggested_stay_minutes INTEGER DEFAULT 25,
  is_must_see BOOLEAN DEFAULT false,
  is_rest_area BOOLEAN DEFAULT false,
  is_accessible BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS ix_spot_visit_meta_official_order
  ON spot_visit_meta (official_order);
```

用途：

- `official_order`：官方推荐游览顺序，用于避免折返。
- `suggested_stay_minutes`：景点建议停留时间，用于总耗时计算。
- `is_must_see`：经典路线优先考虑。
- `is_rest_area`：亲子/轻松路线可插入休息点。
- `is_accessible`：无障碍慢行路线过滤。

## 建议新增景点标签表

当前偏好匹配仍依赖关键词。建议把景点标签结构化：

```sql
CREATE TABLE IF NOT EXISTS spot_tags (
  id SERIAL PRIMARY KEY,
  spot_id INTEGER NOT NULL,
  tag VARCHAR(50) NOT NULL,
  score INTEGER DEFAULT 10,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_spot_tags_spot_id
  ON spot_tags (spot_id);

CREATE INDEX IF NOT EXISTS ix_spot_tags_tag
  ON spot_tags (tag);
```

推荐标签：

- `history`
- `scenery`
- `family`
- `architecture`
- `blessing`

用途：

- 用户选择“历史文化”时，优先选择 `history` 分高的景点。
- 用户选择多个偏好时，按标签加权选点。
- 后续 AI 可以只负责把自然语言转成这些结构化标签。

## 配置项

在 `backend/python/.env` 中配置：

```env
AMAP_WEB_KEY=你的高德Web服务Key
```

没有配置时，后端会自动回退到本地经纬度估算，不会中断路线规划。

## 当前后端行为

路线生成接口：

```http
POST /api/visitor/routes/generate
```

请求体：

```json
{
  "user_id": "guest",
  "preferences": ["history", "blessing"],
  "duration_minutes": 90,
  "travel_mode": "walking",
  "must_spot_ids": [11],
  "latitude": 31.43039,
  "longitude": 120.09658
}
```

返回的 `distance_model.type` 可能是：

- `amap_distance`
- `amap_distance_with_haversine_fallback`
- `haversine_estimate`

这能让前端和日志清楚知道本次路线是由高德计算，还是由本地估算兜底。
