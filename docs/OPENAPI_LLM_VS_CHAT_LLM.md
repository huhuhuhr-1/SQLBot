# openapi_llm 与 chat/task/llm 详细比对

> 考虑 openapi_llm 是从 llm.py 的**老版本**复制后二次开发，本表标出「chat 有 / openapi 无或不同」的差异，并区分：**应同步** / **可选同步** / **保持 openapi 定制**。

---

## 一、导入与依赖

| 项目 | chat llm | openapi llm | 建议 |
|------|----------|-------------|------|
| `get_chat_brief_generate` | ✅ | ❌ 未导入 | **可选**：若 openapi 也要按「是否已有标题」决定 change_title，需补 |
| `get_chat_predict_data` | ✅ | ❌ | 可选（openapi 若不做 predict 可不要） |
| `get_chat_chart_config` | ✅ | ❌ | 可选 |
| `trigger_log_error` | ✅ | ❌ | **建议同步**：check_sql 失败时写 log 用 |
| `get_groups` / `SysArgModel` | ✅ | ❌ | **可选**：chat 用其做 limit/context 配置，openapi 可沿用配置常量 |
| `I18nHelper` / `i18n` / `trans` | ✅ | ❌ | **可选**：仅影响 run_task 里「记录 id」等文案 |
| `tiktoken` / `Template` | ❌ | ✅ | **保持**：openapi 独有（token 估算、自定义提示词） |
| `get_session` / openapi 专用 model | ❌ | ✅ | **保持** |

---

## 二、类属性与 __init__

| 项目 | chat llm | openapi llm | 建议 |
|------|----------|-------------|------|
| `trans: I18nHelper` | ✅ | ❌ | 可选 |
| `articles_number` | ✅ | ❌ | 可选（openapi 未用可忽略） |
| `enable_sql_row_limit` | ✅ 从 settings + create() 配置 | ❌ | **可选**：openapi 若需「限制 SQL 行数」可同步 |
| `base_message_round_count_limit` | ✅ 从 settings + create() | 用常量 `base_message_count_limit=6` | **可选**：openapi 可改为从配置读 |
| `change_title` | `not get_chat_brief_generate(...)` | `len(self.generate_sql_logs)==0` | **可选**：逻辑不同，openapi 可保留现状 |
| `db_schema` 设置时机 | 在 `choose_table_schema(session)` 里 | 在 __init__（有 ds 时）或 run_task 里 | **保持**：openapi 无 choose_table_schema，沿用当前 |
| `create()` 内 `get_groups("chat")` | ✅ 设置 limit/context | ❌ | 可选 |
| 无 ds 时 `chat_question.datasource_id` 写回 chat | ✅ | ❌ | 可选（openapi 入口可能不暴露该流程） |
| tiktoken / _encoder | ❌ | ✅ | **保持** |

---

## 三、init_messages

| 项目 | chat llm | openapi llm | 建议 |
|------|----------|-------------|------|
| 入口 | `choose_table_schema(session)` 再组消息 | 直接组消息，无 choose_table_schema | **保持**：openapi 在 __init__/run_task 里已设 db_schema |
| 历史轮数 | `get_last_conversation_rounds(..., rounds=count_limit)` | `last_sql_messages[count_limit:]` 固定截断 | **建议同步**：chat 的 rounds 更合理，可抽配置或常量 |
| `regenerate_record_id` | ✅ 过滤 sql/chart 历史 | ❌ | **可选**：openapi 若支持「按某条记录重生成」再补 |
| SQL 系统提示 | `sql_sys_question(self.ds.type, self.enable_sql_row_limit)` | 有 my_promote 分支 + get_my_sys_prompt / sql_sys_question_with_schema | **保持**：openapi 定制 |
| 历史条数来源 | `count_limit = self.base_message_round_count_limit` | `count_limit = 0 - base_message_count_limit`（常量 6） | 可选同步为配置 |

---

## 四、run_task 前置流程（生成 SQL 前）

| 项目 | chat llm | openapi llm | 建议 |
|------|----------|-------------|------|
| 有 ds 时 | `filter_terminology_template` → `filter_training_template` → `filter_custom_prompts` → `init_messages` | 内联设 terminologies / data_training / custom_prompt → `init_messages` | **保持**：openapi 简化版，未用 start_log/end_log，可接受 |
| 无 ds 时 | `select_datasource` → (yield) → `validate_history_ds` | 同左，但 db_schema 在「无 ds」分支里设 | 建议确认 openapi 的 db_schema 设置是否覆盖所有分支 |
| `validate_history_ds` | ✅ | ✅ | 一致 |

---

## 五、check_sql / check_save_sql（重要差异）

