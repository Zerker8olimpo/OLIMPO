# backend/database/models/__init__.py

# Import ALL models so SQLAlchemy registry knows them
from .user import User
from .subscription import Subscription
from .device import Device
from .user_profile import UserProfile