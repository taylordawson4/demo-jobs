from nautobot.apps.jobs import register_jobs
from .custom_field import CreateLocationSiteDevice

jobs = [CreateLocationSiteDevice]
register_jobs(*jobs)
