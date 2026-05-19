# std python
# 3rd party
import uvicorn

# local
from dipworkpy.api_app import app

if __name__ == "__main__":
    # api_app mounts the modern routers (/syntax, /geography, /conflict,
    # /round) plus the root '/'. The legacy /dip_eval is still reachable
    # at the package-root app in dipworkpy/__init__.py for backward compat.
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8444,
        log_level="trace",
    )
