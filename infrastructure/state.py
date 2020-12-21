from typing import Optional

from data.users import User
import services.data_service as svc

active_account: Optional[User] = None


def reload_account():
    global active_account
    if not active_account:
        return

    active_account = svc.find_account_by_email(active_account.email)
