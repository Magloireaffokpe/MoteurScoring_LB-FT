from app.models.users import User


def can_rescore(user: User) -> bool:
    perms = user.role.permissions or {}
    return perms.get("can_rescore", False)


def can_export(user: User) -> bool:
    perms = user.role.permissions or {}
    return perms.get("can_export", False)


def can_manage_users(user: User) -> bool:
    perms = user.role.permissions or {}
    return perms.get("can_manage_users", False)


def can_configure(user: User) -> bool:
    perms = user.role.permissions or {}
    return perms.get("can_configure", False)