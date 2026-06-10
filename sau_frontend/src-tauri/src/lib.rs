use std::sync::Mutex;
use tauri::Manager;
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

// 持有后端 sidecar 子进程句柄，供退出时 kill
struct BackendProcess(Mutex<Option<CommandChild>>);

fn spawn_backend(app: &tauri::AppHandle) {
    match app.shell().sidecar("sau-backend") {
        Ok(cmd) => match cmd.spawn() {
            Ok((mut rx, child)) => {
                log::info!("[sidecar] sau-backend 已启动");
                // 把子进程句柄存起来，退出时 kill
                if let Some(state) = app.try_state::<BackendProcess>() {
                    *state.0.lock().unwrap() = Some(child);
                }
                // 消费 sidecar 的 stdout/stderr，避免管道塞满
                let app_handle = app.clone();
                tauri::async_runtime::spawn(async move {
                    use tauri_plugin_shell::process::CommandEvent;
                    while let Some(event) = rx.recv().await {
                        match event {
                            CommandEvent::Stdout(line) => {
                                log::info!("[sidecar] {}", String::from_utf8_lossy(&line));
                            }
                            CommandEvent::Stderr(line) => {
                                log::warn!("[sidecar] {}", String::from_utf8_lossy(&line));
                            }
                            CommandEvent::Terminated(payload) => {
                                log::warn!("[sidecar] 后端退出: {:?}", payload);
                                break;
                            }
                            _ => {}
                        }
                    }
                    let _ = app_handle;
                });
            }
            Err(e) => log::error!("[sidecar] 启动后端失败: {}", e),
        },
        Err(e) => log::error!("[sidecar] 找不到 sau-backend sidecar: {}", e),
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(BackendProcess(Mutex::new(None)))
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            spawn_backend(app.handle());
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while running tauri application")
        .run(|app_handle, event| {
            // 应用退出时 kill 后端 sidecar，避免残留进程
            if let tauri::RunEvent::ExitRequested { .. } = event {
                if let Some(state) = app_handle.try_state::<BackendProcess>() {
                    if let Some(child) = state.0.lock().unwrap().take() {
                        log::info!("[sidecar] 退出，kill 后端");
                        let _ = child.kill();
                    }
                }
            }
        });
}
