# HiveWatch control room (Member 1)

A local web page that runs the demo and shows the results. The terminal demo
(`scripts/run_demo.sh`) works without it.

    source .venv/bin/activate
    pip install fastapi uvicorn
    python3 ui/server.py
    # open http://127.0.0.1:8000 in your browser

It listens on 127.0.0.1 only and runs only `scripts/run_demo.sh` and `docker compose ps`.
