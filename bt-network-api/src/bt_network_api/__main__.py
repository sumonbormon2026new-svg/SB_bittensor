import uvicorn

from bt_network_api.app import create_app

if __name__ == "__main__":
    uvicorn.run(create_app(), host="0.0.0.0", port=8091, log_level="info")
