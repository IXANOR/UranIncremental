# Import all models here so Alembic can discover them via Base.metadata
from app.db.models.events import EventLog  # noqa: F401
from app.db.models.player_state import PlayerState  # noqa: F401
from app.db.models.unit import PlayerUnit, UnitDefinition  # noqa: F401
from app.db.models.upgrade import PlayerUpgrade, UpgradeDefinition  # noqa: F401
from app.db.models.wallet import Wallet  # noqa: F401
