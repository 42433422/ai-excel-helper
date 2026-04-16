import uvicorn

from modstore_server.constants import DEFAULT_API_HOST, DEFAULT_API_PORT

if __name__ == "__main__":
    uvicorn.run(
        "modstore_server.app:app",
        host=DEFAULT_API_HOST,
        port=DEFAULT_API_PORT,
        reload=True,
    )
