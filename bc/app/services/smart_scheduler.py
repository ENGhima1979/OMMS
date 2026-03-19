"""
OMMS Smart Maintenance Scheduler
توليد أوامر العمل بتوزيع ذكي يمنع الازدحام
"""

from datetime import date, timedelta
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import math
import logging

logger = logging.getLogger("omms.scheduler.smart")


FREQ_DAYS = {
    "daily": 1,
    "weekly": 7,
    "biweekly": 14,
    "monthly": 30,
    "quarterly": 91,
    "semi_annual": 182,
    "annual": 365,
}

FREQ_PER_YEAR = {
    "daily": 365,
    "weekly": 52,
    "biweekly": 26,
    "monthly": 12,
    "quarterly": 4,
    "semi_annual": 2,
    "annual": 1,
}


class SmartScheduler:
    """
    Distributes maintenance work orders across the project timeline
    avoiding congestion and ensuring balanced daily workload.
    """

    def __init__(
        self,
        project_start: date,
        project_end: date,
        max_wo_per_day: int = 5,
        work_days: List[int] = None,  # 0=Mon..6=Sun; None=all except Fri,Sat
    ):
        self.start = project_start
        self.end = project_end
        self.max_per_day = max_wo_per_day
        # Default: Saturday is day off (Saudi schedule)
        self.work_days = work_days if work_days is not None else [0, 1, 2, 3, 4, 6]  # Mon-Fri + Sun
        # day_load[date] = count of WOs scheduled that day
        self._day_load: Dict[date, int] = defaultdict(int)

    def _is_work_day(self, d: date) -> bool:
        return d.weekday() in self.work_days

    def _next_available_day(self, from_date: date) -> date:
        """Find next working day that isn't full"""
        d = from_date
        while d <= self.end:
            if self._is_work_day(d) and self._day_load[d] < self.max_per_day:
                return d
            d += timedelta(days=1)
        return from_date  # fallback

    def generate_dates(
        self,
        frequency: str,
        plan_start: Optional[date] = None,
        custom_days: Optional[int] = None,
        preferred_day_of_week: Optional[int] = None,  # 0=Mon
    ) -> List[date]:
        """
        Generate all scheduled dates for a maintenance plan
        using smart distribution.
        """
        start = max(plan_start or self.start, self.start)
        interval = custom_days if frequency == "custom" and custom_days else FREQ_DAYS.get(frequency, 30)

        dates = []
        current = start

        while current <= self.end:
            # Find best day near 'current'
            best = self._find_best_slot(current, preferred_day_of_week)
            if best and best <= self.end:
                dates.append(best)
                self._day_load[best] += 1
            current += timedelta(days=interval)

        logger.info(f"Generated {len(dates)} dates for {frequency} plan")
        return dates

    def _find_best_slot(self, target: date, preferred_dow: Optional[int] = None) -> Optional[date]:
        """
        Find the best available slot within ±3 days of target,
        respecting max_per_day and preferred day of week.
        """
        candidates = []
        for offset in range(-3, 4):
            d = target + timedelta(days=offset)
            if d < self.start or d > self.end:
                continue
            if not self._is_work_day(d):
                continue
            load = self._day_load[d]
            if load >= self.max_per_day:
                continue
            # Score: prefer low load, prefer preferred DOW, prefer closer to target
            dow_bonus = 2 if preferred_dow is not None and d.weekday() == preferred_dow else 0
            score = (self.max_per_day - load) + dow_bonus - abs(offset)
            candidates.append((score, d))

        if not candidates:
            # Fallback: find next available day
            return self._next_available_day(target)

        candidates.sort(key=lambda x: (-x[0], x[1]))
        return candidates[0][1]

    def get_load_stats(self) -> Dict:
        """Return statistics about the generated schedule"""
        if not self._day_load:
            return {"total_days": 0, "total_wo": 0, "avg_per_day": 0, "max_per_day": 0}

        total_wo = sum(self._day_load.values())
        days_with_work = len(self._day_load)
        return {
            "total_work_orders": total_wo,
            "days_with_work": days_with_work,
            "avg_per_day": round(total_wo / days_with_work, 1) if days_with_work else 0,
            "max_per_day_actual": max(self._day_load.values()) if self._day_load else 0,
            "overloaded_days": sum(1 for v in self._day_load.values() if v >= self.max_per_day),
        }

    def generate_all_plans(self, plans: List[Dict]) -> List[Dict]:
        """
        Generate work orders for multiple plans at once,
        balancing across all plans.

        plans: [{"id", "name", "frequency", "start_date",
                  "component_id", "estimated_duration_hours", ...}]
        """
        # Sort plans: higher frequency first (daily, weekly take priority)
        priority = {
            "daily": 0, "weekly": 1, "biweekly": 2,
            "monthly": 3, "quarterly": 4, "semi_annual": 5, "annual": 6, "custom": 7
        }
        sorted_plans = sorted(plans, key=lambda p: priority.get(p.get("frequency", "monthly"), 7))

        all_work_orders = []
        year = self.start.year

        for plan in sorted_plans:
            freq = plan.get("frequency", "monthly")
            plan_start = plan.get("start_date") or self.start
            if isinstance(plan_start, str):
                plan_start = date.fromisoformat(plan_start)

            dates = self.generate_dates(
                frequency=freq,
                plan_start=plan_start,
                custom_days=plan.get("custom_days"),
                preferred_day_of_week=plan.get("preferred_day_of_week"),
            )

            type_prefix = {
                "daily": "PM", "weekly": "PM", "biweekly": "PM",
                "monthly": "PM", "quarterly": "PM",
                "semi_annual": "PM", "annual": "PM",
            }.get(freq, "PM")

            for i, d in enumerate(dates):
                wo_number = f"{type_prefix}-{year}-{len(all_work_orders)+1:06d}"
                all_work_orders.append({
                    "wo_number": wo_number,
                    "maintenance_plan_id": plan["id"],
                    "title": f"{plan['name']} — {d.strftime('%Y-%m-%d')}",
                    "title_ar": f"{plan.get('name_ar', plan['name'])} — {d.strftime('%Y/%m/%d')}",
                    "wo_type": "preventive",
                    "status": "pending",
                    "priority": "medium",
                    "project_id": plan.get("project_id"),
                    "component_id": plan.get("component_id"),
                    "scheduled_date": d.isoformat(),
                    "estimated_duration_hours": plan.get("estimated_duration_hours", 2.0),
                    "estimated_cost": plan.get("estimated_cost", 0.0),
                    "checklist_items": plan.get("checklist_items", []),
                    "safety_precautions": plan.get("safety_precautions", ""),
                })

        logger.info(f"Generated {len(all_work_orders)} total WOs from {len(plans)} plans")
        return all_work_orders


