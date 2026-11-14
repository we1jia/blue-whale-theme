# 蓝鲸主题（blue-whale）

给 Claude Code 桌面端换上一套浅蓝海洋风主题：薰衣草白到海蓝的渐变底色，底部多层半透明波浪，侧栏底部一头喷水的小鲸鱼，右侧一位抱着奶茶和笔记本电脑、骑在鲸鱼上的蓝发少女，周围飘着气泡。状态栏会显示“🐋 深海模式 · 慢慢游”。

## 安装

在 Claude Code 的终端会话里输入：

```
/plugin install blue-whale --marketplace we1jia/blue-whale-theme
```

提示添加 marketplace 时输入 `y`，再选择安装范围即可。

## 说明

- 主题只在 Claude Code **桌面端和手机 App** 里绘制，纯终端和编辑器里看不到背景。
- 只有浅色一套：背景是浅色插画，开启后即使系统是深色模式，也会保持浅色。
- 窗口宽度小于 760 像素时，右侧的人物会自动隐藏，避免挡住正文。
- 背景是静态的，不加动画，避免一直占用 CPU。
- 卸载：`/plugin uninstall blue-whale`。

## 实现

背景是一张纯矢量的 SVG 场景，由 `tools/build_scene.py` 生成到 `hooks/scene.js`：

- 渐变、波浪、气泡直接用矢量绘制；
- 人物和鲸鱼由 `tools/trace.py` 从 `tools/source/sprites.webp` 描摹成分层矢量色块（OpenCV k-means 分色 + 叠层轮廓），因为桌面端的背景场景不显示嵌入的位图；
- 整段 SVG 控制在 131072 字符以内。

重新生成（需要 Python 3、Pillow、numpy、opencv-python）：

```
python3 tools/build_scene.py
```

配色和状态栏文案在 `hooks/register.tsx` 里修改。
