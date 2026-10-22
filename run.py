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

# python run.py --demo        the demo school (instance-demo/), built on first use
# python run.py --demo-reset  rebuild it first, so streaks and due dates match today
DEMO = "--demo" in sys.argv or "--demo-reset" in sys.argv
if DEMO and __name__ == "__main__":
    from tatvax import demo

    os.environ["TATVAX_DEMO"] = "1"  # the demo bar, with one-click switching between accounts
    os.environ["TATVAX_INSTANCE_DIR"] = str(demo.DEFAULT_DIR)
    os.environ["TATVAX_DATABASE"] = str(demo.DEFAULT_DIR / "tatvax.db")
    rebuild = "--demo-reset" in sys.argv or not (demo.DEFAULT_DIR / "tatvax.db").exists()
    if rebuild and not os.environ.get("WERKZEUG_RUN_MAIN"):  # not again in the debug reloader's child
        print("Building the demo school...")
        demo.build(demo.DEFAULT_DIR, reset=True)

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("TATVAX_HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", os.environ.get("TATVAX_PORT", "5000")))
    debug = os.environ.get("TATVAX_DEBUG", "").lower() in {"1", "true", "yes"}
    print(f"TatvaX is running at http://{'localhost' if host in ('127.0.0.1', '0.0.0.0') else host}:{port}")
    if DEMO:
        print(f"Demo school: sign in with any account in {demo.DEFAULT_DIR / 'DEMO_ACCOUNTS.txt'} "
              f"(password: {demo.DEMO_PASSWORD}), for example principal@sunrise.school")
    if not (app.config["FRONTEND_DIST"] / "index.html").exists():
        print("The React frontend isn't built yet: run `npm install` and `npm run build` in frontend/")
    app.run(host=host, port=port, debug=debug, threaded=True)
