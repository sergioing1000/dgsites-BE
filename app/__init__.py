"""dgsites-BE application package.

Layered FastAPI backend that exposes NASA POWER weather data as JSON
and streaming Excel reports.  Sub-packages:

* ``routers``   — HTTP endpoint definitions.
* ``schemas``   — Pydantic request / response models.
* ``services``  — Business logic (NASA client, Excel generator).
* ``validators`` — Geographic and temporal constraint checks.
"""
