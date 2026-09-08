#!/usr/bin/env python3
"""TradeQuest API entrypoint. The legacy unauthenticated server is retired."""

import argparse

from investolingo_backend import create_app, seed_demo

app = create_app()


def main(argv=None):
    parser = argparse.ArgumentParser(description="TradeQuest API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--seed-demo", action="store_true")
    args = parser.parse_args(argv)
    if args.seed_demo:
        seed_demo(app)
        print("Demo accounts ready; passwords were read from the environment.")
    else:
        import uvicorn
        uvicorn.run(app, host=args.host, port=args.port, proxy_headers=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
