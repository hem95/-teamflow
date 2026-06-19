from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import settings

# The limiter tracks each visitor by their IP address and counts how many
# requests they make. We create it once here and import it everywhere so
# all routes share the same counter.
#
# get_remote_address = "identify each caller by their IP address"
#
# storage_uri points the counts at Redis instead of this process's memory.
# Why this matters: when you run several backend servers behind a load
# balancer, each one would otherwise keep its own private counter — so a
# "5 per minute" limit could secretly allow 5 × (number of servers). Storing
# the counts in Redis means all servers read and update one shared counter,
# so the limit is enforced correctly no matter how many servers you run.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
)
