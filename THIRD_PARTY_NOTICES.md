# 来源和许可证

本仓库只覆盖 Muse 功能，根 MIT LICENSE 适用于本地新增应用集成、文档与原创角色。它不替代第三方组件许可证，也不授予未提供的整机代码或 Jollybot 美术权利。

- Muse Gadget SDK：[facebookincubator/muse-gadget-sdk](https://github.com/facebookincubator/muse-gadget-sdk)，基于 `4bd647bc805b2e0de49dc894c0680225ce29bd06`，Apache-2.0。完整原文位于 `device/components/passport_muse/LICENSE`，来源及修改说明位于对应 NOTICE。
- Noise 核心：同一 SDK 的协议实现，保留源码头与 `device/components/noise_core/NOTICE.md`。
- ESP32-C3 / HTTP CONNECT 适配参考：[RongleCat/ai-passport-muse](https://github.com/RongleCat/ai-passport-muse)，`fee6234e08cd0f8c90fbe8af2a6bdfad5d2808a0`，来源在组件 NOTICE 保留。
- 本仓库的角色帧由原创几何机器人生成工具产生；GitHub 源码包不分发官方 Jollybot 美术。
- 官网 `0.2.0-rc.7` 固件中的 Jollybot 编译帧来自上述官方 SDK，固件发布方确认已取得单独的公开分发权限。该素材不因此适用本仓库 MIT 许可证或 SDK Apache-2.0 许可证。
- cJSON 仅供测试时获取，使用 ESP-IDF 5.5.3 对应的 `c859b25da02955fef659d658b8f324b5cde87be3`；上游许可证仍适用。ESP-IDF、LVGL 等宿主依赖不打包进此源码项目。

这是社区适配，不是 Meta/Muse 或 FoloToy 官方固件；服务资格和账号条款以官方为准。Token、配对材料、Wi-Fi 和代理配置由设备主人在运行时提供。
