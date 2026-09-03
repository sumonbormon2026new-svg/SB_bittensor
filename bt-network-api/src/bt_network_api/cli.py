import argparse
from typing import Sequence

import uvicorn

from bt_network_api.app import create_app
from bt_network_api.settings import get_default_port


def main(argv: Sequence[str] | None = None) -> int:
    default_port = get_default_port()
    parser = argparse.ArgumentParser(description="Run the bt-network-api server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument(
        "--port", type=int, default=default_port, help=f"Bind port (default: {default_port})"
    )
    parser.add_argument("--network", default=None, help="Bittensor network name")
    parser.add_argument("--mock", action="store_true", help="Use mock data")
    args = parser.parse_args(argv)

    app = create_app(network=args.network, mock=args.mock)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
