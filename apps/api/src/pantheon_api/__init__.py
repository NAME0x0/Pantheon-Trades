"""Pantheon Trades API gateway.

FastAPI application serving the dashboard + admin surfaces. Owns the
authoritative copy of every service's published artifacts via Postgres
+ Redis stream consumers and renders them through typed Pydantic
response models.
"""

__version__ = "0.1.0"
