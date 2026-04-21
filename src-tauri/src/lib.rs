// src-tauri/src/lib.rs
// VOC Collector v1.5 — Tauri sidecar 관리 + Tauri commands

use std::sync::Mutex;
use tauri::{AppHandle, Emitter, Manager};
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::{CommandChild, CommandEvent};

/// 앱 전역 상태: 백엔드 API 포트 + sidecar 프로세스 핸들
struct AppState {
    api_port: Mutex<Option<u16>>,
    backend_child: Mutex<Option<CommandChild>>,
}

/// 백엔드 포트 반환 (프론트엔드에서 invoke로 호출)
#[tauri::command]
fn get_api_port(state: tauri::State<AppState>) -> Result<u16, String> {
    state
        .api_port
        .lock()
        .map_err(|e| e.to_string())?
        .ok_or_else(|| "Backend not ready yet".to_string())
}

/// 백엔드 상태 문자열 반환
#[tauri::command]
fn get_backend_status(state: tauri::State<AppState>) -> String {
    match *state.api_port.lock().unwrap() {
        Some(port) => format!("running:{}", port),
        None => "starting".to_string(),
    }
}

/// 백엔드 sidecar 강제 종료 (앱 종료 / 제거 시 호출)
///
/// 1차: CommandChild::kill() — Tauri sidecar API 경유
/// 2차: taskkill /F — Windows API 직접 호출 (1차가 타이밍 이슈로 실패해도 보장)
/// 중복 호출 안전: backend_child.take()로 첫 호출 이후 None이 됨
fn kill_backend(app: &AppHandle) {
    let state = app.state::<AppState>();
    let child = {
        match state.backend_child.lock() {
            Ok(mut g) => g.take(),
            Err(_) => return,
        }
    };
    if let Some(c) = child {
        let _ = c.kill();
        println!("[VOC] 백엔드 프로세스 종료 신호 전송");
    }
    // 폴백: taskkill /F로 확실하게 종료 (TerminateProcess 타이밍 이슈 대비)
    let _ = std::process::Command::new("taskkill")
        .args(["/F", "/IM", "voc-backend.exe", "/T"])
        .output();
}

pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .manage(AppState {
            api_port: Mutex::new(None),
            backend_child: Mutex::<Option<CommandChild>>::new(None),
        })
        .invoke_handler(tauri::generate_handler![get_api_port, get_backend_status])
        .setup(|app| {
            let handle = app.handle().clone();
            start_backend(handle);

            // 업데이터: 앱 시작 시 백그라운드에서 업데이트 확인
            let updater_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                check_for_updates(updater_handle).await;
            });

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    // 앱 종료 이벤트에서 백엔드 종료
    // Exit: 정상 종료 / ExitRequested: 강제 종료·OS 신호 포함
    app.run(|app_handle, event| {
        match event {
            tauri::RunEvent::Exit => {
                kill_backend(app_handle);
            }
            tauri::RunEvent::ExitRequested { .. } => {
                kill_backend(app_handle);
            }
            _ => {}
        }
    });
}

/// voc-backend.exe sidecar 시작
/// stdout에서 "VOC_READY:{port}" 라인을 파싱하여 포트를 저장하고
/// 프론트엔드에 "backend-ready" 이벤트를 emit한다.
fn start_backend(handle: AppHandle) {
    tauri::async_runtime::spawn(async move {
        let shell = handle.shell();

        let (mut rx, child) = match shell.sidecar("voc-backend") {
            Ok(cmd) => match cmd.spawn() {
                Ok(result) => result,
                Err(e) => {
                    eprintln!("[VOC] sidecar spawn 실패: {}", e);
                    return;
                }
            },
            Err(e) => {
                eprintln!("[VOC] sidecar 생성 실패: {}", e);
                return;
            }
        };

        // Child 핸들을 AppState에 보관 — Exit 이벤트에서 kill() 호출용
        {
            let state = handle.state::<AppState>();
            *state.backend_child.lock().unwrap() = Some(child);
        }

        // stdout / stderr 이벤트 처리
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    let line = String::from_utf8_lossy(&bytes);
                    let line = line.trim();

                    // "VOC_READY:{port}" 파싱
                    if let Some(port_str) = line.strip_prefix("VOC_READY:") {
                        if let Ok(port) = port_str.trim().parse::<u16>() {
                            {
                                let state = handle.state::<AppState>();
                                *state.api_port.lock().unwrap() = Some(port);
                            }
                            if let Err(e) = handle.emit("backend-ready", port) {
                                eprintln!("[VOC] emit backend-ready 실패: {}", e);
                            }
                            println!("[VOC] 백엔드 준비 완료 — port {}", port);
                        }
                    }
                }
                CommandEvent::Stderr(bytes) => {
                    let line = String::from_utf8_lossy(&bytes);
                    eprintln!("[VOC-backend] {}", line.trim());
                }
                CommandEvent::Error(e) => {
                    eprintln!("[VOC] sidecar 오류: {}", e);
                    break;
                }
                CommandEvent::Terminated(status) => {
                    println!("[VOC] 백엔드 종료: {:?}", status);
                    break;
                }
                _ => {}
            }
        }
    });
}

/// 자동 업데이트 확인 (비동기)
async fn check_for_updates(handle: AppHandle) {
    use tauri_plugin_updater::UpdaterExt;

    match handle.updater() {
        Ok(updater) => {
            match updater.check().await {
                Ok(Some(update)) => {
                    println!("[VOC] 업데이트 가능: {}", update.version);
                    if let Err(e) = update.download_and_install(|_, _| {}, || {}).await {
                        eprintln!("[VOC] 업데이트 설치 실패: {}", e);
                    }
                }
                Ok(None) => {
                    println!("[VOC] 최신 버전입니다");
                }
                Err(e) => {
                    eprintln!("[VOC] 업데이트 확인 실패: {}", e);
                }
            }
        }
        Err(e) => {
            eprintln!("[VOC] 업데이터 초기화 실패: {}", e);
        }
    }
}
