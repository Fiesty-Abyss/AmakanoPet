# 模型文件夹格式（format 1）

AmakanoPet 不附带任何角色立绘。桌宠形象由用户放在**模型文件夹**中，程序启动或点击「重新扫描」时读取。

## 模型文件夹在哪里

| 系统 | 默认位置 |
|---|---|
| Windows | `%APPDATA%\AmakanoPet\models` |
| macOS | `~/Library/Application Support/AmakanoPet/models` |
| Linux | `~/.local/share/AmakanoPet/models` |

可以在乐园「设置 → 模型文件夹」中改成任意目录。

## 目录结构

每个模型是模型文件夹下的一个子文件夹，可以再用一层分组。精灵模型的结构如下（Live2D 模型见文末）：

```text
models/
├── kanon-summer/          ← 一个模型
│   ├── pet.json           ← 清单（可选，推荐）
│   ├── idle.png           ← 待机立绘（必需）
│   ├── blink.png          ← 闭眼帧（可选）
│   └── avatar.png         ← 乐园卡片头像（可选）
└── 我的收藏/               ← 分组文件夹（本身不是模型）
    └── sayuki/
        └── idle.png       ← 没有 pet.json 也能自动识别
```

扫描规则：

- 最多向下查找 3 层；以 `.` 或 `_` 开头的文件夹会被跳过（可以用 `_draft` 存放草稿）。
- 一旦某个文件夹被识别为模型，它的子文件夹不再单独扫描。
- 不跟随符号链接。

## 不写 pet.json 的自动识别

文件夹中有 `idle.png` 时自动识别为精灵模型：

- `blink*.png` 按文件名排序作为闭眼帧；
- `avatar.png` 作为头像；
- 名字使用文件夹名，不绑定角色。

## pet.json

```json
{
  "format": 1,
  "name": "夏日的叶梦",
  "character": "amakano3.kanon",
  "renderer": "sprite",
  "sprite": {
    "idle": "idle.png",
    "blink": ["blink_half.png", "blink.png"]
  },
  "avatar": "avatar.png",
  "scale": 1.0,
  "author": "你的名字",
  "license": "自绘，仅个人使用"
}
```

| 字段 | 必需 | 说明 |
|---|---|---|
| `format` | 否 | 清单版本，目前为 `1`；写了其它值会报错 |
| `name` | 否 | 显示名称（最多 60 字），默认文件夹名 |
| `character` | 否 | 绑定的角色 id（见下表）。绑定后乐园卡片会显示该模型的头像，资料页可一键设为桌宠，桌宠也会使用该角色作品的季节主题 |
| `renderer` | 否 | `sprite`（默认）或 `live2d`（v0.2 起，需安装 live2d-py，见下文） |
| `sprite.idle` | 是 | 待机图，相对于模型文件夹的路径 |
| `sprite.blink` | 否 | 闭眼帧，字符串或数组（最多 4 张）。一张时直接切换；两张时第一张作为半闭眼 |
| `avatar` | 否 | 头像图；未提供时卡片使用 `sprite.idle` 的上半部分 |
| `scale` | 否 | 0.1 – 5 之间；程序实际采用的模型倍率限制在 0.3 – 3，再与用户缩放（0.5 – 2）相乘 |
| `author` / `license` | 否 | 素材作者与使用条件，便于自己备忘 |

### 图片要求

- 格式：PNG（推荐，带透明通道）、WebP、JPG。
- 单张不超过 20 MB；超过 1600 px 的边会在载入时等比缩小。
- 桌宠窗口比例约为 7:9（280 × 360），立绘底部对齐、居中显示。
- 闭眼帧需要和待机图**同尺寸、同位置**，只改变眼睛部分，效果最好。

### 安全校验

- 路径必须在模型文件夹内：拒绝绝对路径、`..` 以及解析后越界的路径。
- 文件不存在、格式不支持、过大时，该模型会在「我的模型」中显示错误原因，且不能被选中。
- `pet.json` 不超过 256 KB，必须是 UTF-8 编码的 JSON 对象。

## 角色 id

