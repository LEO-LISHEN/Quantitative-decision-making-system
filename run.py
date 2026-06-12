import os

import uvicorn
from dotenv import load_dotenv


if __name__ == "__main__":
    load_dotenv(encoding="utf-8-sig")
    uvicorn.run(
        "app.main:app",
        host=os.getenv("APP_HOST", "127.0.0.1"),
        port=int(os.getenv("APP_PORT", "8010")),
        reload=False,
    )
