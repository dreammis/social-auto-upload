## Project Overview

This project, `social-auto-upload`, automates publishing video content to multiple domestic and international mainstream social media platforms.

The current mainline is the Python CLI/backend implementation under `sau_cli.py`, `uploader/`, and `skills/`. The legacy Web stack (`sau_backend.py`, `sau_backend/`) has been moved to `legacy/` and is not the active entrypoint.

**Web Shell (optional React frontend):**

*   Directory: `sau_web/frontend`
*   Backend: `web_runner.py` (Flask, wraps CLI)
*   Framework: React + TypeScript
*   Build Tool: Vite
*   Start: `bash sau_web/start.sh`
*   Docs: `docs/web-shell.md`
*   Note: prefer the CLI unless you are actively working on the React frontend.

**Command-line Interface:**

The project also provides a command-line interface (CLI) for users who prefer to work from the terminal. For new Douyin CLI work, prefer the `sau douyin ...` entrypoint over legacy example scripts.

*   `login`: To log in to the Douyin uploader account.
*   `check`: To verify whether the saved Douyin cookie is still valid.
*   `upload`: To upload one video file with explicit metadata flags.

## Building and Running

### Backend

> 当前主线使用 `uv` + `pyproject.toml` 管理依赖，使用 `patchright` 驱动浏览器，数据库初始化已在 `web_runner/db.py` 中集成（首次启动 `web_runner.py` 时自动建表）。**`requirements.txt` 和 `db/createTable.py` 仅作历史兼容用途，新用户请直接按下方命令走。**

1.  **Install dependencies (推荐 `uv`，回退 `pip` 时使用 `-e` 安装 `pyproject.toml`):**
    ```bash
    uv pip install -e .
    # 或： pip install -e .
    ```

2.  **Install Playwright-compatible browser drivers (`patchright`，国内镜像):**
    ```bash
    patchright install chromium
    # Windows PowerShell 用 npmmirror: $env:PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright"; patchright install chromium
    ```

3.  **Initialize the database (首次启动 `web_runner.py` 时自动完成，无需手动执行):**
    ```bash
    python web_runner.py   # 自动调用 web_runner/db.py::init_db()
    ```

4.  **Run the Web Shell (React + Flask UI):**
    ```bash
    bash sau_web/start.sh
    ```
    Or start the Python backend separately:
    ```bash
    python web_runner.py
    ```
    The Web Shell runs on `http://localhost:5174` (frontend) with API proxy to backend on port 6001.

### Frontend (optional React web UI)

1.  **Navigate to the frontend directory:**
    ```bash
    cd sau_web/frontend
    ```

2.  **Install dependencies:**
    ```bash
    npm install
    ```

3.  **Run the development server:**
    ```bash
    npm run dev
    ```
    The frontend development server will start on `http://localhost:5174`.

### Command-line Interface

`uv pip install -e .` 安装后，会在虚拟环境里注册 `sau` 入口（当前主入口为 `sau_cli.py` / `cli/` 包）。本地开发时也可直接：

```bash
python sau_cli.py douyin login --account <account_name>
```

**Login:**

```bash
sau douyin login --account <account_name>
```

**Check:**

```bash
sau douyin check --account <account_name>
```

**Upload:**

```bash
sau douyin upload-video --account <account_name> --file <video_file> --title <title> [--tags tag1,tag2] [--schedule YYYY-MM-DD HH:MM]
```

**Install bundled skill:**

```bash
sau skill install
```

## Development Conventions

*   Current mainline code is in `sau_cli.py` / `cli/`, `uploader/`, `skills/`, and `docs/CLI.md`.
*   The optional React frontend is located in `sau_web/frontend`.
*   The historical Vue frontend `sau_frontend/` has been removed.
*   The project uses a SQLite database for data storage. The database file is located at `db/database.db`.
*   The `conf.example.py` file should be copied to `conf.py` and configured with the appropriate settings.
*   The `requirements.txt` file lists the Python dependencies.
*   The `sau_web/frontend/package.json` file lists the React frontend dependencies.
