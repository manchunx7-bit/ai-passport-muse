# AI Passport Muse

在 AI Passport 上按住上键说话、松开发送，并查看 Muse 的文字回复。需要自己的 Muse 账号、SDK Token、手机配对，以及设备可用的网络。

**本仓库只开源 Muse 功能，不包含整机源码、其他应用或预编译整机固件。** 普通用户从 [FoloToy 口袋百宝箱玩法页面](https://ai-passport.folotoy.cn/plays/438/) 安装包含 Muse 的固件，再按本仓库教程配置即可；无需编程、VB-CABLE 或微信输入法。

官网维护者尚未上传含 Muse 的版本时，请等待页面更新。GitHub 发布项目不代表官网固件已经更新，Source code ZIP 不能刷机。

## 普通用户：从安装到第一次回复

1. 同款 FoloToy AI Passport（ESP32-C3 / 8 MB / ES8311）先按 [固件说明](docs/FIRMWARE.zh-CN.md) 安装官网固件。已有同版 Muse 则跳过。
2. 在 [Muse Gadget 官方网站](https://gadgets.muse.ai/) 申请自己的 SDK Token，并准备已登录的手机 Muse。账号资格以官方为准。
3. 设备首页长按下键进入手机设置，手机连设备热点，打开屏幕地址（通常 `192.168.4.1`），填写 2.4 GHz Wi-Fi 和本人 Token。
4. 设备不能直连时，按 [网络与代理教程](docs/NETWORK.zh-CN.md) 设置自己的电脑 IPv4、HTTP/混合代理端口。不要填作者地址、SOCKS-only 或管理端口。
5. 完成设置后退出设备热点，打开设备 Muse；在手机 Muse 开发者模式中添加设备，并按硬件确定键确认。
6. 等待“我准备好了”，按住上键说话、松开，等待文字回复后再发下一段。

每一步的完成标志、Token 留空保留规则、权限与重试路径见 [完整教程](docs/QUICKSTART.zh-CN.md)。已配对不等于云端网络可达，不要因普通连接失败反复清空授权。

## 按键和限制

- 按住上键录音，松开发送，单次最长 30 秒。
- 短按确定翻页；错误状态按确定重试。
- 短按下键取消本地录音/等待，不能撤回已提交云端的任务。
- 长按确定退出。错误页长按下键会清除配对；Token 与 Wi-Fi 是单独保存的配置。

本版是**语音输入、文字输出**，没有 TTS、额度查询或完整聊天历史。最新回复最多保存 1023 个 UTF-8 字节，长内容在手机查看。代理方案依赖电脑开机且 IP/端口可达；设备可直连时不需要电脑。

## 开源内容与开发者

| 目录 | 内容 |
| --- | --- |
| `device/main/apps/muse/` | Muse 应用界面、按键业务与原创几何机器人 |
| `device/components/passport_muse/` | Muse 生命周期、音频发送、配对、网络代理及 SDK 适配 |
| `device/components/noise_core/` | 本功能所需的上游 Noise 协议代码，保留 Apache-2.0 声明 |
| `device/tests/` | Muse 语音与会话协议测试 |
| `tools/` | 只针对本功能的测试和角色生成工具 |

没有首页/名片、收音机、小智、其他语音应用、游戏、秒表、整机入口、设置页和 BSP 实现，也没有旧整机 Git 历史。

**独立仓库不等于独立整机固件工程。** 设备模块需要自己的显示、按键、音频、Wi-Fi 和应用生命周期宿主接口；开发者按 [开发与适配说明](docs/DEVELOPMENT.zh-CN.md) 移植。当前提供可独立运行的协议 host 测试，不声称本仓库能单独执行 `idf.py build` 生成整机 BIN。

- [完整使用教程](docs/QUICKSTART.zh-CN.md)
- [网络排错](docs/NETWORK.zh-CN.md)
- [用本地 Codex 辅助配置](docs/CODEX_SETUP.zh-CN.md)
- [测试与验证边界](docs/VALIDATION.md)
- [来源与许可证](THIRD_PARTY_NOTICES.md)

本项目为社区适配，不代表 Meta/Muse 或 FoloToy 官方支持。使用本人账号，遵守服务条款；不要在 Issue、截图或日志中上传 Token、配对材料、个人网络资料或对话内容。
