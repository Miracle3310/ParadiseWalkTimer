# ParadiseWalkTimer

ParadiseWalkTimer 是一个运行在 Windows 上的微信小程序自动签到工具，默认用于“龙湖天街”小程序。

工具通过桌面 UI 自动化打开微信小程序、进入会员页面、识别签到入口并确认签到结果。它支持每日定时执行、锁屏后解锁补签、失败桌面通知，以及本地日志和截图记录。

## 功能

- 从微信小程序页面识别并打开“龙湖天街”
- 进入会员页面并识别“去签到”按钮
- 检测已签到或签到成功状态
- 锁屏时记录待补签状态，解锁后重试
- 失败时显示桌面通知并保存本地诊断信息
- 提供不点击签到按钮的 `dry-run` 模式

## 环境

- Windows 10 或 Windows 11
- 已登录并保持在线的电脑微信
- Python 3.10 或更高版本

## 安装

```powershell
.\scripts\setup.ps1
```

## 使用

检查页面定位，不点击签到：

```powershell
.\.venv\Scripts\python.exe .\run_checkin.py --mode dry-run
```

执行签到：

```powershell
.\.venv\Scripts\python.exe .\run_checkin.py --mode scheduled --force
```

注册每日签到和解锁补签计划任务：

```powershell
.\scripts\install_tasks.ps1
```

删除计划任务：

```powershell
.\scripts\uninstall_tasks.ps1
```

## 配置

主要配置位于 `config.yaml`，包括小程序名称、运行时间、窗口识别参数、图片模板和匹配阈值。

## 本地数据

运行日志、状态文件、失败截图、诊断截图、虚拟环境和本地配置文件不会纳入 Git 版本管理。
