# backend/database/__init__.py

# Re-export ALL models from the models subpackage so SQLAlchemy registry knows them
from .models.user import User
from .models.subscription import Subscription
from .models.device import Device
from .models.user_profile import UserProfile
from .models.observatory_event import ObservatoryEvent
