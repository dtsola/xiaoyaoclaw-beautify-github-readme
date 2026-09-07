# Upgrade Plan（升级改进点清单）

基于上游 oil-oil/beautify-github-readme @ 55bdb1c（MIT，1723★）的升级改进说明。

## 改进点与交付状态

### ① 验证自动化（✅ v1 完成）
**交付**：`skills/xiaoyaoclaw-beautify-github-readme/scripts/visual_verify.py`
- Chrome/Edge 跨平台自动探测（Win/macOS/Linux），headless 渲染每个本地 SVG 到 `--out`
- WCAG 对比度检查：text fill vs 容器 rect 背景（父组内先声明的大面积 rect → 祖先链 → 全局最大 rect 兜底），900px 渲染缩放下大字 3:1 / 正文 4.5:1
- 边缘贴边检测：4px 边缘带非背景像素占比（透明/白色画布外像素忽略，圆角过渡宽容）
- 静态检查：viewBox / title / desc / script / foreignObject / 远程字体
- 无 Chrome 时降级为纯静态检查
- 自测：本项目 README 全量 SVG 跑通；hero/section-method 零报告；抓出上游素材真实问题（9px 小字号标签、浅底灰字 eyebrow 等边界案例）

### ② Windows / 中文字体适配（✅ 完成）
- `references/svg-production.md` 字体栈补 `Microsoft YaHei`（原只有 PingFang SC/macOS）+ Windows 回退 SimSun 风险说明
- 中英混排指导：CJK ≈1em 全角 / 拉丁 ≈0.5em、跨平台 5-10% 宽度差、实测法（visual_verify 渲染检查）
- 预览工具跨平台化：SKILL.md §8 + svg-production.md Validate 段以 visual_verify.py 为默认（sips 降级为 macOS 备注）

### ③ 双主题安全（✅ 完成）
- `references/svg-production.md` 新增「Stay legible on both GitHub themes」节
- 硬规则：不透明容器（推荐）vs 透明底（须对 #fff 与 #0d1117 双端 ≥4.5:1，禁中间灰 #808080）
- 说明 GitHub 不执行 prefers-color-scheme

### ④ OpenClaw 门控精简（⏸️ v1.1 再做）
保留上游完整门控（确认制/模式二选一），实测后再决定精简

### ⑤ 归因与链接指向本项目（✅ 完成，rebrand commit）
- 全仓 URL/锚文本 → dtsola/xiaoyaoclaw-beautify-github-readme
- README 顶部「基于上游升级」声明（中英双语）
- showcase 案例保留并注明来自上游
- ja 版删除；上游 branding hero gif/svg、X callout 移除；新双语 hero.svg（本项目自产）

## 验收标准
- [x] 上游能力全保留（README/asset-only/纯 SVG/hybrid/GIF/audit）
- [x] visual_verify.py 在无 Chrome 机器可用（静态降级）
- [x] 本仓库 README 全部 SVG 通过验证（0 阻断）
- [x] README 中英双语 + 上游声明
- [ ] GitHub 发布（dtsola/xiaoyaoclaw-beautify-github-readme，待指挥官确认）
- [ ] ClawHub 提交（pending-publication，待指挥官确认）