| 项目 | chat llm | openapi llm | 建议 |
|------|----------|-------------|------|
| 签名 | `check_sql(self, session, res, operate: OperationEnum)` | `check_sql(res)` 静态、无 session/operate | **建议同步**：chat 用 `current_logs[operate]` + `trigger_log_error(session, log)` 写失败日志 |
| 失败时 | `trigger_log_error(session, log)` 再抛 | 直接抛 | **建议**：openapi 补入 trigger_log_error（需补 import 与 log 入参） |
| `check_save_sql` | `check_save_sql(session, res, operate)` | `check_save_sql(session, res)` 无 operate | 若 openapi 不区分 operate 可保留；若要做执行详情日志，建议与 chat 对齐 |

---

## 六、generate_sql

| 项目 | chat llm | openapi llm | 建议 |
|------|----------|-------------|------|
| 加强思考 + sql_user_question | ✅ 一致（thinking_result 已在 chat_model 中修复） | ✅ OpenChatQuestion 已传 thinking_result | 已对齐 |
| 主流程 | 无 print_message | 有 `self.print_message(self.sql_message)` | **保持**：openapi 调试用 |
| 其余 | 一致 | 一致 | - |

---

## 七、process_stream / get_token_usage

| 项目 | chat llm | openapi llm | 建议 |
|------|----------|-------------|------|
| 思考块未结束时 | `content = ''` 防止重复输出 | 已补 `content = ''` | ✅ 已同步 |
| 其它逻辑 | 一致 | 一致 | - |
| `get_token_usage` | 一致 | 一致 | - |

---

## 八、run_task 中消费 sql_res / ds_res

| 项目 | chat llm | openapi llm | 建议 |
|------|----------|-------------|------|
| `for chunk in sql_res` | 已做 dict 校验 + `.get('content') or ''` | 已做同样防御 | ✅ 已同步 |
| `for chunk in ds_res` | 直接用 `chunk.get('content')` | 同左 | **建议**：openapi 也做 `isinstance(chunk, dict)` 与默认空串，与 sql_res 一致 |

---

## 九、标题 / brief

| 项目 | chat llm | openapi llm | 建议 |
|------|----------|-------------|------|
| rename_chat | `brief_generate=llm_brief_generated` | 未传 brief_generate | **可选**：若 openapi 需要「标题是否由 LLM 生成」标记可补 |
| change_title 判断 | 基于 get_chat_brief_generate | 基于 generate_sql_logs 长度 | 保持 openapi 逻辑或按产品需求再对齐 |

---

## 十、openapi 独有（保留）

- `get_think_and_content`
- `generate_sql_with_sql` / plan 相关
- `count_tokens` / `_chunk_data_by_tokens` / `_chunk_data_every`
- `get_analysis_sys_prompt` / `get_my_sys_prompt` / `_summarize_data_chunk`
- `init_for_plan` 及 plan 流程
- OpenChatQuestion、my_promote、my_schema、intent 等

---

## 十一、chat 有而 openapi 无的方法（按需同步）

| 方法 | 用途 | 建议 |
|------|------|------|
| `set_articles_number` | 设置文章数 | 若 openapi 不用可忽略 |
| `filter_terminology_template` | 术语模板 + 打 log | 已用内联简化版，可不抽 |
| `filter_custom_prompts` | 自定义提示词 + 打 log | 已内联 find_custom_prompts，可不抽 |
| `filter_training_template` | 训练模板 + 打 log | 已内联 get_training_template，可不抽 |
| `choose_table_schema` | 选表 schema + 打 log | openapi 在别处设 db_schema，可不抽 |

---

## 十二、建议同步项汇总（按优先级）

1. **已做**  
   - process_stream 思考块 `content = ''`  
   - sql_res 循环的 chunk 防御（dict + 默认空串）  
   - thinking_result 在模板中的传入（chat_model + openapiModels）

2. **建议做**  
   - openapi `check_sql`：补 `session`、`operate` 参数，失败时调用 `trigger_log_error(session, log)`（需从 chat curd 导入 trigger_log_error，并保证 current_logs[operate] 存在）。  
   - openapi `run_task` 里 `for chunk in ds_res`：与 sql_res 一致，做 `isinstance(chunk, dict)` 及 `content/reasoning_content` 默认空串。

3. **可选**  
   - `create()` 里用 get_groups 配置 limit/context；  
   - init_messages 用 get_last_conversation_rounds；  
   - change_title 用 get_chat_brief_generate；  
   - rename_chat 传 brief_generate。

---

## 十三、结论

- **openapi_llm 确属 llm 老版本复制**：缺少 chat 的 `trigger_log_error`、`check_sql(session, operate)`、`get_last_conversation_rounds`、`choose_table_schema`、create() 配置等。  
- **已对齐部分**：process_stream、sql_res 防御、thinking_result、OpenChatQuestion.sql_user_question。  
- **建议优先同步**：`check_sql` 的 session/operate 与 `trigger_log_error`，以及 `ds_res` 的 chunk 防御；其余按产品需求再选同步。
