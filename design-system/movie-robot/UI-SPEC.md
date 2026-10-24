# Movie Robot UI 设计开发规范 (Design Specification for Cursor)

> 本规范专门面向 Cursor 及前端开发编写，基于 **Cinematic Studio Dark** 影视工业深色主题构建。请在编码（React / Vue / Tailwind CSS）时严格遵循以下设计 Tokens、布局规则与组件语义。
>
> 来源：Stitch 项目 `movie-robot` · 屏幕「Movie Robot UI 设计开发规范 (Cursor 指南)」

---

## 1. 设计系统全局设定 (Global Foundations)

- **主题模式**: 严格强制 **Dark Mode**（深色电影工业风 / 专业工作站）
- **主要字体**:
  - 界面正文 / 标题: `Plus Jakarta Sans`, `-apple-system`, `BlinkMacSystemFont`, `PingFang SC`, `Hiragino Sans GB`, `Microsoft YaHei`, sans-serif
  - 数据 / 代码 / 路径 / 参数: `JetBrains Mono`, `Fira Code`, `ui-monospace`, monospace
- **圆角体系**:
  - 小型控件 (Badge, Tag, Micro Button): `rounded` (4px)
  - 核心控件 (Button, Input, Select, Checkbox): `rounded-lg` (8px)
  - 面板与卡片 (Card, Container, Dialog, Sheet): `rounded-xl` (12px)
  - 顶栏 / 悬浮栏 / 药丸胶囊: `rounded-full` (9999px)

---

## 2. 色彩系统与 Tailwind Tokens (Color Palette)

系统采用暗黑沉浸式色彩分层（Surfaces），配以温暖的琥珀金（Amber）作为主强调色，营造专业级影视后期的暗室调色盘体验。

### 2.1 表面层级 (Surfaces & Backgrounds)

```css
/* 深度背景：从底向上叠加 */
--bg-lowest: #0e0e10;   /* 最底沉浸背景 / Modal 遮罩层底 */
--bg-surface: #131315;  /* 全局默认页面背景色 (bg-surface) */
--bg-low: #1b1b1d;      /* 侧边栏、主工作区面板、列表行底色 */
--bg-container: #222225;/* 卡片、分组容器、输入框背景 (bg-surface-container) */
--bg-high: #2b2b2e;     /* 悬浮态、激活 Tab、次级卡片底色 */
--bg-highest: #343438;  /* Popover、Dropdown、Toast 浮层底色 */
```

### 2.2 线框与分割线 (Borders & Outlines)

```css
--outline: #49454f;
--outline-variant: rgba(255, 255, 255, 0.08); /* 默认常规低对比度分割线 */
--outline-focus: #f59e0b;                     /* 聚焦态高亮边框 */
```

### 2.3 品牌色与状态色 (Brand & Semantic Accents)

| 角色 | 颜色值 | Tailwind 类名 | 用途 |
| :--- | :--- | :--- | :--- |
| **Primary (琥珀金)** | `#f59e0b` (`amber-500`) | `text-amber-500` / `bg-amber-500` | 核心 CTA、活动高亮、主品牌标识、重要进度 |
| **Primary Hover** | `#d97706` (`amber-600`) | `hover:bg-amber-600` | 主按钮悬浮态 |
| **Success (翡翠绿)** | `#10b981` (`emerald-500`)| `text-emerald-400` / `bg-emerald-500` | 挂载就绪、在线节点、批量执行成功、健康状态 |
| **Warning (暖橙)** | `#fb923c` (`orange-400`)| `text-orange-400` / `bg-orange-500` | 待刮削重命名、警告提示、容量临界 |
| **Error (绯红)** | `#ef4444` (`red-500`)| `text-red-400` / `bg-red-500` | 刮削冲突、识别失败、挂载断开 |
| **Info / Tech (青蓝)** | `#38bdf8` (`sky-400`)| `text-sky-400` / `bg-sky-500/20` | 格式标签 (`.mkv`)、分辨率 Badge (`4K UHD`) |

### 2.4 文本层级 (Text & Contrast)

```css
--text-primary: #f3f3f5;       /* 主标题、高亮数据、选中标签 (text-white/95) */
--text-secondary: #9ca3af;     /* 副标题、表头、辅导说明 (text-zinc-400) */
--text-tertiary: #6b7280;      /* 时间戳、占位符、禁用态文字 (text-zinc-500) */
--text-accent: #f59e0b;        /* 强调文本、活动项文本 */
```

---

## 3. 布局架构规范 (Layout & Shell)

整体采用经典的三栏 / 双栏工作台架构：

