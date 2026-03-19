# 🏗️ OMMS v2.0 — نظام إدارة التشغيل والصيانة المتكامل
## Operation & Maintenance Management System

---

## 📦 ما يحتويه هذا المشروع

```
omms/
├── backend/                     ← Python FastAPI REST API (37 ملف)
│   ├── app/
│   │   ├── main.py              ← نقطة الدخول الرئيسية
│   │   ├── core/                ← الإعدادات، قاعدة البيانات، الأمان
│   │   ├── models/models.py     ← 20+ نموذج SQLAlchemy (709 سطر)
│   │   ├── schemas/schemas.py   ← Pydantic schemas
│   │   ├── api/v1/endpoints/    ← 16 endpoint module
│   │   │   ├── auth.py
│   │   │   ├── assets.py        ← + QR code
│   │   │   ├── work_orders.py   ← + workflow كامل
│   │   │   ├── maintenance_plans.py
│   │   │   ├── inventory.py
│   │   │   ├── workforce.py
│   │   │   ├── contracts.py
│   │   │   ├── budget.py
│   │   │   ├── hse.py
│   │   │   ├── quality.py
│   │   │   ├── dashboard.py     ← KPIs + Charts
│   │   │   ├── reports.py       ← PDF + Excel
│   │   │   ├── notifications.py
│   │   │   └── ai_analytics.py  ← Predictive AI
│   │   └── services/
│   │       ├── scheduler.py     ← APScheduler jobs
│   │       ├── notification_service.py  ← Email + WhatsApp
│   │       ├── report_service.py        ← ReportLab + openpyxl
│   │       └── ai_service.py            ← Predictive engine
│   ├── tests/test_api.py        ← 30+ pytest tests
│   ├── seed.py                  ← بيانات تجريبية كاملة
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── migrations/env.py
│   └── Dockerfile
├── frontend/
│   ├── omms-app.html            ← تطبيق كامل بملف HTML واحد (1323 سطر)
│   ├── Dockerfile
│   └── src/
│       ├── utils/api.js         ← Axios client لكل endpoints
│       └── i18n/translations.js ← ترجمة عربي/إنجليزي
├── nginx/nginx.conf             ← Reverse proxy + Rate limiting
├── docker-compose.yml           ← Full stack: API + DB + Redis + Nginx
├── Makefile                     ← أوامر سريعة
└── README.md
```

---

## 🚀 تشغيل سريع (5 دقائق)

### الطريقة 1: بدون Docker
```bash
cd omms/backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python seed.py                    # تهيئة البيانات التجريبية
uvicorn app.main:app --reload --port 8000
```
ثم افتح `frontend/omms-app.html` مباشرة في المتصفح.

### الطريقة 2: Docker Compose (كل شيء دفعة واحدة)
```bash
cd omms
docker-compose up -d
docker exec omms_api python seed.py
# API Docs:  http://localhost:8000/api/docs
# Frontend:  http://localhost:3000
```

---

## 🔐 بيانات الدخول
| المستخدم | كلمة المرور | الدور |
|----------|-------------|-------|
| `admin` | `admin123` | Super Admin — كامل الصلاحيات |
| `engineer` | `eng123` | Maintenance Engineer |
| `technician` | `tech123` | Field Technician |

---

## 📡 الـ API الرئيسية

| Method | Endpoint | الوصف |
|--------|----------|-------|
| POST | `/api/v1/auth/login` | تسجيل الدخول |
| GET | `/api/v1/dashboard/stats` | KPIs الرئيسية |
| GET/POST | `/api/v1/assets` | إدارة الأصول |
| GET/POST | `/api/v1/work-orders` | أوامر العمل |
| PATCH | `/api/v1/work-orders/{id}/assign` | تعيين فني |
| PATCH | `/api/v1/work-orders/{id}/complete` | إنهاء أمر العمل |
| GET/POST | `/api/v1/maintenance-plans` | خطط الصيانة |
| POST | `/api/v1/maintenance-plans/{id}/generate-work-order` | توليد WO تلقائي |
| GET/POST | `/api/v1/inventory/spare-parts` | قطع الغيار |
| POST | `/api/v1/inventory/spare-parts/{id}/transaction` | حركة مخزون |
| GET | `/api/v1/inventory/alerts` | تنبيهات المخزون المنخفض |
| GET/POST | `/api/v1/hse/incidents` | حوادث HSE |
| GET/POST | `/api/v1/hse/permits` | تصاريح العمل PTW |
| GET/POST | `/api/v1/quality/ncr` | عدم المطابقة NCR |
| GET/POST | `/api/v1/contracts` | العقود |
| GET | `/api/v1/contracts/expiring` | عقود قاربت الانتهاء |
| GET/POST | `/api/v1/budget/plans` | الميزانية |
| GET | `/api/v1/reports/maintenance-summary` | تقرير الصيانة |
| GET | `/api/v1/ai/fleet-health` | صحة الأسطول AI |
| GET | `/api/v1/ai/asset-risk/{id}` | توقع فشل أصل |
| GET | `/api/v1/ai/high-risk-assets` | الأصول عالية الخطر |
| GET | `/api/v1/ai/spare-parts-forecast` | توقع قطع الغيار |