def generate_work_orders_for_plan(
    plan_id: int,
    plan_name: str,
    frequency: str,
    project_start: date,
    project_end: date,
    component_id: Optional[int] = None,
    project_id: Optional[int] = None,
    estimated_duration: float = 2.0,
    estimated_cost: float = 0.0,
    checklist_items: list = None,
    max_wo_per_day: int = 5,
    db=None,
) -> Tuple[List[Dict], Dict]:
    """
    High-level function to generate work orders for a single plan.
    Returns (work_orders_list, stats_dict)
    """
    scheduler = SmartScheduler(
        project_start=project_start,
        project_end=project_end,
        max_wo_per_day=max_wo_per_day,
    )

    dates = scheduler.generate_dates(frequency=frequency, plan_start=project_start)
    year = project_start.year

    work_orders = []
    for i, d in enumerate(dates):
        work_orders.append({
            "wo_number": f"PM-{year}-PLAN{plan_id}-{i+1:04d}",
            "maintenance_plan_id": plan_id,
            "title": f"{plan_name}",
            "title_ar": plan_name,
            "wo_type": "preventive",
            "status": "pending",
            "priority": "medium",
            "project_id": project_id,
            "component_id": component_id,
            "scheduled_date": d,
            "estimated_duration_hours": estimated_duration,
            "estimated_cost": estimated_cost,
            "checklist_items": checklist_items or [],
        })

    stats = scheduler.get_load_stats()
    stats["frequency"] = frequency
    stats["per_year"] = FREQ_PER_YEAR.get(frequency, 0)

    return work_orders, stats


def calculate_storage_from_level(level: float, storage_curve: list) -> Optional[float]:
    """
    Calculate storage volume (MCM) from water level using storage curve.
    storage_curve: [{"level": 140.0, "volume_mcm": 45.2}, ...]
    Uses linear interpolation.
    """
    if not storage_curve or len(storage_curve) < 2:
        return None

    # Sort by level
    curve = sorted(storage_curve, key=lambda x: x["level"])

    if level < curve[0]["level"]:
        return curve[0]["volume_mcm"]
    if level > curve[-1]["level"]:
        return curve[-1]["volume_mcm"]

    # Linear interpolation
    for i in range(len(curve) - 1):
        l1, v1 = curve[i]["level"], curve[i]["volume_mcm"]
        l2, v2 = curve[i+1]["level"], curve[i+1]["volume_mcm"]
        if l1 <= level <= l2:
            ratio = (level - l1) / (l2 - l1)
            return v1 + ratio * (v2 - v1)

    return None
