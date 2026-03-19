"""
OMMS Test Suite
Tests for API endpoints, models, and business logic
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Helpers ──────────────────────────────────────────────────────
def make_client():
    """Create test client with in-memory SQLite DB"""
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.main import app
    from app.core.database import get_db, Base

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    TestSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    return TestClient(app), engine


def get_token(client):
    """Register admin and return JWT token"""
    client.post("/api/v1/auth/register", json={
        "employee_id": "EMP-TEST-001",
        "username": "testadmin",
        "email": "test@omms.com",
        "full_name": "Test Admin",
        "password": "test1234",
        "role": "super_admin",
    })
    resp = client.post("/api/v1/auth/login", data={
        "username": "testadmin",
        "password": "test1234",
    })
    return resp.json()["access_token"]


# ── Test: Health ─────────────────────────────────────────────────
class TestHealth:
    def test_root(self):
        client, _ = make_client()
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert data["version"] == "2.0.0"
        assert data["status"] == "operational"

    def test_health_endpoint(self):
        client, _ = make_client()
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_docs_available(self):
        client, _ = make_client()
        r = client.get("/api/docs")
        assert r.status_code == 200


# ── Test: Authentication ─────────────────────────────────────────
class TestAuth:
    def test_register_first_user_becomes_super_admin(self):
        client, _ = make_client()
        r = client.post("/api/v1/auth/register", json={
            "employee_id": "EMP-001",
            "username": "admin",
            "email": "admin@test.com",
            "full_name": "Admin User",
            "password": "admin123",
        })
        assert r.status_code == 200
        assert r.json()["role"] == "super_admin"

    def test_login_success(self):
        client, _ = make_client()
        client.post("/api/v1/auth/register", json={
            "employee_id": "EMP-001",
            "username": "admin",
            "email": "admin@test.com",
            "full_name": "Admin",
            "password": "admin123",
        })
        r = client.post("/api/v1/auth/login", data={
            "username": "admin",
            "password": "admin123",
        })
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self):
        client, _ = make_client()
        client.post("/api/v1/auth/register", json={
            "employee_id": "EMP-001",
            "username": "admin",
            "email": "a@b.com",
            "full_name": "Admin",
            "password": "correct",
        })
        r = client.post("/api/v1/auth/login", data={
            "username": "admin",
            "password": "wrong",
        })
        assert r.status_code == 401

    def test_me_endpoint(self):
        client, _ = make_client()
        token = get_token(client)
        r = client.get("/api/v1/auth/me",
                       headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["username"] == "testadmin"

    def test_protected_endpoint_no_token(self):
        client, _ = make_client()
        r = client.get("/api/v1/assets")
        assert r.status_code == 403


# ── Test: Projects ───────────────────────────────────────────────
class TestProjects:
    def test_create_project(self):
        client, _ = make_client()
        token = get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        r = client.post("/api/v1/projects", json={
            "code": "PRJ-001",
            "name": "Test Dam Project",
            "project_type": "dam",
            "start_date": "2024-01-01",
            "end_date": "2026-12-31",
            "budget": 1000000.0,
        }, headers=headers)
        assert r.status_code == 200
        assert r.json()["code"] == "PRJ-001"

    def test_list_projects(self):
        client, _ = make_client()
        token = get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        r = client.get("/api/v1/projects", headers=headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_duplicate_project_code(self):
        client, _ = make_client()
        token = get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"code": "PRJ-DUP", "name": "P1", "project_type": "dam",
                   "start_date": "2024-01-01", "end_date": "2026-12-31"}
        client.post("/api/v1/projects", json=payload, headers=headers)
        r = client.post("/api/v1/projects", json=payload, headers=headers)
        assert r.status_code == 400


# ── Test: Assets ─────────────────────────────────────────────────
class TestAssets:
    def _create_project(self, client, headers):
        r = client.post("/api/v1/projects", json={
            "code": "PRJ-A", "name": "P", "project_type": "dam",
            "start_date": "2024-01-01", "end_date": "2026-12-31",
        }, headers=headers)
        return r.json()["id"]

    def test_create_asset_with_qr(self):
        client, _ = make_client()
        token = get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        proj_id = self._create_project(client, headers)
        r = client.post("/api/v1/assets", json={
            "asset_code": "ASSET-001",
            "name": "Test Pump",
            "project_id": proj_id,
            "criticality": "high",
        }, headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["asset_code"] == "ASSET-001"
        assert data["qr_code"] is not None  # QR auto-generated

    def test_asset_qr_code_endpoint(self):
        client, _ = make_client()
        token = get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        proj_id = self._create_project(client, headers)
        r = client.post("/api/v1/assets", json={
            "asset_code": "ASSET-QR",
            "name": "QR Test",
            "project_id": proj_id,
        }, headers=headers)
        asset_id = r.json()["id"]
        r2 = client.get(f"/api/v1/assets/{asset_id}/qr-code", headers=headers)
        assert r2.status_code == 200
        assert "qr_code" in r2.json()

    def test_asset_not_found(self):
        client, _ = make_client()
        token = get_token(client)
        r = client.get("/api/v1/assets/9999",
                       headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 404

    def test_update_running_hours(self):
        client, _ = make_client()
        token = get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        proj_id = self._create_project(client, headers)
        r = client.post("/api/v1/assets", json={
            "asset_code": "ASSET-HRS",
            "name": "Hours Test",
            "project_id": proj_id,
        }, headers=headers)
        asset_id = r.json()["id"]
        r2 = client.patch(
            f"/api/v1/assets/{asset_id}/update-hours",
            params={"running_hours": 5000.0},
            headers=headers
        )
        assert r2.status_code == 200
        assert r2.json()["running_hours"] == 5000.0


# ── Test: Work Orders ────────────────────────────────────────────
class TestWorkOrders:
    def _setup(self, client, headers):
        proj = client.post("/api/v1/projects", json={
            "code": "PRJ-WO", "name": "P", "project_type": "dam",
            "start_date": "2024-01-01", "end_date": "2026-12-31",
        }, headers=headers).json()
        asset = client.post("/api/v1/assets", json={
            "asset_code": "A-WO-001", "name": "WO Test Asset",
            "project_id": proj["id"],
        }, headers=headers).json()
        return proj["id"], asset["id"]

    def test_create_work_order_auto_numbering(self):
        client, _ = make_client()
        token = get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        proj_id, asset_id = self._setup(client, headers)
        r = client.post("/api/v1/work-orders", json={
            "title": "Test Pump Inspection",
            "wo_type": "preventive",
            "priority": "medium",
            "project_id": proj_id,
            "asset_id": asset_id,
            "scheduled_date": "2025-04-01",
            "estimated_duration_hours": 2.0,
        }, headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["wo_number"].startswith("PM-")
        assert data["status"] == "draft"

    def test_corrective_wo_numbering(self):
        client, _ = make_client()
        token = get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        proj_id, asset_id = self._setup(client, headers)
        r = client.post("/api/v1/work-orders", json={
            "title": "Pump Failure Fix",
            "wo_type": "corrective",
            "priority": "critical",
            "project_id": proj_id,
            "asset_id": asset_id,
            "scheduled_date": "2025-04-01",
        }, headers=headers)
        assert r.json()["wo_number"].startswith("CM-")

    def test_emergency_wo_numbering(self):
        client, _ = make_client()
        token = get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        proj_id, asset_id = self._setup(client, headers)
        r = client.post("/api/v1/work-orders", json={
            "title": "Emergency Repair",
            "wo_type": "emergency",
            "priority": "critical",
            "project_id": proj_id,
            "asset_id": asset_id,
            "scheduled_date": "2025-04-01",
        }, headers=headers)
        assert r.json()["wo_number"].startswith("EM-")

    def test_wo_stats(self):
        client, _ = make_client()
        token = get_token(client)
        r = client.get("/api/v1/work-orders/stats/summary",
                       headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert "by_status" in data

    def test_complete_work_order(self):
        client, _ = make_client()
        token = get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        proj_id, asset_id = self._setup(client, headers)
        wo = client.post("/api/v1/work-orders", json={
            "title": "Complete Test",
            "wo_type": "preventive",
            "priority": "low",
            "project_id": proj_id,
            "asset_id": asset_id,
            "scheduled_date": "2025-04-01",
        }, headers=headers).json()
        r = client.patch(
            f"/api/v1/work-orders/{wo['id']}/complete",
            params={"completion_notes": "Done OK", "actual_duration_hours": 2.5},
            headers=headers
        )
        assert r.status_code == 200
        assert r.json()["status"] == "completed"


# ── Test: Inventory ───────────────────────────────────────────────
class TestInventory:
    def test_create_spare_part(self):
        client, _ = make_client()
        token = get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        r = client.post("/api/v1/inventory/spare-parts", json={
            "part_number": "SP-TEST-001",
            "name": "Test Bearing",
            "unit": "pcs",
            "quantity_in_stock": 10.0,
            "minimum_quantity": 3.0,
            "reorder_point": 5.0,
            "unit_cost": 150.0,
        }, headers=headers)
        assert r.status_code == 200
        assert r.json()["part_number"] == "SP-TEST-001"

    def test_inventory_transaction_issue(self):
        client, _ = make_client()
        token = get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        part = client.post("/api/v1/inventory/spare-parts", json={
            "part_number": "SP-TX-001",
            "name": "TX Test Part",
            "unit": "pcs",
            "quantity_in_stock": 20.0,
            "minimum_quantity": 2.0,
            "reorder_point": 3.0,
            "unit_cost": 100.0,
        }, headers=headers).json()
        r = client.post(
            f"/api/v1/inventory/spare-parts/{part['id']}/transaction",
            params={"qty": 5.0, "tx_type": "issue", "notes": "For PM-001"},
            headers=headers
        )
        assert r.status_code == 200
        assert r.json()["quantity_in_stock"] == 15.0

    def test_inventory_transaction_insufficient_stock(self):
        client, _ = make_client()
        token = get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        part = client.post("/api/v1/inventory/spare-parts", json={
            "part_number": "SP-LOW-001",
            "name": "Low Stock Part",
            "unit": "pcs",
            "quantity_in_stock": 2.0,
            "minimum_quantity": 1.0,
            "reorder_point": 1.0,
            "unit_cost": 100.0,
        }, headers=headers).json()
        r = client.post(
            f"/api/v1/inventory/spare-parts/{part['id']}/transaction",
            params={"qty": 10.0, "tx_type": "issue"},
            headers=headers
        )
        assert r.status_code == 400  # Insufficient stock

    def test_low_stock_alerts(self):
        client, _ = make_client()
        token = get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        # Create a low-stock part
        client.post("/api/v1/inventory/spare-parts", json={
            "part_number": "SP-ALERT-001",
            "name": "Alert Part",
            "unit": "pcs",
            "quantity_in_stock": 1.0,
            "minimum_quantity": 5.0,
            "reorder_point": 5.0,
            "unit_cost": 100.0,
        }, headers=headers)
        r = client.get("/api/v1/inventory/alerts", headers=headers)
        assert r.status_code == 200
        assert len(r.json()) >= 1


# ── Test: Dashboard ────────────────────────────────────────────────
class TestDashboard:
    def test_stats(self):
        client, _ = make_client()
        token = get_token(client)
        r = client.get("/api/v1/dashboard/stats",
                       headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert "assets" in data
        assert "work_orders" in data
        assert "inventory" in data

    def test_asset_status_chart(self):
        client, _ = make_client()
        token = get_token(client)
        r = client.get("/api/v1/dashboard/charts/asset-status",
                       headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

    def test_wo_trend_chart(self):
        client, _ = make_client()
        token = get_token(client)
        r = client.get("/api/v1/dashboard/charts/work-orders-trend",
                       params={"months": 6},
                       headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 6


# ── Test: HSE ─────────────────────────────────────────────────────
class TestHSE:
    def _get_proj(self, client, headers):
        return client.post("/api/v1/projects", json={
            "code": "PRJ-HSE", "name": "HSE Proj", "project_type": "dam",
            "start_date": "2024-01-01", "end_date": "2026-12-31",
        }, headers=headers).json()["id"]

    def test_create_incident(self):
        client, _ = make_client()
        token = get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        proj_id = self._get_proj(client, headers)
        r = client.post("/api/v1/hse/incidents", json={
            "title": "Worker Slip",
            "severity": "minor",
            "project_id": proj_id,
            "incident_date": "2025-03-15",
            "location": "Zone B",
        }, headers=headers)
        assert r.status_code == 200
        assert r.json()["incident_number"].startswith("INC-")

    def test_hse_stats(self):
        client, _ = make_client()
        token = get_token(client)
        r = client.get("/api/v1/hse/stats",
                       headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert "total_incidents" in data


# ── Test: AI Analytics ────────────────────────────────────────────
class TestAI:
    def test_fleet_health(self):
        client, _ = make_client()
        token = get_token(client)
        r = client.get("/api/v1/ai/fleet-health",
                       headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert "fleet_health_score" in data
        assert "health_grade" in data

    def test_high_risk_assets_empty(self):
        client, _ = make_client()
        token = get_token(client)
        r = client.get("/api/v1/ai/high-risk-assets",
                       headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_failure_prediction_logic(self):
        """Test the AI engine directly"""
        from app.services.ai_service import PredictiveMaintenanceEngine
        engine = PredictiveMaintenanceEngine()

        # High-risk scenario
        result = engine.predict_failure_probability(
            asset_id=1,
            running_hours=18000,
            expected_life_hours=17520,  # 2 years, almost dead
            days_since_last_maintenance=90,
            maintenance_frequency_days=30,
            recent_corrective_wos=5,
            recent_incidents=3,
        )
        assert result["risk_level"] == "critical"
        assert result["failure_probability"] >= 75

        # Low-risk scenario
        result2 = engine.predict_failure_probability(
            asset_id=2,
            running_hours=1000,
            expected_life_hours=175200,
            days_since_last_maintenance=5,
            maintenance_frequency_days=30,
            recent_corrective_wos=0,
            recent_incidents=0,
        )
        assert result2["risk_level"] == "low"
        assert result2["failure_probability"] < 25

    def test_maintenance_interval_optimization(self):
        from app.services.ai_service import PredictiveMaintenanceEngine
        engine = PredictiveMaintenanceEngine()

        # Poor completion rate should tighten interval
        result = engine.predict_optimal_maintenance_interval(
            current_interval_days=30,
            wo_completion_rate=0.6,
            avg_defects_per_inspection=3.0,
            asset_criticality="critical",
        )
        assert result["recommended_interval_days"] < 30
        assert result["change"] == "decrease"


# ── Test: Notifications ───────────────────────────────────────────
class TestNotifications:
    def test_list_notifications(self):
        client, _ = make_client()
        token = get_token(client)
        r = client.get("/api/v1/notifications",
                       headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_unread_count(self):
        client, _ = make_client()
        token = get_token(client)
        r = client.get("/api/v1/notifications/unread-count",
                       headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert "count" in r.json()


# ── Test: Contracts ────────────────────────────────────────────────
class TestContracts:
    def _get_proj(self, client, headers):
        return client.post("/api/v1/projects", json={
            "code": "PRJ-CTR", "name": "CTR Proj", "project_type": "dam",
            "start_date": "2024-01-01", "end_date": "2026-12-31",
        }, headers=headers).json()["id"]

    def test_create_contract(self):
        client, _ = make_client()
        token = get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        proj_id = self._get_proj(client, headers)
        r = client.post("/api/v1/contracts", json={
            "contract_number": "CTR-TEST-001",
            "title": "Maintenance Contract",
            "contract_type": "maintenance",
            "party_name": "Test Vendor",
            "project_id": proj_id,
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "value": 100000.0,
        }, headers=headers)
        assert r.status_code == 200
        assert r.json()["contract_number"] == "CTR-TEST-001"

    def test_expiring_contracts(self):
        client, _ = make_client()
        token = get_token(client)
        r = client.get("/api/v1/contracts/expiring",
                       params={"days": 365},
                       headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200


# ── Test: Budget ──────────────────────────────────────────────────
class TestBudget:
    def test_create_budget_plan(self):
        client, _ = make_client()
        token = get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        proj = client.post("/api/v1/projects", json={
            "code": "PRJ-BUD", "name": "Budget Proj", "project_type": "dam",
            "start_date": "2024-01-01", "end_date": "2026-12-31",
        }, headers=headers).json()
        r = client.post("/api/v1/budget/plans", json={
            "project_id": proj["id"],
            "year": 2025,
            "total_budget": 500000.0,
            "labor_budget": 200000.0,
            "material_budget": 150000.0,
            "contractor_budget": 100000.0,
            "overhead_budget": 30000.0,
            "contingency_budget": 20000.0,
        }, headers=headers)
        assert r.status_code == 200
        assert r.json()["total_budget"] == 500000.0

    def test_budget_summary(self):
        client, _ = make_client()
        token = get_token(client)
        r = client.get("/api/v1/budget/summary",
                       params={"year": 2025},
                       headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200


# ── Test: Report Service ───────────────────────────────────────────
class TestReportService:
    def test_pdf_generation(self):
        from app.services.report_service import generate_work_order_pdf
        pdf_bytes = generate_work_order_pdf({
            "wo_number": "PM-TEST-001",
            "title": "Test Inspection",
            "wo_type": "preventive",
            "status": "completed",
            "asset_name": "Test Pump",
            "scheduled_date": "2025-03-19",
            "estimated_duration_hours": 2.0,
            "description": "Weekly inspection checklist",
            "checklist_items": [
                {"item": "Check oil", "item_ar": "فحص الزيت"},
                {"item": "Check leaks", "item_ar": "فحص التسربات"},
            ],
        })
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:4] == b"%PDF"  # Valid PDF header

    def test_excel_generation(self):
        from app.services.report_service import generate_maintenance_report_excel
        xlsx_bytes = generate_maintenance_report_excel({
            "period_from": "2025-01-01",
            "period_to": "2025-03-31",
            "completion_rate": 87.5,
            "asset_availability": 96.5,
            "mttr": 2.8,
            "oee": 83.9,
            "budget_used_pct": 42.0,
            "open_incidents": 2,
            "work_orders": [
                {
                    "wo_number": "PM-001",
                    "title": "Weekly Inspection",
                    "wo_type": "preventive",
                    "status": "completed",
                    "priority": "medium",
                    "scheduled_date": "2025-03-17",
                    "actual_duration_hours": 2.5,
                    "actual_cost": 620,
                }
            ],
            "spare_parts": [
                {
                    "part_number": "SP-001",
                    "name": "Pump Impeller",
                    "quantity_in_stock": 2,
                    "minimum_quantity": 2,
                    "reorder_point": 2,
                    "unit_cost": 1200,
                    "total_value": 2400,
                }
            ],
        })
        assert isinstance(xlsx_bytes, bytes)
        assert len(xlsx_bytes) > 0
        # Excel files start with PK (zip format)
        assert xlsx_bytes[:2] == b"PK"


# ── Run ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
