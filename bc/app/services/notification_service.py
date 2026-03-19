"""
OMMS Notification Service
Send notifications via Email, WhatsApp, and in-app
"""

import logging
from typing import Optional, List
from datetime import datetime

logger = logging.getLogger("omms.notifications")


class EmailService:
    """Email notification service via SMTP"""

    def __init__(self):
        from app.core.config import settings
        self.settings = settings
        self.enabled = bool(settings.SMTP_USER and settings.SMTP_PASSWORD)

    def send(
        self,
        to: List[str],
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
    ) -> bool:
        if not self.enabled:
            logger.info(f"[EMAIL-MOCK] To: {to} | Subject: {subject}")
            return True

        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.settings.SMTP_USER
            msg["To"] = ", ".join(to)

            if body_text:
                msg.attach(MIMEText(body_text, "plain", "utf-8"))
            msg.attach(MIMEText(body_html, "html", "utf-8"))

            with smtplib.SMTP(self.settings.SMTP_HOST, self.settings.SMTP_PORT) as server:
                server.ehlo()
                server.starttls()
                server.login(self.settings.SMTP_USER, self.settings.SMTP_PASSWORD)
                server.sendmail(self.settings.SMTP_USER, to, msg.as_string())

            logger.info(f"Email sent to {to}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Email failed: {e}")
            return False

    def send_work_order_notification(self, wo_number: str, title: str, to_email: str) -> bool:
        subject = f"[OMMS] Work Order Assigned: {wo_number}"
        body_html = f"""
        <div dir="rtl" style="font-family:Arial;max-width:600px">
          <div style="background:#185FA5;color:#fff;padding:20px;border-radius:8px 8px 0 0">
            <h2>🏗️ OMMS — أمر عمل جديد</h2>
          </div>
          <div style="background:#f9f9f9;padding:20px;border:1px solid #ddd">
            <p>تم تعيين أمر عمل جديد لك:</p>
            <table style="width:100%;border-collapse:collapse">
              <tr><td style="padding:8px;border:1px solid #ddd;font-weight:bold">رقم أمر العمل</td><td style="padding:8px;border:1px solid #ddd">{wo_number}</td></tr>
              <tr><td style="padding:8px;border:1px solid #ddd;font-weight:bold">العنوان</td><td style="padding:8px;border:1px solid #ddd">{title}</td></tr>
            </table>
            <p style="margin-top:16px">يرجى تسجيل الدخول لعرض التفاصيل الكاملة.</p>
          </div>
          <div style="background:#042C53;color:#aaa;padding:12px;text-align:center;font-size:12px;border-radius:0 0 8px 8px">
            OMMS v2.0 | نظام إدارة التشغيل والصيانة
          </div>
        </div>
        """
        return self.send([to_email], subject, body_html)

    def send_maintenance_reminder(
        self, asset_name: str, plan_name: str, due_date: str, to_email: str
    ) -> bool:
        subject = f"[OMMS] تنبيه صيانة: {asset_name}"
        body_html = f"""
        <div dir="rtl" style="font-family:Arial;max-width:600px">
          <div style="background:#EF9F27;color:#fff;padding:20px;border-radius:8px 8px 0 0">
            <h2>⏰ تنبيه: صيانة مجدولة قادمة</h2>
          </div>
          <div style="padding:20px;border:1px solid #ddd">
            <p>لديك صيانة مجدولة قادمة:</p>
            <ul>
              <li><strong>الأصل:</strong> {asset_name}</li>
              <li><strong>الخطة:</strong> {plan_name}</li>
              <li><strong>الموعد:</strong> {due_date}</li>
            </ul>
          </div>
        </div>
        """
        return self.send([to_email], subject, body_html)


class WhatsAppService:
    """WhatsApp notification via Twilio"""

    def __init__(self):
        from app.core.config import settings
        self.settings = settings
        self.enabled = bool(
            settings.TWILIO_ACCOUNT_SID
            and settings.TWILIO_AUTH_TOKEN
            and settings.TWILIO_WHATSAPP_FROM
        )

    def send(self, to_phone: str, message: str) -> bool:
        if not self.enabled:
            logger.info(f"[WHATSAPP-MOCK] To: {to_phone} | Msg: {message[:60]}...")
            return True

        try:
            from twilio.rest import Client
            client = Client(
                self.settings.TWILIO_ACCOUNT_SID,
                self.settings.TWILIO_AUTH_TOKEN
            )
            msg = client.messages.create(
                from_=self.settings.TWILIO_WHATSAPP_FROM,
                to=f"whatsapp:{to_phone}",
                body=message,
            )
            logger.info(f"WhatsApp sent to {to_phone}: {msg.sid}")
            return True

        except Exception as e:
            logger.error(f"WhatsApp failed: {e}")
            return False

    def send_work_order_alert(self, wo_number: str, title: str, to_phone: str) -> bool:
        message = (
            f"🏗️ *OMMS - أمر عمل جديد*\n\n"
            f"رقم: {wo_number}\n"
            f"العنوان: {title}\n\n"
            f"يرجى تسجيل الدخول لعرض التفاصيل."
        )
        return self.send(to_phone, message)

    def send_overdue_alert(self, wo_number: str, scheduled_date: str, to_phone: str) -> bool:
        message = (
            f"⚠️ *OMMS - تنبيه: أمر عمل متأخر*\n\n"
            f"رقم: {wo_number}\n"
            f"كان مجدولاً: {scheduled_date}\n\n"
            f"يرجى اتخاذ الإجراء اللازم فوراً."
        )
        return self.send(to_phone, message)


class NotificationManager:
    """Unified notification manager"""

    def __init__(self):
        self.email = EmailService()
        self.whatsapp = WhatsAppService()

    def notify_user(
        self,
        db,
        user_id: int,
        title: str,
        title_ar: str,
        message: str,
        message_ar: str,
        notification_type: str,
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        send_email: bool = False,
        send_whatsapp: bool = False,
    ) -> bool:
        from app.models.models import Notification, User

        # Save in-app notification
        notif = Notification(
            user_id=user_id,
            title=title,
            title_ar=title_ar,
            message=message,
            message_ar=message_ar,
            notification_type=notification_type,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        db.add(notif)

        # Send via other channels
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            if send_email and user.email:
                self.email.send(
                    [user.email],
                    title,
                    f"<p>{message}</p>",
                )
                notif.is_sent_email = True

            if send_whatsapp and user.whatsapp:
                self.whatsapp.send(user.whatsapp, f"{title}\n\n{message}")
                notif.is_sent_whatsapp = True

        db.commit()
        return True

    def notify_maintenance_due(self, db, plan_id: int) -> None:
        from app.models.models import MaintenancePlan, User

        plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id).first()
        if not plan:
            return

        # Notify all users in the project
        users = db.query(User).filter(
            User.project_id == plan.project_id,
            User.is_active == True,
            User.role.in_(["admin", "project_manager", "maintenance_engineer"]),
        ).all()

        for user in users:
            self.notify_user(
                db=db,
                user_id=user.id,
                title=f"Maintenance Due: {plan.name}",
                title_ar=f"صيانة مجدولة: {plan.name_ar or plan.name}",
                message=f"Maintenance plan {plan.plan_number} is due on {plan.next_due_date}",
                message_ar=f"خطة الصيانة {plan.plan_number} مجدولة بتاريخ {plan.next_due_date}",
                notification_type="maintenance_due",
                reference_type="maintenance_plan",
                reference_id=plan.id,
                send_email=True,
            )


# Singleton
notification_manager = NotificationManager()
