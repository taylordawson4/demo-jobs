from nautobot.apps.jobs import register_jobs
jobs = [CreateLocationSiteDevice]
register_jobs(*jobs)
