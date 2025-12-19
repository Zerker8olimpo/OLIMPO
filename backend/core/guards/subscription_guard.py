from backend.core.errors import SubscriptionInactiveError
from backend.database.subscription_store import SubscriptionStore

def ensure_active_subscription(user, subs_store: SubscriptionStore):
    sub = subs_store.get_by_user_id(user.id)

    if not sub or sub["status"] != "active":
        raise SubscriptionInactiveError()

    return sub