# 固件与刷写注意

本项目只公开 Muse 功能模块和教程，不分发整机源码或整机 BIN。普通用户无需编译，去 [FoloToy 口袋百宝箱玩法页面](https://ai-passport.folotoy.cn/plays/438/) 安装包含 Muse 的版本，再返回 [使用教程](QUICKSTART.zh-CN.md)。

不要固定旧的 `?v=` 版本参数。页面需要明确说明该固件包含 Muse，且适用于同款 ESP32-C3 / 8 MB / ST7789P3 / ES8311 AI Passport；若维护者还没上传，先等待更新。本仓库的发布不代表官网已经更新。

准备数据 USB 线、电脑与设备，按官网说明备份、选正确设备并安装。刷机替换整个玩法，不是安装插件。已经能打开同版 Muse 则无需重刷；直接配 Wi-Fi、Token 和账号即可。官方 Jollybot 版对应集成固件 `0.2.0-rc.7`。

## 配置与恢复

维护者的 rc.7 `full.bin` 为写入 `0x0` 的合并镜像，里面包含空白 NVS，写入会覆盖 Wi-Fi、Muse 配置等区域；网页未勾“清除数据”也不能保证保留配置。不要全片擦除，不要把应用分段 BIN 当合并 BIN。

希望保留数据升级时，只使用官网或维护者明确提供、并核对分区相同的应用升级方式。本应用源码仓库没有整机刷写工具；不要因找不到 `flash.py` 就自行猜地址。原始 Flash 备份可能包含凭据，必须私下保存，不要上传 GitHub。

GitHub 的 Source code ZIP 是开发者源码，不含固件。随身语音的 Windows 程序也不能用来给 Muse 联网；Muse 网络和代理配置见 [NETWORK](NETWORK.zh-CN.md)。
