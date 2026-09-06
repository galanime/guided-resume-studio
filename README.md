# Guided Resume Studio

一个面向多种职业的可复用简历 Skill：通过多轮交互建立候选人事实库，按目标岗位选择合适的叙事策略，完成 ATS 关键词映射与有证据的经历增强，在用户最终确认后生成可溯源的一页 PDF 简历。它覆盖互联网、法律、财务、教育、医疗、公共服务、设计与其他岗位，不会因为缺少百分比指标就把真实经历写成空泛职责。

视觉采用 **LapisCV 单页 A4 结构 + professional-blue 专业蓝主题**，并提供明确的内容批准、PDF 质量检查和重建机制。

## 核心能力

- 每轮只询问 1–3 个相关问题，逐步建立候选人资料库。
- 按 JD 职责信号选择岗位族叙事策略，避免所有岗位使用同一种简历句式。
- 没有数字指标时，从范围、难点、判断、交付物、质量证据和反馈中增强经历表达。
- 支持 Markdown、TXT、JSON、YAML、PDF、DOCX 和目录型知识库。
- 区分 `user_verified`、`source_supported`、`unverified`、`conflicted` 和 `do_not_disclose`。
- 一次处理一个岗位，优先分析用户提供的官方 JD。
- 先建立“岗位要求 → 用户事实”的匹配矩阵，再决定区块、经历和 bullet 写法。
- 无事实支持的 ATS 关键词只进入 gap 报告，不能写进简历。
- 动态省略没有内容的项目、实习、奖项、技能或语言区块。
- 预览阶段只生成 Markdown/HTML；用户明确确认后才允许生成 PDF。
- 内容、模板或主题变化会自动使原批准哈希失效。
- 使用 Chromium 打印一页 A4 PDF，并检查文本、字体、页数、尺寸和视觉结果。
- 保存 profile、ATS 映射、批准记录、QA 报告、渲染器及 `rebuild.sh`。

## 安装

```bash
git clone https://github.com/galanime/guided-resume-studio.git
cd guided-resume-studio
./install.sh
```

安装脚本默认复制到 `${CODEX_HOME:-$HOME/.codex}/skills/guided-resume-studio`。如果目标目录已存在，脚本会停止，不会覆盖已有资料。

也可以手动复制：

```bash
cp -R guided-resume-studio ~/.codex/skills/guided-resume-studio
```

## 使用

在 Codex 中开始一个新任务：

```text
请使用 $guided-resume-studio，帮我针对一个岗位建立资料库并生成简历。
```

Skill 会依次完成：

1. 基础信息和本地资料库初始化；
2. 文件导入、事实提取与冲突确认；
3. 单个岗位的官方 JD 调研；
4. ATS 关键词与事实匹配；
5. 经历选择、排序和有证据的改写；
6. Markdown 内容与专业蓝 HTML 预览；
7. 模板、公开信息、正文和重点标记确认；
8. 正式 PDF、QA 报告和溯源包生成。

Skill 无法自行改变 Codex 的系统协作模式。如果当前不是 Plan 模式，它会执行同等严格的内部规划阶段，并提示用户可手动切换。

## 运行依赖

- Python 3；
- Chrome、Edge 或 Chromium；
- Noto Sans CJK SC、Source Han Sans CN、PingFang SC 或 Microsoft YaHei；
- `pypdf`，用于检查并修复 Chromium 中文 PDF 的 ToUnicode 映射；
- Poppler 的 `pdftoppm`，用于生成视觉 QA PNG。

Codex Desktop 通常可通过 bundled workspace dependencies 提供 `pypdf` 和 Poppler。缺少浏览器、字体或 PDF 工具时，Skill 会停止并给出修复提示，不会生成近似版本。

## 隐私边界

- 默认只写入当前工作区的 `resume-workspace/<candidate-id>/`。
- 不将候选人资料写入全局记忆。
- 不上传个人资料、不读取凭据、不自动填写或提交招聘申请。
- 不复制整套原始知识库；只保存来源路径或 URL、SHA-256、采用片段和结构化事实。
- 正式简历只能使用用户确认的事实。

## 开发与验证

```bash
python3 -m unittest discover -s guided-resume-studio/tests -v
python3 -m py_compile guided-resume-studio/scripts/*.py
```

Skill Creator 校验：

```bash
python /path/to/skill-creator/scripts/quick_validate.py guided-resume-studio
```

## 项目结构

```text
guided-resume-studio/
├── SKILL.md
├── agents/openai.yaml
├── references/
├── assets/
│   ├── candidate-profile-template.md
│   ├── profile.schema.json
│   ├── resume.schema.json
│   └── lapiscv/
├── scripts/
│   ├── init_workspace.py
│   ├── render_lapiscv.py
│   ├── validate_resume.py
│   └── snapshot_run.py
└── tests/
```

## 上游与许可证

仓库主体采用 [MIT License](LICENSE)。

`guided-resume-studio/assets/lapiscv/` 中的基础结构源自 [BingyanStudio/LapisCV](https://github.com/BingyanStudio/LapisCV)，保留其 MIT 版权与许可证声明。专业蓝主题、事实模型、ATS 映射、批准门禁、QA 和溯源脚本为本项目实现。
