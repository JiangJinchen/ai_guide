from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
import csv
import io
import json
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    AppUserBehavior,
    RouteHistory,
    Spot,
    VisitorBehavior,
    VisitorFeedback,
    VisitorInteraction,
)


router = APIRouter()


def _parse_date(value: str | None, fallback: date) -> date:
    if not value:
        return fallback
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="日期格式必须为 YYYY-MM-DD") from exc


def _date_range(start_date: str | None, end_date: str | None):
    today = date.today()
    end_day = _parse_date(end_date, today)
    start_day = _parse_date(start_date, end_day - timedelta(days=29))
    if start_day > end_day:
        raise HTTPException(status_code=400, detail="开始日期不能晚于结束日期")
    if (end_day - start_day).days > 365:
        raise HTTPException(status_code=400, detail="单次查询范围不能超过 366 天")
    start_at = datetime.combine(start_day, time.min)
    end_at = datetime.combine(end_day + timedelta(days=1), time.min)
    return start_day, end_day, start_at, end_at


def _period(start_day: date, end_day: date) -> dict:
    return {"start_date": start_day.isoformat(), "end_date": end_day.isoformat()}


def _datetime_rows(db: Session, model, start_at: datetime, end_at: datetime):
    return db.query(model).filter(
        model.created_at >= start_at,
        model.created_at < end_at,
    ).all()


def _behavior_rows(
    db: Session,
    start_day: date,
    end_day: date,
    start_at: datetime,
    end_at: datetime,
):
    return db.query(VisitorBehavior).filter(
        or_(
            and_(
                VisitorBehavior.visit_date.is_not(None),
                VisitorBehavior.visit_date >= start_day,
                VisitorBehavior.visit_date <= end_day,
            ),
            and_(
                VisitorBehavior.visit_date.is_(None),
                VisitorBehavior.created_at >= start_at,
                VisitorBehavior.created_at < end_at,
            ),
        )
    ).all()


def _lingshan_behavior_rows(
    db: Session,
    start_day: date,
    end_day: date,
    start_at: datetime,
    end_at: datetime,
):
    rows = _behavior_rows(db, start_day, end_day, start_at, end_at)
    spot_names = {
        name.strip()
        for (name,) in db.query(Spot.spot_name).all()
        if name and name.strip()
    }
    if not spot_names:
        return []
    return [
        item for item in rows
        if item.attraction_name and any(
            spot_name in item.attraction_name
            for spot_name in spot_names
        )
    ]


def _number(value) -> float:
    return float(value or 0)


