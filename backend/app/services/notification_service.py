from sqlalchemy.orm import Session

from app.models import Notification, NotificationType, User, UserRole


def notify_company_users(
    db: Session,
    company_id: int,
    notification_type: NotificationType,
    title: str,
    message: str,
    entity_ref: str | None = None,
    roles: list[UserRole] | None = None,
) -> None:
    query = db.query(User).filter(User.company_id == company_id, User.is_active == True)
    if roles:
        query = query.filter(User.role.in_(roles))
    for user in query.all():
        db.add(Notification(
            user_id=user.id,
            company_id=company_id,
            notification_type=notification_type,
            title=title,
            message=message,
            entity_ref=entity_ref,
        ))
    db.commit()


def notify_platform_owners(
    db: Session,
    notification_type: NotificationType,
    title: str,
    message: str,
    entity_ref: str | None = None,
) -> None:
    owners = db.query(User).filter(User.role == UserRole.platform_owner, User.is_active == True).all()
    for user in owners:
        db.add(Notification(
            user_id=user.id,
            notification_type=notification_type,
            title=title,
            message=message,
            entity_ref=entity_ref,
        ))
    db.commit()


def notify_user(
    db: Session,
    user_id: int,
    notification_type: NotificationType,
    title: str,
    message: str,
    entity_ref: str | None = None,
    company_id: int | None = None,
) -> None:
    db.add(Notification(
        user_id=user_id,
        company_id=company_id,
        notification_type=notification_type,
        title=title,
        message=message,
        entity_ref=entity_ref,
    ))
    db.commit()
