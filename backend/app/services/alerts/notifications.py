"""Notification adapters. Real SMS/email/push only if explicitly configured."""

from __future__ import annotations

import logging
from typing import Protocol

from app.core.config import settings

log = logging.getLogger(__name__)


class NotificationProvider(Protocol):
    channel: str

    def send(self, title: str, message: str, meta: dict | None = None) -> dict: ...


class DashboardNotificationProvider:
    channel = "dashboard"

    def send(self, title: str, message: str, meta: dict | None = None) -> dict:
        return {"channel": self.channel, "delivered": True, "mode": "dashboard", "title": title}


class EmailNotificationProvider:
    channel = "email"

    def send(self, title: str, message: str, meta: dict | None = None) -> dict:
        live = bool(settings.enable_real_email and settings.smtp_host)
        if live:
            log.warning("Real email is configured but no SMTP client is wired; refusing to send.")
            return {"channel": self.channel, "delivered": False, "mode": "refused_unwired", "title": title}
        log.info("Mock email (not sent): %s", title)
        return {"channel": self.channel, "delivered": False, "mode": "mock", "title": title}


class SMSNotificationProvider:
    channel = "sms"

    def send(self, title: str, message: str, meta: dict | None = None) -> dict:
        live = bool(settings.enable_real_sms and settings.sms_api_key)
        if live:
            log.warning("Real SMS is configured but no carrier client is wired; refusing to send.")
            return {"channel": self.channel, "delivered": False, "mode": "refused_unwired", "title": title}
        log.info("Mock SMS (not sent): %s", title)
        return {"channel": self.channel, "delivered": False, "mode": "mock", "title": title}


class MobilePushNotificationProvider:
    channel = "mobile_push"

    def send(self, title: str, message: str, meta: dict | None = None) -> dict:
        live = bool(settings.enable_real_push and settings.push_api_key)
        if live:
            log.warning("Real push is configured but no FCM/APNs client is wired; refusing to send.")
            return {"channel": self.channel, "delivered": False, "mode": "refused_unwired", "title": title}
        log.info("Mock push (not sent): %s", title)
        return {"channel": self.channel, "delivered": False, "mode": "mock", "title": title}


def default_providers() -> list[NotificationProvider]:
    return [
        DashboardNotificationProvider(),
        EmailNotificationProvider(),
        SMSNotificationProvider(),
        MobilePushNotificationProvider(),
    ]


def dispatch(alert, providers: list[NotificationProvider] | None = None) -> list[dict]:
    text = f"{alert.title}: {alert.message}"
    receipts = []
    for p in providers or default_providers():
        receipts.append(p.send(alert.title, text, {"id": alert.id, "severity": alert.severity}))
    return receipts
