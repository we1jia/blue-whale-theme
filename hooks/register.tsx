import type { Register, ThemeSetArgs } from 'claude-code'

import { makeColors } from './make-colors.js'
import { SCENE } from './scene.js'

// 只做浅色：背景是浅色插画（渐变海面、多层波浪、喷水鲸鱼、骑鲸少女），
// 深色模式下浅底配浅字会看不清，所以用 only: 'light' 锁定浅色
// 配色取自插画：薰衣草白底、海蓝强调，红绿黄保留各自含义
const { theme, problems } = makeColors({
  label: 'Blue whale',
  only: 'light',
  roles: { accent: '#4d6bfe', danger: '#d0454c', success: '#2e9d6a', warning: '#c98a1b', pro: '#7b61d9' },
  light: {
    gray: {
      anchors: {
        'surface-0': '#edf1fc',
        'surface-1': '#f4f7fe',
        'surface-2': '#fafbff',
        'text-primary': '#1b2440',
        'text-secondary': '#3d4868',
        'text-muted': '#5a6584',
      },
    },
  },
})

// 背景用 scene（SVG）而不是 image：当前 App 版本的图片背景不绘制，场景里嵌入的位图也会被拦掉，
// 只有纯矢量能显示。场景由 tools/build_scene.py 生成到 hooks/scene.js，
// 骑鲸少女和喷水鲸鱼由 tools/trace.py 从素材描摹成矢量；为省 CPU，场景是静态的。
// glass：侧栏毛玻璃调轻（模糊 3、不透明度 0.4），让侧栏底部的喷水鲸鱼看得清
const LOOK: ThemeSetArgs = {
  colors: theme,
  backdrop: { scene: 'whale-girl', glass: { blur: 3, opacity: 0.4 } },
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    // 搭建阶段：如果有一行会让桌面端整套主题不上色，弹个提示
    const unpainted = problems.find(line => line.startsWith("Desktop won't paint"))

    if (unpainted !== undefined) {
      $.ui.toast(unpainted)
    }
    // 会话启动时客户端可能还没连上，isDrawn 会是 false，但连上后照样会画，所以只用 toast 提示一次
    const set = await $.theme.set(LOOK)

    if (!set.isDrawn) {
      $.ui.toast(`蓝鲸主题暂未绘制：${set.reason}`)
    }
    $.ui.status('🐋 深海模式 · 慢慢游')

    return next(e)
  })

  on('ui.render', { component: 'Backdrop' }, ($, e, next) => {
    if (e.surface !== 'desktop' && e.surface !== 'mobile') {
      return next(e)
    }

    const { Svg } = $.ui.resolve(e)

    // 不开 isInteractive：按图片绘制，内嵌的 data URI 位图和 CSS 动画都能正常显示
    return <Svg source={SCENE} alt="浅蓝海面插画：底部多层波浪，左下一头喷水的鲸鱼，右侧一位抱着奶茶和笔记本电脑、骑在鲸鱼上的蓝发少女，周围飘着气泡" />
  })
}
