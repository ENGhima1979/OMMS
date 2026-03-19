"""
OMMS AI Predictive Analytics Service
Failure prediction, maintenance optimization, anomaly detection
"""

import logging
from datetime import date, timedelta
from typing import List, Dict, Optional
import math

logger = logging.getLogger("omms.ai")


class PredictiveMaintenanceEngine:
    """
    Rule-based predictive maintenance engine.
    In production, replace with ML models (scikit-learn, TensorFlow, etc.)
    """

    def predict_failure_probability(
        self,
        asset_id: int,
        running_hours: float,
        expected_life_hours: float,
        days_since_last_maintenance: int,
        maintenance_frequency_days: int,
        recent_corrective_wos: int,
        recent_incidents: int,
    ) -> Dict:
        """
        Calculate failure probability score (0-100)
        Based on: age, maintenance history, incident frequency
        """
        score = 0.0

        # 1. Age factor (0-30 points)
        if expected_life_hours > 0:
            age_pct = min(running_hours / expected_life_hours, 1.0)
            score += age_pct * 30

        # 2. Overdue maintenance factor (0-30 points)
        if maintenance_frequency_days > 0:
            overdue_ratio = days_since_last_maintenance / maintenance_frequency_days
            score += min(overdue_ratio, 1.5) * 20

        # 3. Corrective work order frequency (0-25 points)
        # More corrective WOs = higher failure probability
        score += min(recent_corrective_wos * 8, 25)

        # 4. Incident history (0-15 points)
        score += min(recent_incidents * 5, 15)

        score = min(score, 100)

        # Risk classification
        if score >= 75:
            risk_level = "critical"
            recommendation = "Immediate inspection and preventive action required"
            recommendation_ar = "مطلوب فحص فوري وإجراء وقائي عاجل"
        elif score >= 50:
            risk_level = "high"
            recommendation = "Schedule maintenance within 7 days"
            recommendation_ar = "جدول صيانة خلال 7 أيام"
        elif score >= 25:
            risk_level = "medium"
            recommendation = "Continue monitoring, schedule next maintenance on time"
            recommendation_ar = "استمر في المراقبة وجدول الصيانة في الموعد"
        else:
            risk_level = "low"
            recommendation = "Asset is in good condition"
            recommendation_ar = "الأصل في حالة جيدة"

        return {
            "asset_id": asset_id,
            "failure_probability": round(score, 1),
            "risk_level": risk_level,
            "recommendation": recommendation,
            "recommendation_ar": recommendation_ar,
            "factors": {
                "age_factor": round(min(running_hours / max(expected_life_hours, 1), 1.0) * 30, 1),
                "maintenance_overdue_factor": round(min(days_since_last_maintenance / max(maintenance_frequency_days, 1), 1.5) * 20, 1),
                "corrective_frequency_factor": round(min(recent_corrective_wos * 8, 25), 1),
                "incident_factor": round(min(recent_incidents * 5, 15), 1),
            },
            "analyzed_at": date.today().isoformat(),
        }

    def predict_optimal_maintenance_interval(
        self,
        current_interval_days: int,
        wo_completion_rate: float,
        avg_defects_per_inspection: float,
        asset_criticality: str,
    ) -> Dict:
        """Optimize maintenance interval based on performance data"""
        adjustment = 1.0

        # If completion rate is low, tighten interval
        if wo_completion_rate < 0.8:
            adjustment *= 0.85

        # If many defects found, tighten interval
        if avg_defects_per_inspection > 2:
            adjustment *= 0.75
        elif avg_defects_per_inspection < 0.5:
            adjustment *= 1.15  # Can extend interval

        # Criticality constraint
        criticality_max = {
            "critical": 0.9,
            "high": 1.0,
            "medium": 1.2,
            "low": 1.4,
        }
        adjustment = min(adjustment, criticality_max.get(asset_criticality, 1.0))

        new_interval = round(current_interval_days * adjustment)

        return {
            "current_interval_days": current_interval_days,
            "recommended_interval_days": new_interval,
            "adjustment_factor": round(adjustment, 2),
            "change": "decrease" if new_interval < current_interval_days else "increase" if new_interval > current_interval_days else "no_change",
            "reasoning": self._get_interval_reasoning(adjustment, wo_completion_rate, avg_defects_per_inspection),
        }

    def _get_interval_reasoning(self, adj: float, completion_rate: float, defects: float) -> str:
        reasons = []
        if completion_rate < 0.8:
            reasons.append("Low WO completion rate suggests maintenance is being deferred")
        if defects > 2:
            reasons.append("High defect rate indicates asset needs more frequent attention")
        elif defects < 0.5:
            reasons.append("Low defect rate suggests interval can be safely extended")
        if not reasons:
            reasons.append("Asset performance is within normal parameters")
        return ". ".join(reasons)

    def analyze_fleet_health(self, db) -> Dict:
        """Analyze overall fleet health and generate summary"""
        from app.models.models import Asset, AssetStatus, WorkOrder, WorkOrderType, WorkOrderStatus
        from sqlalchemy import func

        total = db.query(Asset).filter(Asset.is_deleted == False).count()
        if total == 0:
            return {"total_assets": 0, "health_score": 0}

        operational = db.query(Asset).filter(
            Asset.status == AssetStatus.operational,
            Asset.is_deleted == False
        ).count()

        # Assets with overdue maintenance
        today = date.today()
        overdue_maintenance = db.query(Asset).filter(
            Asset.next_maintenance_date < today,
            Asset.status != AssetStatus.decommissioned,
            Asset.is_deleted == False,
        ).count()

        # Recent corrective WOs (last 30 days)
        recent_corrective = db.query(WorkOrder).filter(
            WorkOrder.wo_type == WorkOrderType.corrective,
            WorkOrder.created_at >= today - timedelta(days=30),
        ).count()

        # Fleet health score (0-100)
        availability_score = (operational / total) * 40
        maintenance_score = max(0, (1 - overdue_maintenance / total)) * 30
        reliability_score = max(0, (1 - min(recent_corrective / max(total, 1), 1))) * 30
        health_score = round(availability_score + maintenance_score + reliability_score, 1)

        # Identify high-risk assets
        critical_assets = db.query(Asset).filter(
            Asset.criticality == "critical",
            Asset.status != AssetStatus.operational,
            Asset.is_deleted == False,
        ).all()

        return {
            "total_assets": total,
            "operational_assets": operational,
            "availability_pct": round(operational / total * 100, 1),
            "overdue_maintenance_count": overdue_maintenance,
            "recent_corrective_wos": recent_corrective,
            "fleet_health_score": health_score,
            "health_grade": "A" if health_score >= 85 else "B" if health_score >= 70 else "C" if health_score >= 55 else "D",
            "critical_assets_at_risk": [
                {"id": a.id, "name": a.name, "status": a.status} for a in critical_assets
            ],
            "recommendations": self._fleet_recommendations(health_score, overdue_maintenance, recent_corrective),
        }

    def _fleet_recommendations(self, score: float, overdue: int, corrective: int) -> List[str]:
        recs = []
        if score < 70:
            recs.append("Fleet health is below target — initiate comprehensive review")
        if overdue > 0:
            recs.append(f"Address {overdue} assets with overdue maintenance immediately")
        if corrective > 5:
            recs.append("High corrective WO rate — review maintenance plan effectiveness")
        if score >= 85:
            recs.append("Fleet is performing well — maintain current maintenance schedule")
        return recs

    def generate_spare_parts_forecast(self, db, project_id: int, months_ahead: int = 3) -> List[Dict]:
        """Forecast spare parts consumption based on maintenance plans"""
        from app.models.models import MaintenancePlan, SparePart

        today = date.today()
        forecast_end = today + timedelta(days=months_ahead * 30)

        plans = db.query(MaintenancePlan).filter(
            MaintenancePlan.project_id == project_id,
            MaintenancePlan.is_active == True,
            MaintenancePlan.next_due_date <= forecast_end,
        ).all()

        # Count planned maintenance events
        events_per_part = {}
        for plan in plans:
            for item in (plan.required_spare_parts or []):
                part_id = item.get("part_id")
                qty = item.get("quantity", 1)
                if part_id:
                    events_per_part[part_id] = events_per_part.get(part_id, 0) + qty

        forecast = []
        for part_id, needed_qty in events_per_part.items():
            part = db.query(SparePart).filter(SparePart.id == part_id).first()
            if part:
                current_stock = part.quantity_in_stock
                shortage = max(0, needed_qty - current_stock)
                forecast.append({
                    "part_id": part_id,
                    "part_number": part.part_number,
                    "name": part.name,
                    "name_ar": part.name_ar,
                    "current_stock": current_stock,
                    "forecasted_need": needed_qty,
                    "shortage": shortage,
                    "action_required": shortage > 0,
                    "urgency": "critical" if shortage > 0 and part.is_critical else "normal",
                })

        return sorted(forecast, key=lambda x: x["shortage"], reverse=True)


# Singleton
ai_engine = PredictiveMaintenanceEngine()
