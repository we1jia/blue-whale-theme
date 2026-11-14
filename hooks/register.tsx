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

const SCENE_NAME = 'whale-girl'

// 背景用 scene（SVG）而不是 image：当前 App 版本的图片背景不绘制，场景里嵌入的位图也会被拦掉，
// 只有纯矢量能显示。场景由 tools/build_scene.py 生成到 hooks/scene.js，
// 骑鲸少女和喷水鲸鱼由 tools/trace.py 从素材描摹成矢量；为省 CPU，场景是静态的。
// glass：所有面板（侧栏、对话区）共用一套毛玻璃，App 默认是模糊 16、不透明度 0.6。
// 这里调到不模糊、不透明度 0.08，面板几乎全透，插画原样露出来；
// 插画是浅色粉彩，深色文字压在上面仍然看得清。文字看不清时把 opacity 往 0.15～0.2 调
const LOOK: ThemeSetArgs = {
  colors: theme,
  backdrop: { scene: SCENE_NAME, glass: { blur: 0, opacity: 0.08 } },
}

const STATUS = '🐋 深海模式 · 慢慢游'
// 开关状态存在 $.store 里，跨会话保留；从没设置过就当作开启
const ENABLED_KEY = 'enabled'

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    // 命令名写成字面量：校验器据此认出这个 hook 只回答自己注册的命令
    await $.command.register({
      name: 'blue-whale',
      description: '开关蓝鲸主题（on 打开，off 关闭，不带参数切换）',
      argumentHint: '[on|off]',
      immediate: true,
    })

    // 关掉过就不套主题，也不清主题：会话启动时清主题会把别的插件或卡片选的主题一起抹掉
    if ((await $.store.get(ENABLED_KEY)) === false) {
      return next(e)
    }

    // 搭建阶段：如果有一行会让桌面端整套主题不上色，弹个提示
    const unpainted = problems.find(line => line.startsWith("Desktop won't paint"))

    if (unpainted !== undefined) {
      $.ui.toast(unpainted)
    }
    // 会话启动时客户端可能还没连上，isDrawn 会是 false，但连上后照样会画；
    // 纯终端会话也永远是 false，所以这里不再弹提示，免得每个会话都冒一句
    await $.theme.set(LOOK)
    $.ui.status(STATUS)

    return next(e)
  })

  on('command.run', { command: 'blue-whale' }, async ($, e) => {
    // 只输入 /blue-whale 时 args 是空串；兜底 undefined，防止别的插件用 $.command.run 不带 args 调用
    const arg = (e.args ?? '').trim().toLowerCase()

    if (arg !== '' && arg !== 'on' && arg !== 'off') {
      return { text: '用法：/blue-whale on 打开，/blue-whale off 关闭，只输入 /blue-whale 在开和关之间切换。' }
    }
    const wasOn = (await $.store.get(ENABLED_KEY)) !== false
    const turnOn = arg === '' ? !wasOn : arg === 'on'

    await $.store.set(ENABLED_KEY, turnOn)

    if (!turnOn) {
      // 主题全会话只有一套，clear 会清掉当前生效的主题，回到 App 默认外观
      await $.theme.clear()
      $.ui.status(undefined)

      return { text: '蓝鲸主题已关闭，已换回 App 默认外观。以后的新会话也不会自动套用，输入 /blue-whale on 可重新打开。' }
    }
    const set = await $.theme.set(LOOK)

    $.ui.status(STATUS)

    if (!set.isDrawn) {
      return { text: `蓝鲸主题已打开，但当前界面暂时没画出来：${set.reason}。背景只在桌面端和手机 App 的 Code 会话里显示。` }
    }

    return { text: '蓝鲸主题已打开，以后的新会话也会自动套用。' }
  })

  on('ui.render', { component: 'Backdrop' }, ($, e, next) => {
    // 只画自己的场景：别的插件设的背景交给它自己画。
    // 场景名在新版本里叫 scene、旧版本里叫 id（官方 theme-examples 也两个都读）；
    // 只认 scene 的话，旧字段下会误以为不是自己的而不画，且没有任何报错。
    // 两个都没有时照画，宁可多画也不要整张图消失
    const props = e.props as { scene?: unknown; id?: unknown }
    const name = typeof props.scene === 'string' ? props.scene : props.id

    if (typeof name === 'string' && name !== SCENE_NAME) {
      return next(e)
    }
    if (e.surface !== 'desktop' && e.surface !== 'mobile') {
      return next(e)
    }

    const { Svg } = $.ui.resolve(e)

    // 不开 isInteractive：整段 SVG 按静态图片绘制，场景里只有纯矢量
    return <Svg source={SCENE} alt="浅蓝海面插画：底部多层波浪，左下一头喷水的鲸鱼，右侧一位抱着奶茶和笔记本电脑、骑在鲸鱼上的蓝发少女，周围飘着气泡" />
  })
}