| id | 日文名 | 中文名 |
|---|---|---|
| `amakano.sayuki` | 高社 紗雪 | 高社纱雪 |
| `amakano.mizuki` | 上林 聖 | 上林圣 |
| `amakano.koharu` | 星川 こはる | 星川小春 |
| `amakano-ss.honami` | 一ノ瀬 穂波 | 一之濑穗波 |
| `amakano-ss.kanade` | 沓野 奏 | 沓野奏 |
| `amakano-ss.yuzuka` | 高社 雪静 | 高社雪静 |
| `amakano-ss.ruika` | 硯川・ユーフラジー・涙香 | 砚川·Euphrasie·泪香 |
| `amakano2.chitose` | 蔦町 ちとせ | 茑町千岁 |
| `amakano2.yuuhi` | 黒姫 結灯 | 黑姬结灯 |
| `amakano2.rei` | 氷見山 玲 | 冰见山玲 |
| `amakano2.sara` | 咲來 | 咲来 |
| `amakano3.kanon` | 柳木 叶夢 | 柳木叶梦 |
| `amakano3.shion` | 柳木 詩夢 | 柳木诗梦 |
| `amakano3.sayumi` | 鴻 さゆみ | 鸿纱由美 |
| `amakano3.touka` | 御所院 冬樺 | 御所院冬桦 |
| `amakano3.scarlet` | スカーレット・斑鳩・ウィスタリア | 史卡蕾特・斑鸠・威斯塔利亚 |

## Live2D 模型（v0.2 起）

AmakanoPet 可以显示**你自己准备**的 Live2D Cubism 模型（Cubism 3 及以上的 `*.model3.json`，以及 Cubism 2 的 `*.model.json` / `model.json`）。

### 启用

Live2D 是可选功能，需要 Python 3.11+，并额外安装 [live2d-py](https://github.com/Arkueid/live2d-py)：

```bash
pip install -r requirements-live2d.txt     # 或 pip install live2d-py
```

live2d-py 以 MIT 许可证发布，内置官方 Live2D Cubism SDK；其中的 Cubism Core 适用 [Live2D Proprietary Software License](https://www.live2d.com/eula/live2d-proprietary-software-license-agreement_cn.html)。AmakanoPet 不附带 Cubism Core。没有安装时，Live2D 模型会在「我的模型」中显示安装提示，精灵模型不受影响。显卡驱动需要支持 OpenGL 2.1 或更高版本。

### 目录

把模型导出的整个文件夹原样放进模型文件夹即可，不需要改动其中的文件：

```text
models/
└── my-live2d/
    ├── pet.json              ← 可选
    ├── avatar.png            ← 可选，乐园卡片头像
    ├── xxx.model3.json
    ├── xxx.moc3
    ├── xxx.physics3.json
    ├── xxx.4096/texture_00.png
    └── motions/…
```

没有 `pet.json` 时，程序会自动识别文件夹中的 `*.model3.json` / `*.model.json` / `model.json`，名字使用文件夹名。

### pet.json

```json
{
  "format": 1,
  "name": "我的 Live2D 模型",
  "character": "amakano3.kanon",
  "renderer": "live2d",
  "live2d": { "model": "xxx.model3.json", "zoom": 1.0, "offset": [0, 0] },
  "avatar": "avatar.png",
  "scale": 1.0
}
```

| 字段 | 必需 | 说明 |
|---|---|---|
| `live2d.model` | 否 | 模型 json 的相对路径；省略时自动查找 |
| `live2d.zoom` | 否 | 模型在画布内的缩放，0.1 – 10，默认 1 |
| `live2d.offset` | 否 | `[x, y]`，模型在画布内的偏移（模型坐标，-5 – 5），用于把脸调到合适的位置 |
| `scale` / `avatar` / `character` | 否 | 与精灵模型相同 |

### 行为

- 模型自带的呼吸、眨眼、物理和 Idle 动作由 Cubism SDK 驱动，AmakanoPet 不再叠加呼吸和浮动效果。
- 单击桌宠时随机播放 `TapBody` 动作组；没有这个动作组时，从全部动作中随机挑选。
- 视线会跟随鼠标（需要模型有标准的角度参数）。
- 模型加载失败时自动换回糯糯，并在「我的模型」页显示原因。

### 测试用的示例模型

开发者可以运行 `tools/fetch_live2d_sample.sh Mark`，把 Live2D 官方免费示例模型下载到已被 git 忽略的 `.local-test-models/`。这些模型适用 [Live2D Free Material License](https://www.live2d.com/eula/live2d-free-material-license-agreement_cn.html)，**只用于本地测试，不得提交到本仓库或随程序分发**。

## 素材来源提醒

请只使用你有权使用的素材，不要使用游戏解包文件，也不要把他人的素材打包分发。详见 [DISCLAIMER.md](../DISCLAIMER.md)。
