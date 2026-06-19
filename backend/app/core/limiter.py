from slowapi import Limiter
from slowapi.util import get_remote_address

# The limiter tracks each visitor by their IP address and counts how many
# requests they make. We create it once here and import it everywhere so
# all routes share the same counter.
#
# get_remote_address = "identify each caller by their IP address"
limiter = Limiter(key_func=get_remote_address)
