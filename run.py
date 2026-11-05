"""启动器：读取 PORT 环境变量并绑定 0.0.0.0（云端部署注入 PORT；本地默认 8790）。"""
import os

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8790"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
