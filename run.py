"""Start TatvaX locally:  python run.py

For production use a WSGI server instead, for example:
    gunicorn "run:app" --worker-class gthread --threads 8
"""

import os
import sys

from tatvax import create_app

# Windows consoles default to a legacy code page; make log output UTF-8 safe.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("TATVAX_HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", os.environ.get("TATVAX_PORT", "5000")))
    debug = os.environ.get("TATVAX_DEBUG", "").lower() in {"1", "true", "yes"}
    print(f"TatvaX is running at http://{'localhost' if host in ('127.0.0.1', '0.0.0.0') else host}:{port}")
    if not (app.config["FRONTEND_DIST"] / "index.html").exists():
        print("The React frontend isn't built yet: run `npm install` and `npm run build` in frontend/")
    app.run(host=host, port=port, debug=debug, threaded=True)
