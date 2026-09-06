# Narrative strategy library

Use this library after the requirement-to-fact matrix and before drafting. It is a
small, extensible set of role-family strategies, not a collection of canned
sentences. Select one primary strategy from JD evidence, then record the choice
and any secondary strategy in `research.json` and `change-map.md`.

## Selection protocol

1. Classify the JD by recurring responsibility signals, not by title alone.
2. Choose the family with the strongest `must_have` coverage. If two families are
   tied, ask the user only when the choice changes the story materially.
3. Use the family voice and proof order below. Keep the candidate's natural
   Chinese phrasing where it is clear; do not translate it into generic English-
   style action-verb prose.
4. For each rewritten bullet, preserve this audit trail:
   `事实 -> 叙事角度 -> 证据/结果 -> JD关键词`.
5. Generate at most two variants when the JD genuinely spans families. Label one
   primary and one secondary; do not blend incompatible voices in one bullet.

## Role families

### AI product / product builder

**JD signals:** 用户场景、需求拆解、产品设计、0-1、原型、Prompt、Agent、工作流、
人机协同、迭代、质量门禁、跨团队协作。

**Story order:** 场景或问题 -> 判断/取舍 -> 工作流或方案 -> 验证与边界 -> 结果。

**Voice:** 具体、克制、面向用户和交付；说明为什么这样设计，不把“参与”升级为
“负责全链路”。优先写决策和验证，不堆技术名词。

**Avoid:** “全面负责”“赋能业务”“打造行业领先”“显著提升”这类没有证据的套话，
以及把本地 Mock、人工确认或 Demo 写成生产规模化系统。

### Product operations / growth

**JD signals:** 用户增长、内容/活动、策略、转化、留存、运营机制、数据复盘、生态、
商家/创作者/用户分层。

**Story order:** 用户或业务目标 -> 分层/策略判断 -> 执行动作 -> 指标或反馈 -> 复盘。

**Voice:** 面向对象和业务结果优先；把工具写成支撑手段，把运营判断写在前面。
没有真实增长指标时，写清反馈、覆盖范围或验证状态，不补 ROI、用户量和收入。

**Avoid:** 将产品研发过程改写成增长战果，或把一次性活动写成持续运营机制。

### Engineering / AI application engineering

**JD signals:** 系统设计、服务/API、Python、React、FastAPI、数据流、测试、稳定性、
部署、性能、工程质量、可维护性。

**Story order:** 工程问题 -> 关键机制 -> 范围/质量约束 -> 测试或运行证据 -> 结果。

**Voice:** 机制清楚、边界明确；允许使用“实现/接入/验证”，但 ownership、规模、
生产状态必须与事实一致。测试数量或错误数只有在事实库中有证据时才出现。

**Avoid:** 把调用 API 写成训练模型，把原型写成线上系统，把“通过测试”写成业务收益。

### Research / algorithm / science

**JD signals:** 研究问题、实验、方法、模型、数据集、指标、论文、复现、分析、科学问题。

**Story order:** 问题 -> 方法/实验设计 -> 观察或贡献 -> 验证与限制。

**Voice:** 解释问题和方法之间的关系，量化结果必须带实验上下文；没有训练轨迹、基线
或统计显著性就明确标注不可用。

**Avoid:** 用产品上线语言替代研究贡献，或从几何/静态数据推断训练效果。

### General / cross-functional

**JD signals:** 项目协调、沟通、文档、流程、客户/合作方、综合支持，且没有单一专业族
占据明显多数。

**Story order:** 目标与约束 -> 协作动作 -> 交付物 -> 可核验结果。

**Voice:** 简洁、事实导向，突出交付和协作接口；不使用“沟通能力强”等自评句替代证据。

### Legal / compliance

**JD signals:** 法律检索、合同审查、合规、争议解决、诉讼/仲裁、尽调、法律意见、法规政策、证据、文书。

**Story order:** 事项/法域与问题 -> 风险或争点判断 -> 检索/审查/论证 -> 文书或程序结果。

**Voice:** 精确、谨慎，区分独立责任与协助；不把实习或课程案例写成独立代理、执业或胜诉。

### Finance / consulting / business analysis

**JD signals:** 财务分析、建模、预算、审计、尽调、商业分析、咨询、管理报告、内控、预测。

**Story order:** 业务问题 -> 数据/模型或访谈方法 -> 建议/控制措施 -> 决策采用或交付证据。

**Voice:** 结论和判断优先，解释假设与限制；没有真实收益时不补节省额、回报率或客户名称。

### Education / training

**JD signals:** 课程设计、教学、教研、教案、学习目标、课堂管理、评估、辅导、培训、学生/学员。

**Story order:** 学习对象与目标 -> 教学设计/干预 -> 课堂或交付 -> 学习反馈与范围。

**Voice:** 关注学习目标、教学选择和反馈，不用互联网产品的“用户增长/转化”话术替代教学证据。

### Healthcare / public service

**JD signals:** 患者/居民服务、临床支持、公共项目、政策执行、服务流程、隐私、安全、转介、个案管理。

**Story order:** 服务对象与需求 -> 协议/流程/协调动作 -> 安全或可及性证据 -> 交接与限制。

**Voice:** 责任边界和安全优先；明确实习、志愿、行政支持与持证专业实践的区别。

### Design / content / communications

**JD signals:** 视觉设计、交互、品牌、编辑、文案、内容策划、拍摄、作品集、审稿、传播。

**Story order:** 受众与传播目标 -> 概念/创作决策 -> 产出物与迭代 -> 发布、审阅或反馈。

**Voice:** 让作品和创作判断可见；没有真实传播指标时使用交付、审阅、发布状态和反馈，不补曝光量。

## Language quality gate

Before content review, run a language pass independent of ATS coverage:

- 每条经历只保留一个主语和一个主动作，避免“负责/推动/协同/赋能”连续堆叠。
- 优先使用中文自然因果连接（“针对…，通过…，验证…”），不要逐词套用英文简历句式。
- “结果”可以是指标、测试证据、交付物、反馈或明确的未达成边界；没有结果时不要硬补。
- 保留能体现判断的细节，删除与 JD 无关的背景；不要为了填满一页添加弱相关经历。
- 让同一岗位的 bullets 共享同一叙事角度，但允许不同事实使用不同证据类型。

## Extension rule

新增岗位族前，至少收集三份当前官方 JD，记录可复用的信号、故事顺序、禁用升级和
一个真实改写对照；先加入本文件，再同步 `assets/narrative-strategies.json`。不要把
单个公司的口号或一次用户反馈固化成通用模板。
