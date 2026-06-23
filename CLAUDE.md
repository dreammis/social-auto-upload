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

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Install Playwright browser drivers:**
    ```bash
    playwright install chromium
    ```

3.  **Initialize the database:**
    ```bash
    python db/createTable.py
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

To use the CLI, you can run the `cli_main.py` script with the appropriate arguments.

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
sau douyin upload --account <account_name> --file <video_file> --title <title> [--tags tag1,tag2] [--schedule YYYY-MM-DD HH:MM]
```

**Install bundled skill:**

```bash
sau skill install
```

## Development Conventions

*   Current mainline code is in `sau_cli.py`, `uploader/`, `skills/`, and `docs/CLI.md`.
*   The optional React frontend is located in `sau_web/frontend`.
*   The historical Vue frontend `sau_frontend/` has been removed.
*   The project uses a SQLite database for data storage. The database file is located at `db/database.db`.
*   The `conf.example.py` file should be copied to `conf.py` and configured with the appropriate settings.
*   The `requirements.txt` file lists the Python dependencies.
*   The `sau_web/frontend/package.json` file lists the React frontend dependencies.