def _average(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


def _behavior_total_cost(item) -> float:
    if item.total_cost is not None:
        return _number(item.total_cost)
    return sum(
        _number(getattr(item, field))
        for field in ("ticket_cost", "food_cost", "shopping_cost", "transport_cost", "entertainment_cost")
    )


def _normalize_question(value: str | None) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    return text.strip("？?。！!，,；; ")


def _route_spot_names(route_record: RouteHistory) -> list[str]:
    try:
        payload = json.loads(route_record.route_data or "{}")
    except (TypeError, json.JSONDecodeError):
        return []
    names = []
    for item in payload.get("route", []):
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("spot_name")
        if name and name not in names:
            names.append(str(name))
    return names


def _rating_summary(feedbacks) -> dict:
    ratings = [
        _number(item.satisfaction_score)
        for item in feedbacks
        if item.satisfaction_score is not None
    ]
    distribution = {str(score): sum(1 for rating in ratings if round(rating) == score) for score in range(1, 6)}
    positive = sum(1 for rating in ratings if rating >= 4)
    services = defaultdict(list)
    for item in feedbacks:
        if item.satisfaction_score is None:
            continue
        service = item.feedback_type or item.target_type or "未分类"
        services[service].append(_number(item.satisfaction_score))
    return {
        "average_score": _average(ratings),
        "satisfaction_rate": round(positive * 100 / len(ratings), 2) if ratings else 0.0,
        "rating_count": len(ratings),
        "distribution": distribution,
        "by_service": [
            {
                "feedback_type": service,
                "count": len(values),
                "average_score": _average(values),
                "satisfaction_rate": round(sum(1 for value in values if value >= 4) * 100 / len(values), 2),
            }
            for service, values in sorted(services.items())
        ],
    }


@router.get("/overview")
def analytics_overview(
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
):
    start_day, end_day, start_at, end_at = _date_range(start_date, end_date)
    interactions = _datetime_rows(db, VisitorInteraction, start_at, end_at)
    routes = _datetime_rows(db, RouteHistory, start_at, end_at)
    feedbacks = _datetime_rows(db, VisitorFeedback, start_at, end_at)
    behaviors = _lingshan_behavior_rows(db, start_day, end_day, start_at, end_at)
    navigation = [
        item for item in _datetime_rows(db, AppUserBehavior, start_at, end_at)
        if item.behavior_type == "navigate"
    ]

    visitor_ids = {
        item.visitor_id
        for item in [*interactions, *routes, *feedbacks, *behaviors]
        if item.visitor_id
    }
    visitor_ids.update(item.visitor_id for item in navigation if item.visitor_id)
    session_ids = {item.session_id for item in interactions if item.session_id}
    satisfaction = _rating_summary(feedbacks)
    spend_values = [_behavior_total_cost(item) for item in behaviors]
    spending_visitor_ids = {item.visitor_id for item in behaviors if item.visitor_id}

    focus_counts = Counter()
    for route in routes:
        focus_counts.update(_route_spot_names(route))
    focus_counts.update(item.spot_name for item in navigation if item.spot_name)
    question_counts = Counter()
    for item in interactions:
        if item.interaction_type != "chat":
            continue
        question = _normalize_question(item.content)
        if question:
            question_counts[question] += 1
    category_totals = {
        "门票": sum(_number(item.ticket_cost) for item in behaviors),
        "餐饮": sum(_number(item.food_cost) for item in behaviors),
        "购物": sum(_number(item.shopping_cost) for item in behaviors),
        "交通": sum(_number(item.transport_cost) for item in behaviors),
        "娱乐": sum(_number(item.entertainment_cost) for item in behaviors),
    }

    insights = []
    if focus_counts:
        name, count = focus_counts.most_common(1)[0]
        insights.append(f"{name} 是本周期关注度最高的景点，在路线或导航中共出现 {count} 次。")
    if question_counts:
        question, count = question_counts.most_common(1)[0]
        insights.append(f"游客最常咨询“{question}”，共出现 {count} 次，可优先完善相关内容和 FAQ。")
    if any(category_totals.values()):
        category = max(category_totals, key=category_totals.get)
        insights.append(f"{category}是当前占比最高的消费类别，可结合高关注景点设计联动服务。")
    if satisfaction["rating_count"]:
        insights.append(
            f"综合满意率为 {satisfaction['satisfaction_rate']:.1f}%，建议优先复盘低于 4 分的服务记录。"
        )

    return {
        "period": _period(start_day, end_day),
        "visitor_count": len(visitor_ids),
        "session_count": len(session_ids),
        "interaction_count": len(interactions),
        "route_count": len(routes),
        "feedback_count": len(feedbacks),
        "average_spend": round(sum(spend_values) / len(spending_visitor_ids), 2) if spending_visitor_ids else 0.0,
        **satisfaction,
        "insights": insights,
    }


@router.get("/comparison")
def analytics_comparison(
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
):
    """Compare the selected period with the immediately preceding equal period."""
    start_day, end_day, _, _ = _date_range(start_date, end_date)
    period_days = (end_day - start_day).days + 1
    previous_end = start_day - timedelta(days=1)
    previous_start = previous_end - timedelta(days=period_days - 1)

    current = analytics_overview(
        start_date=start_day.isoformat(),
        end_date=end_day.isoformat(),
        db=db,
    )
    previous = analytics_overview(
        start_date=previous_start.isoformat(),
        end_date=previous_end.isoformat(),
        db=db,
    )
    fields = (
        "visitor_count",
        "session_count",
        "interaction_count",
        "route_count",
        "feedback_count",
        "average_spend",
        "satisfaction_rate",
    )
    changes = {}
    for field in fields:
        current_value = _number(current.get(field))
        previous_value = _number(previous.get(field))
        delta = round(current_value - previous_value, 2)
        if previous_value:
            rate = round(delta * 100 / previous_value, 2)
        else:
            rate = 0.0 if not current_value else None
        changes[field] = {
            "current": round(current_value, 2),
            "previous": round(previous_value, 2),
            "delta": delta,
            "rate": rate,
        }

    return {
        "period": _period(start_day, end_day),
        "comparison_period": _period(previous_start, previous_end),
        "changes": changes,
    }


@router.get("/visitors")
def analytics_visitors(
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
):
    start_day, end_day, start_at, end_at = _date_range(start_date, end_date)
    interactions = _datetime_rows(db, VisitorInteraction, start_at, end_at)
    visitors_by_day = defaultdict(set)
    interactions_by_day = Counter()
    for item in interactions:
        day = item.created_at.date().isoformat()
        if item.visitor_id:
            visitors_by_day[day].add(item.visitor_id)
        interactions_by_day[day] += 1

    series = []
    current = start_day
    while current <= end_day:
        key = current.isoformat()
        series.append({
            "date": key,
            "visitor_count": len(visitors_by_day[key]),
            "interaction_count": interactions_by_day[key],
        })
        current += timedelta(days=1)
    return {"period": _period(start_day, end_day), "series": series}


@router.get("/focus-points")
def analytics_focus_points(
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    start_day, end_day, start_at, end_at = _date_range(start_date, end_date)
    routes = _datetime_rows(db, RouteHistory, start_at, end_at)
    navigation = [
        item for item in _datetime_rows(db, AppUserBehavior, start_at, end_at)
        if item.behavior_type == "navigate" and item.spot_name
    ]
    route_counts = Counter()
    for route in routes:
        route_counts.update(_route_spot_names(route))
    navigation_counts = Counter(item.spot_name for item in navigation)
    names = set(route_counts) | set(navigation_counts)
    items = [
        {
            "name": name,
            "route_count": route_counts[name],
            "navigation_count": navigation_counts[name],
            "count": route_counts[name] + navigation_counts[name],
            "route_coverage_rate": round(route_counts[name] * 100 / len(routes), 2) if routes else 0.0,
        }
        for name in names
    ]
    items.sort(key=lambda item: item["count"], reverse=True)
    return {
        "period": _period(start_day, end_day),
        "route_count": len(routes),
        "navigation_count": len(navigation),
        "items": items[:max(1, min(limit, 50))],
    }


@router.get("/hot-questions")
def analytics_hot_questions(
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    start_day, end_day, start_at, end_at = _date_range(start_date, end_date)
    interactions = _datetime_rows(db, VisitorInteraction, start_at, end_at)
    grouped = defaultdict(lambda: {"count": 0, "answer": ""})
    for item in interactions:
        if item.interaction_type != "chat":
            continue
        question = _normalize_question(item.content)
        if not question:
            continue
        row = grouped[question]
        row["count"] += 1
        if item.reply_text:
            row["answer"] = item.reply_text

    items = [
        {
            "question": question,
            "count": values["count"],
            "latest_answer": values["answer"],
        }
        for question, values in grouped.items()
    ]
    items.sort(key=lambda item: item["count"], reverse=True)
    return {"period": _period(start_day, end_day), "items": items[:max(1, min(limit, 50))]}


@router.get("/routes")
def analytics_routes(
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    start_day, end_day, start_at, end_at = _date_range(start_date, end_date)
    routes = _datetime_rows(db, RouteHistory, start_at, end_at)
    grouped = defaultdict(lambda: {"count": 0, "names": Counter(), "durations": [], "distances": [], "spots": []})
    for item in routes:
        spot_names = _route_spot_names(item)
        signature = tuple(spot_names) if spot_names else (item.route_name or "未命名路线",)
        row = grouped[signature]
        row["count"] += 1
        row["names"][item.route_name or "未命名路线"] += 1
        row["spots"] = spot_names
        if item.total_duration is not None:
            row["durations"].append(_number(item.total_duration))
        if item.total_distance is not None:
            row["distances"].append(_number(item.total_distance))

    popular_routes = [
        {
            "route_name": values["names"].most_common(1)[0][0],
            "spot_names": values["spots"],
            "route_path": " → ".join(values["spots"]) if values["spots"] else signature[0],
            "count": values["count"],
            "average_duration": _average(values["durations"]),
            "average_distance": _average(values["distances"]),
        }
        for signature, values in grouped.items()
    ]
    popular_routes.sort(key=lambda item: (-item["count"], item["average_duration"], item["route_name"]))
    return {
        "period": _period(start_day, end_day),
        "total": len(routes),
        "unique_route_count": len(popular_routes),
        "popular_routes": popular_routes[:max(1, min(limit, 50))],
    }


@router.get("/consumption")
def analytics_consumption(
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
):
    start_day, end_day, start_at, end_at = _date_range(start_date, end_date)
    behaviors = _lingshan_behavior_rows(db, start_day, end_day, start_at, end_at)
    fields = [
        ("门票", "ticket_cost"),
        ("餐饮", "food_cost"),
        ("购物", "shopping_cost"),
        ("交通", "transport_cost"),
        ("娱乐", "entertainment_cost"),
    ]
    category_totals = {
        label: round(sum(_number(getattr(item, field)) for item in behaviors), 2)
        for label, field in fields
    }
    category_sum = sum(category_totals.values())
    categories = [
        {
            "name": label,
            "total": total,
            "average": round(total / len(behaviors), 2) if behaviors else 0.0,
            "share": round(total * 100 / category_sum, 2) if category_sum else 0.0,
        }
        for label, total in category_totals.items()
    ]
    total_values = [_behavior_total_cost(item) for item in behaviors]
    visitor_ids = {item.visitor_id for item in behaviors if item.visitor_id}
    segments = Counter()
    for value in total_values:
        if value < 100:
            segments["100元以下"] += 1
        elif value < 300:
            segments["100-299元"] += 1
        elif value < 500:
            segments["300-499元"] += 1
        else:
            segments["500元及以上"] += 1

    category_shares = {item["name"]: item["share"] for item in categories}
    insights = []
    if category_sum:
        top_category = max(categories, key=lambda item: item["total"])
        insights.append(f"{top_category['name']}消费占比最高，为 {top_category['share']:.1f}%。")
        if category_shares.get("餐饮", 0) < 15:
            insights.append("餐饮消费占比较低，可结合热门路线设置餐饮优惠券或路线套餐。")
        if category_shares.get("购物", 0) < 10:
            insights.append("购物消费占比较低，可在高关注景点配置文创联名和到店引导。")
        if category_shares.get("门票", 0) >= 60:
            insights.append("消费仍以门票为主，可通过餐饮、文创和体验活动提高非票收入。")

    return {
        "period": _period(start_day, end_day),
        "record_count": len(behaviors),
        "visitor_count": len(visitor_ids),
        "total_spend": round(sum(total_values), 2),
        "average_spend": round(sum(total_values) / len(visitor_ids), 2) if visitor_ids else 0.0,
        "average_non_ticket_spend": round(
            sum(total for name, total in category_totals.items() if name != "门票") / len(visitor_ids), 2
        ) if visitor_ids else 0.0,
        "categories": categories,
        "segments": [{"name": name, "count": segments[name]} for name in ["100元以下", "100-299元", "300-499元", "500元及以上"]],
        "insights": insights,
    }


@router.get("/satisfaction")
def analytics_satisfaction(
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
):
    start_day, end_day, start_at, end_at = _date_range(start_date, end_date)
    feedbacks = _datetime_rows(db, VisitorFeedback, start_at, end_at)
    negative_feedback = [
        {
            "id": item.id,
            "score": item.satisfaction_score,
            "comment": item.comment,
            "feedback_type": item.feedback_type,
            "target_type": item.target_type,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in sorted(
            feedbacks,
            key=lambda item: item.created_at.timestamp() if item.created_at else 0,
            reverse=True,
        )
        if item.satisfaction_score is not None and item.satisfaction_score < 4
    ][:10]
    return {
        "period": _period(start_day, end_day),
        **_rating_summary(feedbacks),
        "negative_feedback": negative_feedback,
    }


def _csv_response(rows: list[dict], fieldnames: list[str], filename: str) -> StreamingResponse:
    output = io.StringIO(newline="")
    output.write("\ufeff")
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    response = StreamingResponse(iter([output.getvalue()]), media_type="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@router.get("/export")
def analytics_export(
    dataset: str = "overview",
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
):
    """Export an existing analytics aggregation without recalculating it in the browser."""
    start_day, end_day, start_at, end_at = _date_range(start_date, end_date)
    period_suffix = f"{start_day.isoformat()}_{end_day.isoformat()}"

    if dataset == "overview":
        data = analytics_overview(start_date=start_day.isoformat(), end_date=end_day.isoformat(), db=db)
        fields = [
            "visitor_count", "session_count", "interaction_count", "route_count",
            "feedback_count", "average_spend", "average_score", "satisfaction_rate", "rating_count",
        ]
        return _csv_response([{key: data.get(key, 0) for key in fields}], fields, f"analytics_overview_{period_suffix}.csv")

    exporters = {
        "visitors": (
            analytics_visitors(start_date=start_day.isoformat(), end_date=end_day.isoformat(), db=db)["series"],
            ["date", "visitor_count", "interaction_count"],
        ),
        "focus_points": (
            analytics_focus_points(start_date=start_day.isoformat(), end_date=end_day.isoformat(), db=db)["items"],
            ["name", "route_count", "navigation_count", "count", "route_coverage_rate"],
        ),
        "hot_questions": (
            analytics_hot_questions(start_date=start_day.isoformat(), end_date=end_day.isoformat(), db=db)["items"],
            ["question", "count", "latest_answer"],
        ),
        "routes": (
            analytics_routes(start_date=start_day.isoformat(), end_date=end_day.isoformat(), db=db)["popular_routes"],
            ["route_name", "route_path", "count", "average_duration", "average_distance"],
        ),
        "consumption": (
            analytics_consumption(start_date=start_day.isoformat(), end_date=end_day.isoformat(), db=db)["categories"],
            ["name", "total", "average", "share"],
        ),
        "satisfaction": (
            analytics_satisfaction(start_date=start_day.isoformat(), end_date=end_day.isoformat(), db=db)["by_service"],
            ["feedback_type", "count", "average_score", "satisfaction_rate"],
        ),
    }
    if dataset not in exporters:
        raise HTTPException(status_code=400, detail="不支持的导出数据集")
    rows, fields = exporters[dataset]
    return _csv_response(rows, fields, f"analytics_{dataset}_{period_suffix}.csv")
