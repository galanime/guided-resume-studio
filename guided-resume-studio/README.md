# Guided Resume Studio

引导式简历工作室（Agent Skill）：先建立可复用的个人职业知识库，再针对一个目标岗位做官方 JD 调研、ATS 关键词映射和事实溯源改写，最终生成一页 LapisCV 专业蓝 PDF 简历。所有资料只保存在本地工作区，不上传、不填表、不投递。

## 安装

把 `<owner>` 替换为实际的 GitHub 用户名或组织名。

**方式一：一键脚本（推荐）**

```bash
curl -fsSL https://raw.githubusercontent.com/<owner>/guided-resume-studio/main/install.sh | bash
```

**方式二：git clone**

```bash
git clone https://github.com/<owner>/guided-resume-studio.git ~/.codex/skills/guided-resume-studio
```

使用 Claude Code 或 Kimi Code 时，把目标目录换成 `~/.agents/skills/guided-resume-studio` 或 `~/.kimi-code/skills/guided-resume-studio`；install.sh 会自动探测这些位置。

**方式三：Release 压缩包**

从 GitHub Releases 下载 `guided-resume-studio.skill`（本质是 zip），解压到上述任一 skills 目录，保证解压后存在 `guided-resume-studio/SKILL.md`。

安装完成后运行结构校验确认完整：

```bash
python3 ~/.codex/skills/guided-resume-studio/scripts/quick_validate.py ~/.codex/skills/guided-resume-studio
```

## 运行依赖

- Python 3.10+（脚本仅用标准库；正式 PDF 的 Unicode 修复和 QA 需要 `pypdf`）
- Chrome / Edge / Chromium 任一浏览器（打印 PDF）
- Poppler 的 `pdftoppm`（渲染 PNG 用于视觉验收）
- 中文字体：Noto Sans CJK SC、Source Han Sans CN、PingFang SC 或 Microsoft YaHei 任一

## 使用

在支持 Agent Skills 的客户端里说「帮我针对某公司的某岗位做一份简历」即可触发。流程：建库与事实确认 → 岗位调研与 ATS 映射 → 一页适配检查（`--fit-check`）→ 预览批准 → 正式渲染 → 结构与视觉 QA → 溯源快照。细节见 [SKILL.md](SKILL.md) 与 `references/`。

## 隐私

知识库（`resume-workspace/<candidate-id>/knowledge/`）保存全部已确认资料——包括某次简历没有用上的内容——仅供后续岗位复用，不写入全局记忆，不离开本机。不要在知识库中放入凭据、证件号等敏感信息。

## 目录结构

- `SKILL.md`：技能入口与硬性规则
- `references/`：交互工作流、资料溯源、岗位调研改写、岗位族叙事策略库、经历增强规则、渲染 QA
- `scripts/`：工作区初始化、一页预估、渲染、校验、快照、打包
- `assets/`：候选人模板、岗位族叙事配置、JSON Schema、LapisCV 模板（MIT，见 `assets/lapiscv/LICENSE`）
- `tests/`：`python3 -m unittest discover -s tests`

## 打包发布

```bash
python3 scripts/package_skill.py .           # 产出 dist/guided-resume-studio.skill
```

把 `.skill` 文件作为 GitHub Release 资产上传即可支持方式三安装。