📖 **التوثيق الكامل التفاعلي:** `http://localhost:8000/api/docs`

---

## 🗄️ نماذج قاعدة البيانات (Database Models)

```
users               ← RBAC: 9 أدوار مختلفة
projects            ← 8 أنواع مشاريع
asset_categories    ← تصنيفات هرمية
assets              ← الأصول + QR + GPS + specifications
maintenance_plans   ← خطط وقائية + checklist
work_orders         ← أوامر عمل + workflow + توقيع رقمي
spare_parts         ← قطع الغيار + FIFO
inventory_transactions ← سجل كامل للحركات
purchase_orders     ← طلبات الشراء
contracts           ← العقود + SLA
incidents           ← الحوادث + تحقيق + إجراءات
permits_to_work     ← تصاريح PTW
inspection_checklists ← قوائم الفحص
non_conformances    ← NCR
budget_plans        ← الميزانيات السنوية
cost_transactions   ← معاملات التكاليف
notifications       ← إشعارات + WhatsApp/Email flags
audit_logs          ← سجل تدقيق كامل
kpi_snapshots       ← لقطات KPI تاريخية
```

---

## ⏰ المهام التلقائية (APScheduler)

| المهمة | التوقيت | الوصف |
|--------|---------|-------|
| `auto_generate_work_orders` | يومياً 6:00 ص | إنشاء WOs للخطط المستحقة |
| `check_overdue_work_orders` | يومياً 6:30 ص | تعليم المتأخرة + إشعار |
| `check_low_stock_alerts` | يومياً 7:00 ص | تنبيه المخزون المنخفض |
| `check_contract_expiry` | أسبوعياً الاثنين | تنبيه العقود قاربت الانتهاء |
| `compute_kpi_snapshot` | أول كل شهر | حفظ لقطة KPI تاريخية |

---

## 🤖 وحدة الذكاء الاصطناعي

محرك تنبؤي rule-based يحسب:

- **احتمالية الفشل (0-100%)** بناءً على:
  - عمر الأصل نسبة للعمر الافتراضي
  - تأخر الصيانة عن موعدها
  - تكرار أوامر العمل التصحيحية (90 يوم)
  - سجل الحوادث
  
- **تحسين الفترة الزمنية للصيانة** بناءً على:
  - معدل إنجاز أوامر العمل
  - متوسط المعيوب في كل فحص
  - درجة حرجية الأصل

- **تنبؤ قطع الغيار** للأشهر القادمة

- **تحليل MTBF / MTTR** لكل أصل

> قابل للترقية لـ ML models (scikit-learn, Prophet) لاحقاً

---

## 📊 مؤشرات الأداء KPIs

| KPI | الهدف | الوصف |
|-----|-------|-------|
| Asset Availability | ≥ 98% | نسبة الأصول التشغيلية |
| WO Completion Rate | ≥ 95% | معدل إنجاز أوامر العمل |
| MTTR | < 4 hrs | متوسط وقت الإصلاح |
| MTBF | > 500 hrs | متوسط الوقت بين الأعطال |
| OEE | > 85% | الكفاءة الشاملة للمعدات |
| LTI Rate | 0 | حوادث العجز عن العمل |
| NCR Closure Rate | > 90% | معدل إغلاق عدم المطابقة |

---

## 🧪 تشغيل الاختبارات

```bash
cd backend
pip install pytest httpx
python -m pytest tests/ -v

# المتوقع:
# 30+ tests PASSED
# Coverage: Auth, Assets, Work Orders, Inventory,
#           Dashboard, HSE, AI, Notifications, Contracts, Budget,
#           Report Service (PDF + Excel)
```

---

## 🌐 التكاملات

| التكامل | الحالة | التفاصيل |
|---------|--------|---------|
| WhatsApp | ✅ جاهز | Twilio API — أضف بيانات في .env |
| Email | ✅ جاهز | SMTP — Gmail/Outlook |
| PDF Export | ✅ جاهز | ReportLab |
| Excel Export | ✅ جاهز | openpyxl |
| QR Code | ✅ جاهز | تلقائي عند إضافة أصل |
| SCADA/IoT | 🔜 قريباً | REST endpoints جاهزة |
| Power BI | 🔜 قريباً | via REST API |

---

## 💼 النموذج التجاري المقترح

### SaaS Pricing
| الباقة | السعر | الحدود |
|--------|-------|-------|
| Basic | 500 ر.س/شهر | 5 مستخدمين، مشروع واحد |
| Professional | 1,500 ر.س/شهر | 20 مستخدماً، 5 مشاريع |
| Enterprise | 4,000 ر.س/شهر | غير محدود |

### On-Premise License
- إعداد وتركيب: **25,000 — 50,000 ر.س**
- ترخيص سنوي: **12,000 — 30,000 ر.س**

---

*OMMS v2.0 | Python FastAPI | SQLAlchemy | PostgreSQL | RTL Arabic/English*
