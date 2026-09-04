import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from db.database import get_conn
from routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


class HeatmapData(BaseModel):
    """Heatmap data point."""
    hour: int
    day: int
    count: int
    event_type: str


class DayStats(BaseModel):
    """Stats for a specific day."""
    day: int
    day_name: str
    total_events: int
    opens: int
    clicks: int
    bounces: int


class HourStats(BaseModel):
    """Stats for a specific hour."""
    hour: int
    total_events: int
    opens: int
    clicks: int
    bounces: int


class EngagementHeatmap(BaseModel):
    """Full engagement heatmap data."""
    period_days: int
    total_events: int
    heatmap: list[HeatmapData]
    best_day: DayStats
    best_hour: HourStats
    daily_breakdown: list[DayStats]
    hourly_breakdown: list[HourStats]


DAY_NAMES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


@router.get("", response_model=EngagementHeatmap)
async def get_engagement_heatmap(
    days: int = Query(30, ge=1, le=365),
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user)
):
    """Get engagement heatmap data."""
    tenant_id = current_user["tenant_id"]
    
    # Get heatmap data from email_engagement table
    # If table is empty, generate from email_events
    heatmap_rows = await conn.fetch("""
        SELECT 
            event_hour as hour,
            event_day as day,
            event_type,
            COUNT(*) as count
        FROM email_engagement
        WHERE tenant_id = $1
        AND created_at >= NOW() - INTERVAL '1 day' * $2
        GROUP BY event_hour, event_day, event_type
    """, tenant_id, days)
    
    # If no engagement data, generate from email_events
    if not heatmap_rows:
        heatmap_rows = await conn.fetch("""
            SELECT 
                EXTRACT(HOUR FROM ee.created_at)::INTEGER as hour,
                EXTRACT(DOW FROM ee.created_at)::INTEGER as day,
                LOWER(ee.event_type) as event_type,
                COUNT(*) as count
            FROM email_events ee
            WHERE ee.tenant_id = $1
            AND ee.created_at >= NOW() - INTERVAL '1 day' * $2
            GROUP BY EXTRACT(HOUR FROM ee.created_at), EXTRACT(DOW FROM ee.created_at), LOWER(ee.event_type)
        """, tenant_id, days)
    
    # Process heatmap data
    heatmap = []
    for row in heatmap_rows:
        r = dict(row)
        heatmap.append(HeatmapData(
            hour=r["hour"],
            day=r["day"],
            count=r["count"],
            event_type=r["event_type"]
        ))
    
    # Get total events
    total_events = sum(h.count for h in heatmap)
    
    # Get daily breakdown
    daily_data = {}
    for h in heatmap:
        if h.day not in daily_data:
            daily_data[h.day] = {"total": 0, "opens": 0, "clicks": 0, "bounces": 0}
        daily_data[h.day]["total"] += h.count
        if h.event_type == "open":
            daily_data[h.day]["opens"] += h.count
        elif h.event_type == "click":
            daily_data[h.day]["clicks"] += h.count
        elif h.event_type == "bounce":
            daily_data[h.day]["bounces"] += h.count
    
    daily_breakdown = []
    for day in range(7):
        data = daily_data.get(day, {"total": 0, "opens": 0, "clicks": 0, "bounces": 0})
        daily_breakdown.append(DayStats(
            day=day,
            day_name=DAY_NAMES[day],
            total_events=data["total"],
            opens=data["opens"],
            clicks=data["clicks"],
            bounces=data["bounces"]
        ))
    
    # Get hourly breakdown
    hourly_data = {}
    for h in heatmap:
        if h.hour not in hourly_data:
            hourly_data[h.hour] = {"total": 0, "opens": 0, "clicks": 0, "bounces": 0}
        hourly_data[h.hour]["total"] += h.count
        if h.event_type == "open":
            hourly_data[h.hour]["opens"] += h.count
        elif h.event_type == "click":
            hourly_data[h.hour]["clicks"] += h.count
        elif h.event_type == "bounce":
            hourly_data[h.hour]["bounces"] += h.count
    
    hourly_breakdown = []
    for hour in range(24):
        data = hourly_data.get(hour, {"total": 0, "opens": 0, "clicks": 0, "bounces": 0})
        hourly_breakdown.append(HourStats(
            hour=hour,
            total_events=data["total"],
            opens=data["opens"],
            clicks=data["clicks"],
            bounces=data["bounces"]
        ))
    
    # Find best day and hour
    best_day = max(daily_breakdown, key=lambda x: x.opens)
    best_hour = max(hourly_breakdown, key=lambda x: x.opens)
    
    return EngagementHeatmap(
        period_days=days,
        total_events=total_events,
        heatmap=heatmap,
        best_day=best_day,
        best_hour=best_hour,
        daily_breakdown=daily_breakdown,
        hourly_breakdown=hourly_breakdown
    )


@router.get("/recommendations")
async def get_send_recommendations(
    days: int = Query(30, ge=1, le=365),
    conn=Depends(get_conn),
    current_user: dict = Depends(get_current_user)
):
    """Get recommendations for best time to send."""
    heatmap = await get_engagement_heatmap(days, conn, current_user)
    
    # Find top 3 hours
    top_hours = sorted(heatmap.hourly_breakdown, key=lambda x: x.opens, reverse=True)[:3]
    
    # Find top 3 days
    top_days = sorted(heatmap.daily_breakdown, key=lambda x: x.opens, reverse=True)[:3]
    
    recommendations = []
    
    # Add day recommendations
    for day in top_days:
        if day.opens > 0:
            recommendations.append({
                "type": "day",
                "value": day.day,
                "label": day.day_name,
                "score": day.opens,
                "reason": f"Mayor engagement los {day.day_name}"
            })
    
    # Add hour recommendations
    for hour in top_hours:
        if hour.opens > 0:
            recommendations.append({
                "type": "hour",
                "value": hour.hour,
                "label": f"{hour.hour:02d}:00",
                "score": hour.opens,
                "reason": f"Mayor engagement a las {hour.hour:02d}:00"
            })
    
    return {
        "period_days": days,
        "recommendations": recommendations,
        "best_time": f"Mejor día: {top_days[0].day_name}, Mejor hora: {top_hours[0].hour:02d}:00" if top_days and top_hours else "Sin datos suficientes"
    }
