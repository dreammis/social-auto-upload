use std::sync::Mutex;
use tauri::Manager;
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

// 持有后端 sidecar 子进程句柄 + pid，供退出时 kill
struct BackendProcess {
    child: Mutex<Option<CommandChild>>,
    pid: Mutex<Option<u32>>,
}

// 杀掉整棵进程树：sau-backend 还会派生 node.exe(playwright driver) 甚至 chrome，
// child.kill() 只杀直接子进程，会留下孤儿。Windows 用 taskkill /T /F 连子带孙一起杀。
#[cfg(windows)]
fn kill_tree(pid: u32) {
    use std::process::Command;
    let _ = Command::new("taskkill")
        .args(["/PID", &pid.to_string(), "/T", "/F"])
        .creation_flags(0x08000000) // CREATE_NO_WINDOW
        .status();
}

#[cfg(windows)]
use std::os::windows::process::CommandExt;

#[cfg(not(windows))]
fn kill_tree(_pid: u32) {}

fn kill_backend(app_handle: &tauri::AppHandle) {
    if let Some(state) = app_handle.try_state::<BackendProcess>() {
        // 先 taskkill 整棵树（带 node/chrome）
        if let Some(pid) = state.pid.lock().unwrap().take() {
            log::info!("[sidecar] 退出，kill 后端进程树 pid={}", pid);
            kill_tree(pid);
        }
        // 再 kill 句柄兜底
        if let Some(child) = state.child.lock().unwrap().take() {
            let _ = child.kill();
        }
    }
}

fn spawn_backend(app: &tauri::AppHandle) {
    match app.shell().sidecar("sau-backend") {
        Ok(cmd) => match cmd.spawn() {
            Ok((mut rx, child)) => {
                let pid = child.pid();
                log::info!("[sidecar] sau-backend 已启动 pid={}", pid);
                if let Some(state) = app.try_state::<BackendProcess>() {
                    *state.child.lock().unwrap() = Some(child);
                    *state.pid.lock().unwrap() = Some(pid);
                }
                // 消费 sidecar 的 stdout/stderr，避免管道塞满
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
        .manage(BackendProcess {
            child: Mutex::new(None),
            pid: Mutex::new(None),
        })
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
            // ExitRequested（最后一个窗口关闭/请求退出）和 Exit（事件循环结束）
            // 都 kill 后端，确保关窗即停、无残留
            match event {
                tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit => {
                    kill_backend(app_handle);
                }
                _ => {}
            }
        });
}
