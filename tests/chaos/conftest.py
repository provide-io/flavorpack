from hypothesis import HealthCheck, settings

settings.register_profile(
    "chaos",
    deadline=None,
    suppress_health_check=(HealthCheck.filter_too_much, HealthCheck.too_slow),
)
settings.load_profile("chaos")
