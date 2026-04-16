import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "modrepo_server.app:app",
        host="127.0.0.1",
        port=8765,
        reload=True,
    )
