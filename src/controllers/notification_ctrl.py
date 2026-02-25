from datetime import datetime

from src.controllers.ctrl_types import Notification, NotificationType


class NotificationCtrl:
    _latest_notification: Notification | None

    def __init__(self):
        self._latest_notification = None

    def set_notification_to_none(self):
        self._latest_notification = None

    def set_notification(
        self,
        typ: NotificationType,
        job_id: int,
        command_id: int | None = None,
        project_id: int | None = None,
    ):
        n = Notification(
            type_of_notification=typ,
            job_id=job_id,
            cmd_id=command_id if command_id is not None else -1,
            project_id=project_id if project_id is not None else -1,
            created_at=datetime.now(),
        )
        self._latest_notification = n

    def get_notification(self) -> Notification | None:
        return self._latest_notification
