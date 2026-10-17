# 更新日志

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.1.0] - 2026-10-17

首个公开版本。

### 新增

- 精灵渲染器：呼吸、上下浮动、随机眨眼（含偶发双眨），单击小跳。
- 原创占位吉祥物「糯糯」，由代码绘制，随季节主题换装；托盘图标也由它绘制。
- 用户模型文件夹扫描与 `pet.json`（format 1）清单，支持闭眼帧、头像、缩放、角色绑定，带路径越界与文件校验；文档见 `docs/MODEL_FORMAT.md`。
- 乐园窗口：7 部作品页签 → 16 位女主角卡片 → 角色资料页（资料为自行撰写，附来源链接，仅含全年龄内容）。
- 季节主题：甜点 / 冬 / 秋 / 夏，按作品自动切换，也可在设置中固定。
- 托盘菜单：显示/隐藏、打开乐园、切换桌宠、重新扫描、退出。
- 设置持久化：位置、大小、当前模型、模型文件夹、置顶、动画、主题、上次页签。
- `tools/make_demo_model.py` 示例模型生成脚本、`tools/capture_screenshots.py` 截图脚本。
- MIT 许可证、免责声明、GitHub Actions（ruff + Python 3.10/3.12/3.13 离屏测试）。

### 移除

- 早期的连接测试文件 `test_connection.txt`。

[0.1.0]: https://github.com/Fiesty-Abyss/AmakanoPet/releases/tag/v0.1.0
