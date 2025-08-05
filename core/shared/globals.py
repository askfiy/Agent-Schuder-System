from core.shared.middleware.context import g
from core.shared.database.redis import client
from core.shared.components import RBroker, RCacher

broker = RBroker(client)
cacher = RCacher(client)

__all__ = ["g", "broker", "cacher"]