```
+------------------------------------------------------------------------------------+
| 侧边栏 (240px 固定)      | 顶栏 TopBar (h-14, 粘性/固定, border-b)                   |
| - Logo & 工作区徽标      +---------------------------------------------------------+
| - 核心存储容量仪表盘     | 状态条 / 面包屑 / 全局操作栏                            |
| - 导航菜单 (3-5项)       +---------------------------------------------------------+
| - 底栏 (文档/健康度)     | 主工作区: 左侧目录文件浏览器 (60%) | 右侧预览与刮削配置 (40%)  |
+------------------------------------------------------------------------------------+
```

1. **左侧导航栏 (`w-[240px]` 响应式折叠)**:
   - 背景: `bg-[#1b1b1d]` (`surface-container-low`)
   - 边框: `border-r border-white/[0.08]`
   - 激活项样式: `bg-[#2b2b2e] text-amber-500 border-l-2 border-amber-500 font-medium`
   - 未激活样式: `text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]`
2. **顶栏 (`h-14`)**:
   - 背景: `bg-[#131315]/80 backdrop-blur-md`
   - 包含：面包屑导航、环境标签（`生产环境 v2.8.4`）、系统状态指示灯、文档快捷入口、管理员信息。
3. **主工作区网格**:
   - 左右双栏协作：左侧列表区占用 `flex-1`（或 `w-3/5`），右侧预览检查区占用固定宽度或 `w-2/5`（最小 `380px`）。

---

## 4. 组件规范 (Component Specs)

### 4.1 按钮 (Buttons)

- **Primary Button (主行动按钮)**: 黑字 + `bg-amber-500`，悬浮 `amber-600/400`，`rounded-lg`，轻阴影 `shadow-amber-500/20`，`active:scale-[0.98]`
- **Secondary / Action Button (次级操作)**: `text-amber-400 bg-amber-500/10 border-amber-500/30`
- **Ghost / Neutral Button (幽灵 / 弱操作)**: `text-zinc-400 bg-white/[0.04] border-white/[0.08]`

### 4.2 表格与文件列表项 (File List Rows)

- 默认态: 透明底 + `border-b border-white/[0.04]`
- 悬浮态: `hover:bg-white/[0.02]`
- 选中态: `bg-amber-500/[0.06] border-amber-500/20`
- 影视规格标签用 `font-mono` 小字号 Badge（4K / `.mkv` / Atmos 等）

### 4.3 输入框与搜索栏 (Form & Inputs)

- 背景偏黑半透明、`border-white/[0.08]`、`rounded-lg`
- Focus: `border-amber-500/60` + 轻 `ring-amber-500/30`

### 4.4 状态微胶囊 (Status Badges & Indicators)

- 成功 / 在线: 翡翠绿底 + 呼吸圆点
- 其它语义色对齐 §2.3

### 4.5 代码与规则模板卡片 (Code Template Box)

- 深底 `#0e0e10`、等宽字体、琥珀文字，用于命名规则 / 路径模板展示

---

## 5. Cursor 开发提示词与指令模版 (Prompt for Cursor)

当使用 Cursor 生成或重构组件时，可将以下指令作为系统提示或对话前缀：

```markdown
请严格按照《Movie Robot UI 设计规范》进行开发：
1. 界面风格为专业级暗色模式（Dark Workstation），主背景色为 #131315，容器背景使用 #1b1b1d 和 #222225，边框使用 border-white/[0.08]。
2. 品牌主色使用 Amber (#f59e0b)，用于重要 CTA、关键选中态与高亮标签；成功状态使用 Emerald (#10b981)。
3. 所有字体采用 Plus Jakarta Sans（正文）搭配 JetBrains Mono（路径、文件名、技术规格）。
4. 保持扁平少投影、高可读性、紧凑专业的信息密度（Information-Dense UI），行内多用 gap-2 / gap-3。
5. 动效微弱流畅，按钮点击具备 active:scale-[0.98] 反馈，hover 使用 transition-colors duration-150。
```

---

## 6. 与本仓库技术栈的映射说明

本仓库前端为 **Vue 3 + Element Plus**，规范中的 Tailwind 类名为语义参考。落地时优先：

1. 将 §2 色彩写入 / 对齐 `frontend/src/styles/global.css` 中的 CSS 变量（`--mr-*` / `--el-color-primary` 等）
2. 用 Element Plus 主题与 scoped CSS 实现同等视觉，而不是强行引入 Tailwind
3. 路径、文件名、规格标签使用等宽字体栈
4. 冲突时以本文档为准，覆盖旧版 `MASTER.md` 中不一致的色值或圆角
