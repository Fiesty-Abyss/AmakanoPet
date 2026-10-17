# 更新日志

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.2.1] - 2026-10-17

### 修复（Live2D 兼容性）

- 有些模型没有定义 `EyeBlink` 参数组（为 VTube Studio 面捕制作的模型很常见），以前不会眨眼。现在只要模型有 `ParamEyeLOpen` / `ParamEyeROpen`，就由 AmakanoPet 驱动眨眼。
- 没有动作文件的模型，单击时改为随机显示模型自带的表情（2.5 秒后恢复）。

### 新增

- 没有 `avatar` 的 Live2D 模型，首次显示后自动截取头部作为乐园卡片和资料页的头像（缓存在系统缓存目录，模型文件变化后会重新生成）。
- `tools/capture_screenshots.py --live2d <模型文件夹>`：为 Live2D 模型截取桌宠、我的模型、角色一览、资料页的实际运行画面。
- `.gitignore` 和测试会防止模型文件（`*.moc3`、`*.model3.json`、`*.vtube.json` 等）、压缩包和 `private-models/` 被提交。
- README：在「社区模型」中加入 Jim_Milton 制作的柳木诗梦 Live2D 模型的运行截图（只有截图，不含模型文件）；新增「支持正版」章节。

## [0.2.0] - 2026-10-17

### 新增

- 可选的 Live2D 支持：安装 `live2d-py`（Python 3.11+）后，可以显示用户自备的 Cubism 2 / 3+ 模型。
  - 在共享的离屏 OpenGL 上下文中渲染，桌宠窗口保持透明。
  - 模型自带呼吸、眨眼和物理；单击播放 `TapBody` 动作；视线跟随鼠标。
- `pet.json` 新增 `live2d.model` / `zoom` / `offset`；未写 `pet.json` 时自动识别 Live2D 模型文件夹。
- 模型加载失败时自动换回糯糯，并在「我的模型」页显示原因。
- `requirements-live2d.txt` 与 `pip install amakanopet[live2d]` 可选依赖。
- `tools/fetch_live2d_sample.sh`：在测试时下载 Live2D 官方免费示例模型，存放在被 git 忽略的目录中。
- CI 新增 Live2D 任务（Xvfb），渲染官方免费示例模型；示例模型不进入仓库。

### 变更

- 未安装 live2d-py 时，Live2D 模型显示安装提示，不再提示“计划支持”。

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

[0.2.1]: https://github.com/Fiesty-Abyss/AmakanoPet/releases/tag/v0.2.1
[0.2.0]: https://github.com/Fiesty-Abyss/AmakanoPet/releases/tag/v0.2.0
[0.1.0]: https://github.com/Fiesty-Abyss/AmakanoPet/releases/tag/v0.1.0
