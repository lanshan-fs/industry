### 数据库设计
- `SQL/mysql-design/` 目录下设计存放多份 MySQL 设计，设计文件的命名为 `design-日期`。
  当前仍以最新设计为主，但本地真实落地需要同步回写本文件和 `SQL/sql/init.sql`，避免“设计已变、初始化文件未变”。
- `SQL/sql/` 目录下存放对 MySQL 数据库的操作文件。
  `init.sql` 为完整初始化文件，新增正式表结构时必须同步补到这里。
- `SQL/scripts/` 目录下存放和数据导入、自动打标相关的 Python 脚本。
  需要严格基于当前本地数据库模型工作，不再引入旧项目的旧表结构。

### 当前新增表

#### `company_tag_batch`
- 用途：记录一次自动打标任务的批次头信息。
- 关键字段：
  `company_tag_batch_id`：主键。
  `batch_code`：批次编码，供前后端和导出使用。
  `batch_name`：批次名称，可为空。
  `status`：批次状态，当前约定为 `pending` / `running` / `completed` / `failed`。
  `requested_by_user_id`：发起用户 ID，可为空。
  `dimension_ids`：本次选择的标签维度 ID 列表，JSON。
  `dimension_names`：本次选择的标签维度名称列表，JSON。
  `requested_company_count` / `success_company_count` / `failed_company_count`：企业数量统计。
  `summary_json`：批次执行摘要，保存自动打标脚本返回的汇总结果。
  `error_message`：批次级错误信息。
  `started_at` / `finished_at` / `created_at` / `updated_at`：时间字段。
- 设计意图：
  这张表负责“批次管理”和“历史记录”的头信息，不和 `company_tag_map` 混用。`company_tag_map` 仍然只保存当前生效标签。

#### `company_tag_batch_item`
- 用途：记录一个批次内每家企业的执行结果。
- 关键字段：
  `company_tag_batch_item_id`：主键。
  `company_tag_batch_id`：所属批次。
  `company_id`：企业 ID。
  `status`：明细状态，当前约定为 `pending` / `success` / `failed`。
  `tag_count`：本次命中的标签数。
  `result_json`：明细结果 JSON，保存脚本返回的企业级标签结果。
  `error_message`：该企业执行失败时的错误信息。
  `started_at` / `finished_at` / `created_at` / `updated_at`：时间字段。
- 设计意图：
  这张表负责“批次详情”和“导出数据源”。前端查看某个批次时，优先读这里，再和当前 `company_tag_map` 做展示层拼装。

#### `company_tag_llm_batch`
- 用途：记录一次 LLM 场景候选生成任务的批次头信息。
- 关键字段：
  `company_tag_llm_batch_id`：主键。
  `batch_code`：LLM 批次编码。
  `batch_name`：批次名称，可为空。
  `status`：批次状态，当前约定为 `pending` / `running` / `completed` / `failed`。
  `provider` / `model_name`：候选生成服务来源与模型信息。
  `company_tag_dimension_id`：对应标签维度，当前固定为 `应用场景`。
  `requested_company_count` / `success_company_count` / `failed_company_count`：企业数量统计。
  `summary_json`：候选生成摘要，保存每家企业的映射结果概览。
  `error_message`：批次级错误信息。
- 设计意图：
  这张表只管理“候选生成任务”，不直接承载正式标签结果，也不替代 `company_tag_batch`。

#### `company_tag_llm_candidate`
- 用途：记录 LLM 生成的应用场景候选及其审核状态。
- 关键字段：
  `company_tag_llm_candidate_id`：主键。
  `company_tag_llm_batch_id`：所属 LLM 批次。
  `company_id`：企业 ID。
  `company_tag_id`：若能映射到正式标签库，则记录对应标签 ID；否则为空。
  `candidate_type`：候选类型，当前约定为 `mapped_tag` / `unmapped_term`。
  `candidate_name` / `normalized_name`：候选标签名称或未映射短语。
  `status`：当前候选状态，约定为 `pending` / `unmapped` / `applied` / `rejected`。
  `confidence` / `reason_text`：候选置信度与原因。
  `evidence_json`：生成时使用的企业资料快照。
  `prompt_text` / `raw_response` / `response_json`：提示词、模型原始输出和解析后的 JSON。
  `reviewed_by_user_id` / `reviewed_at` / `applied_at`：人工审核与采纳时间。
- 设计意图：
  这张表是“生成式标签候选层”的核心，不直接污染 `company_tag_map`。只有人工采纳后，才把对应正式标签写入 `company_tag_map`。

### 第一阶段能力与表结构对应
- 完整批次管理：`company_tag_batch` + `company_tag_batch_item`
- 历史记录：基于 `company_tag_batch` 查询
- 导出：基于 `company_tag_batch_item` 和当前 `company_tag_map` 生成
- 自动打标主结果：仍落到 `company_tag_map`

### 第二阶段说明
- `行业标签` 不新增独立业务表，直接复用现有 `category_industry`、`category_industry_company_map`、`chain_industry`、`chain_industry_category_industry_map`。
- 企业标签体系中的 `行业标签` 维度由后端同步到 `company_tag_dimension` / `company_tag_subdimension` / `company_tag_library`，再将命中结果写入 `company_tag_map`。
- 当前拆分为两个子维度：
  `产业链`
  `行业分类`
- 命名规则：
  `产业链` 子维度直接使用 `chain_industry.chain_name`。
  `行业分类` 子维度默认使用 `category_industry.category_name`；如果分类名和其他正式标签重名，或分类名本身在行业分类体系内重复，则自动追加 `（category_level_code）` 后缀，例如 `互联网+健康（0102）`。

### 第三阶段说明
- 当前只对 `应用场景` 维度开放 LLM 候选生成。
- LLM 生成结果分两类：
  `mapped_tag`：能够映射到现有 `company_tag_library` 的正式应用场景标签。
  `unmapped_term`：模型认为语义相关，但当前正式标签库中不存在的候选短语。
- `mapped_tag` 初始只落到 `company_tag_llm_candidate`，状态为 `pending`；人工采纳后才写入 `company_tag_map`，并把候选状态更新为 `applied`。
- `unmapped_term` 不直接入正式标签库，只保留候选、原因、原始响应与证据快照，供后续扩充标签体系时参考。

### 当前实现边界
- 不引入旧项目的 `temp_upload_batch`。
- 不把批次表当作标签正式结果表使用。
- 不在批次表内重复存整份企业基础信息，企业名称、信用代码等展示信息按需从 `company_basic` 联查。

### 下一步
- 第一阶段先完成批次创建、进度查询、历史列表、批次详情和导出。
- 第二阶段再接行业标签全量迁移。
- 第三阶段再接 LLM 生成式标签，并将其作为候选增强层而不是直接污染正式标签库。

### 注意
- 项目要求在各个设备可简单快速部署。
- 新增正式表后，必须同步更新：
  `SQL/sql/init.sql`
  `SQL/SQL.md`
- 如后续对表结构继续调整，需要保证自动打标脚本、Node 后端接口和前端页面同时对齐。
