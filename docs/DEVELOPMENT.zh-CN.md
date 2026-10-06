# Muse 功能模块开发

本仓库是应用模块，不是整机 ESP-IDF 工程。普通用户从官网刷入含 Muse 的固件，再按使用教程配置；不用编译。本仓库不包含整机入口、BSP、手机设置实现、共享字体或启动器。

## 目录与依赖

- `device/components/passport_muse/`：配对、授权、HTTP CONNECT、实时通信、录音提交、回复同步和资源生命周期。
- `device/components/noise_core/`：上游 Noise 实现及本地 ESP-IDF 组件声明。
- `device/main/apps/muse/`：单个 Muse 应用的界面和按键业务、角色帧接口，以及原创几何回退素材。
- `device/tests/`：聊天协议/故障注入、音频 WAV/base64/UTF-8 与可选加密回归测试。

生产代码对应 ESP-IDF 5.5.3、LVGL 9.5；SDK 来源 commit 和修改说明保留在组件 NOTICE 中。自己移植时需审查内存预算、生命周期和许可证，不能把 PC host 测试当作设备验收。

## 独立运行 host 测试

需要 Bash、Python 3、C 编译器和 cJSON 源码。在 Linux/WSL 的仓库根目录运行。已有 ESP-IDF 5.5.3 时：

```bash
source /你的路径/esp-idf/export.sh
bash tools/test-host.sh
```

若只跑本功能测试、不装整套 ESP-IDF，可以准备同一版 cJSON（首次执行，目录应不存在）：

```bash
git clone https://github.com/DaveGamble/cJSON.git .deps/idf/components/json/cJSON
git -C .deps/idf/components/json/cJSON checkout c859b25da02955fef659d658b8f324b5cde87be3
IDF_PATH="$PWD/.deps/idf" bash tools/test-host.sh
```

脚本编译真实聊天实现及音频辅助函数，运行 11 项会话场景和 WAV/base64/UTF-8 边界测试，不连接账号、不发送录音。`test_muse_inplace.cpp` 是保留的可选加密测试，需要额外 mbedTLS/PSA 构建环境，不属于默认 host 脚本已验收范围。

## 接入自己的宿主固件

1. 在自己的 ESP-IDF 工程加入两个组件目录，保留原有许可证和 NOTICE。先准备组件声明所需的 `bsp`、`esp-wifi-connect` 等宿主接口或相应适配，不能直接在此仓库根目录运行 `idf.py build`。
2. `passport_muse.h` 提供 start/stop、上键按下/松开、取消、配对确认、清配对、状态快照等 API。让单个应用拥有生命周期，退出时等待工作线程结束；不要跨线程随意调用底层会话函数。
3. `bsp_audio.h` 由宿主实现录音格式与 PCM 读写/关闭；`wifi_manager.h` 由宿主提供实际网络状态。ESP-IDF 的 NVS、FreeRTOS、TLS、BLE、lwIP 等使用公开依赖。
4. `app_muse.cc` 另外依赖 `apps/app_base.h`、`launcher/app_registry.h`、`bsp_display.h`、`bsp_battery.h`、`app_fonts.h`、`ui_pixel.h`。这些维护者整机实现不在本仓库；在你自己的宿主中定义等价接口，或重写这一层界面。
5. 提供安全的运行时配置入口：本人 Token、可选 IPv4 HTTP CONNECT 代理、Wi-Fi。参考组件中的 NVS 行为，不把真实 Token、Wi-Fi 或代理地址写进源码；更换 Token 与只改代理的配对处理不同。
6. 完成实际配对、真实语音提交、文字回复、取消、退出重进、断网恢复，再记录内存与任务退出情况。不能只凭“手机已有设备”就宣布链路通过。

这些是接入责任说明，不是已实现的独立宿主。共享字体、设置网页、驱动和其他应用不会为了消除编译依赖而自动加入开源范围。

## 角色素材

`tools/generate_avatar.py` 使用 Pillow 生成本项目原创几何机器人。执行会覆盖对应生成帧，请先提交或备份自己的改动。GitHub 源码包未收录官方 Jollybot 美术；官网固件中的 Jollybot 编译帧由发布方依据单独取得的公开分发权限提供，不属于本仓库 MIT 许可证范围。
