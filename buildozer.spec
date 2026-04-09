[app]

# App 名称（英文，用于包名）
title = StockAnalysis

# 应用名称（显示在手机桌面）
package.name = stockanalysis

# 包名（Android 的 application id）
package.domain = com.stockmonitor

# 源码目录（相对于 spec 文件的位置）
source.dir = .

# 主程序入口
source.include_exts = py,png,jpg,kv,atlas,json

# 版本
version = 1.0

# 最低 Android 版本（API 21 = Android 5.0）
android.minapi = 21

# 目标 Android 版本
android.api = 33

# 支持的架构
android.archs = arm64-v8a, armeabi-v7a

# 需要的权限
android.permissions = INTERNET, ACCESS_NETWORK_STATE

# 依赖包（重要！）
requirements = python3,kivy,requests

# 打包模式
orientation = portrait

# 全屏模式
fullscreen = 0

# 图标文件（可选，如果有的话）
# icon.filename = icon.png

# 启动画面图片（可选）
# splashscreen.filename = splash.png

# Android manifest 配置
android.meta_data = com.google.android.gms.version @integer/google_play_services_version

# 禁用 P4A 兼容性（如果遇到奇怪的错误可以尝试开启）
# p4a.bootstrap = sdl2

[buildozer]

# 日志级别
log_level = 2

# 是否显示编译警告
warn_on_root = 1

# Buildozer 的仓库
# buildozer.spec_title = StockAnalysis
# buildozer.spec_author = Your Name
# buildozer.spec_license = MIT

# Android SDK 路径（留空则自动下载）
# android.sdk_path = /path/to/android/sdk

# NDK 路径（留空则自动下载）
# android.ndk_path = /path/to/android/ndk

# Android NDK 版本
android.ndk_api = 21

# Android NDK 的 GCC 版本
android.ndk_gcc_version = 4.9

# 是否允许 buildozer 自动更新已下载的 SDK/NDK
android.allow_redeploy = 1

# 是否允许在打包后重新安装 APK 到设备
android.install_referrer = 

# 是否在打包完成后自动运行 APK
android.do_launch = 1

# Android 是否预装 Google Play 服务
android.playstore_merge = 

# 本地仓库路径（用于离线打包）
# local_repositories = 

# Android Gradle 版本
android.gradle_version = 7.4.2

# 是否在打包时清理旧的 build 文件
android.clean_build = 1
