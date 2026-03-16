# -*- coding: utf-8 -*-
""" 
@Time    : 2025/11/10 14:24
@Author  : chenshu
@FileName: analysis_tool.py
@Description: 
"""
import json
from typing import Any, Dict, List
from typing import Type

import numpy as np
import pandas as pd
from langchain.tools import BaseTool
from langchain_core.pydantic_v1 import BaseModel, Field

from apps.openapi.agent.analysis_componet.data_model import DataModel, Measure, SiblingGroup, AnalysisContext
from apps.openapi.agent.analysis_componet.insights import InsightFactoryDict, InsightType
from common.utils.utils import SQLBotLogUtil
from sqlmodel import Session

pd.set_option("display.max_columns", None)


class GetDataTool(BaseTool):
    name: str = "get_data"
    description: str = (
        "取数智能体：自然语言描述需求，返回 pd.DataFrame 的 JSON。"
        "**同一表同一时间窗尽量一次取全多维度**；常态下全任务调用本工具约 2～4 次即可，避免同表重复查。"
        "先判断当前问题属于聚合分析还是快照/详情查询：聚合问题返回聚合结果，快照/详情问题允许返回受控的记录级结果。"
    )

    class GetDataInput(BaseModel):
        query: str = Field(
            description="当前需要获取的数据，是人类的自然语言描述。\n\n            ## 第一步：先判断取数模式  \n\n            1. **聚合模式（aggregate）**：当问题在问次数、数量、总量、均值、占比、趋势、排名、对比时，优先获取聚合结果  \n            2. **快照模式（snapshot/detail）**：当问题在问最新、最后一次、最近一次、当前状态、详情、明细记录时，允许获取**受控的记录级结果**，直接返回回答问题所需字段，禁止先改写成次数或趋势  \n\n            ## 通用要求  \n\n            1. **一次性取全必要字段**：取数描述必须一次性包含回答当前子问题所需的相关字段，禁止分多次请求同一事实  \n                - 字段必须来自表 Schema  \n                - 仅保留直接回答问题所需的最小字段集合  \n            2. **一次取整个时间段**：仅在问题明确给定时间范围时，取数描述必须一次性覆盖所需时间段  \n                - 时间段要表述清楚，如：近一年、昨天、上个月、2023年5月1日-2023年8月13日等\n                - **仅对趋势/聚合分析**，时间跨度超过半年（6个月）时优先考虑月度粒度\n                - **对快照模式不要因为时间跨度较长就自动改成月度汇总**\n            3. **简洁描述**：仅包含必要的筛选条件、时间段、字段/维度和指标信息，剔除无关说明  \n            4. **筛选条件规则**  \n                - **禁止漏掉任务明确要求的筛选条件**，使用原始词，禁止解释、转译、引申、改写、扩展等  \n                - 筛选条件分为两种模式：\n                    - 表达式模式：例如 筛选城市为北京、品牌为Apple，筛选天气为雨天 等  \n                    - 关键词模式：例如 筛选北京，筛选CFO、算法工程师 等\n                - **筛选条件选择与分析任务中的模式一致**，禁止将关键词模式转换成表达式模式  \n            5. 分析任务中有**分析我们部门/我们团队/我们小组/我部门/我团队/我小组等相关表达**时，表示限定取数范围，必须作为筛选条件  \n                - 此条件直接将原文放在筛选中，禁止翻译成 `维度=值` 这种条件表达式\n            6. **筛选条件无法确定属于哪个维度时，直接使用值表达筛选条件**  \n\n            ## 返回格式  \n\n            - 聚合模式：`筛选[条件1]、[条件2]...，根据[维度1]、[维度2]...进行分组，统计[时间段]的[聚合指标]`\n            - 快照模式：`筛选[条件1]、[条件2]...，获取[时间段]内每个[实体]最近一次/当前有效的[字段1]、[字段2]、[字段3]...记录`\n\n            ## 关键约束  \n\n            - 聚合模式下，每次请求只围绕 **1 个核心指标** 组织结果  \n            - 快照模式下，允许返回记录级字段，但必须能**直接回答主问题**，且字段数量受控  \n            - **禁止把快照/详情问题改写成聚合统计问题**  \n            - 避免获取错误或无关数据，保证结果完整、可直接用于回答问题")

    args_schema: Type[BaseModel] = GetDataInput
    context: AnalysisContext = None
    session: Session = None

    def __init__(self, context: AnalysisContext, session: Session):
        super().__init__()
        self.context = context
        self.session = session

    def _run(self, query: str) -> str:
        SQLBotLogUtil.error("调用非流式的get_data")
        return ""

    async def _arun(self, query: str) -> str:
        try:
            SQLBotLogUtil.info("开始调用智能取数工具")
            await self.context.queue.put(
                self.context.create_result(content="当前阶段：智能取数", message_type="stage"))
            await self.context.queue.put(
                self.context.create_result(content=f"\n### 智能取数  \n"))

            await self.context.queue.put(
                self.context.create_result(content=f"\n#### 1. 取数 Query\n{query}  \n"))

            granularity = (self.context.answer_granularity or "").strip()
            if granularity == "single_latest_record":
                query = f"{query}。只返回最近一条记录，结果应为 1 条"
            elif granularity == "latest_record_per_entity":
                query = f"{query}。每个实体返回最近一条，最终结果最多 {self.context.max_data_size} 行"
            else:
                query = f"{query}。取 {self.context.max_data_size} 条"

            await self.context.queue.put(
                self.context.create_result(content=f"\n#### 2. 生成取数 SQL \n"))

            df = None

            async for result in self.context.llm_service.get_data_for_plan(
                    _session=self.session,
                    query=query,
                    is_chart_output=self.context.is_chart_output):
                result_type = result["type"]
                result_data = result["data"]

                if result_type == "error":
                    await self.context.queue.put(
                        self.context.create_result(content=f"\n {result_data} \n"))
                    # 将具体错误原因返回给 agent，避免同一错误反复重试（如图表配置解析失败）
                    return result_data if isinstance(result_data, str) and result_data.strip() else "获取数据异常,请重新尝试"

                elif result_type == "sql_result":
                    sql = result_data["sql"]
                    enhanced_think_result = result_data["enhanced_think_result"]
                    if len(enhanced_think_result) != 0:
                        await self.context.queue.put(
                            self.context.create_result(content=f"\n#### 思考过程\n{enhanced_think_result}\n"))
                    await self.context.queue.put(
                        self.context.create_result(content=f"\n```sql\n{sql.strip()}\n```\n"))
                    await self.context.queue.put(
                        self.context.create_result(content=f"\n#### 3. 执行生成的 SQL \n"))

                elif result_type == "sql_execute_result":
                    await self.context.queue.put(
                        self.context.create_result(content=f"\n {result_data} \n"))
                    await self.context.queue.put(
                        self.context.create_result(content=f"\n#### 4. 取数结果 \n"))

                elif result_type == "chart_result":
                    if self.context.is_chart_output:
                        df = pd.DataFrame(
                            np.array(result_data["pd_data"]["data"]), columns=result_data["pd_data"]["columns"])

                        output_data = result_data["output_data"]

                        if isinstance(output_data, str):
                            top_k = min(5, len(df))
                            await self.context.queue.put(self.context.create_result(
                                content=f"\n共获取到 {len(df)} 条数据，前 {top_k} 条数据如下：\n\n{df[: top_k].to_markdown(index=False)}\n"))
                        else:
                            for chart_result in output_data:
                                await self.context.queue.put(chart_result)
                    else:
                        df = pd.DataFrame(np.array(result_data["data"]), columns=result_data["columns"])
                        top_k = min(5, len(df))
                        self.context.queue.put_nowait(self.context.create_result(
                            content=f"\n共获取到 {len(df)} 条数据，前 {top_k} 条数据如下：\n\n{df[: top_k].to_markdown(index=False)}\n"))
            if df is not None:
                final_result = df.to_json()
                await self.context.queue.put(self.context.create_result(content=f"\n  本次取数结束  \n"))
                return final_result
            else:
                await self.context.queue.put(self.context.create_result(content=f"\n  取数结果为空  \n"))
                return "获取数据异常,请重新尝试"

        except Exception as e:
            SQLBotLogUtil.error(e)
            SQLBotLogUtil.error("取数工具调用失败")
            self.context.queue.put_nowait(self.context.create_result(content=f"\n  取数工具调用失败  \n"))
            return "获取数据异常,请重新尝试"


class InsightTool(BaseTool):
    name: str = "insight_analysis"
    description: str = "这是一个传统数据分析工具。可以使用此工具做一些常见数据分析。\n        \n    ## 支持的分析类型  \n\n    - OutstandingFirst: 分析指标表现最高的情况\n    - OutstandingLast: 分析指标表现最差的情况\n    - Attribution: 分析指标表现最高的是否占据绝对优势，对整体指标影响占据主要地位\n    - Evenness: 分析指标是否平稳\n    - Trend: 分析指标趋势，**指标需要有时序**\n    - Correlation: 分析相关性，看两个维度是否具有相同或者相反表现，维度必须是数字类型\n    - ChangePoint: 分析拐点，看数据在哪个点出现转折，**指标需要有时序**\n\n    ---\n    返回 Dict 类型的分析结果"

    class InsightInput(BaseModel):
        df: str = Field(description="分析的数据，必须是 pd.DataFrame 的json类型")
        breakdown: str = Field(
            description="需要分析的维度，也可以理解需要下钻分析的维度。必须是 df 数据中的列，禁止捏造维度，如果是序列分析（如 Trend、ChangePoint）则必须是时间序列的维度")
        measure: str = Field(
            description="分析的指标，必须是 df 数据中的列，禁止捏造指标，指标列只能是数值类型，不能有 nan 值，如果有请合理处理")
        measure_type: str = Field(
            description="指标的类型，只有 quantity、ratio 两种。quantity 表示数量类型指标，ratio 表示比率类型指标。")
        analysis_method: str = Field(
            description="当前支持的分析方法。只有如下几种类型：\n            - OutstandingFirst: 分析指标表现最高的情况\n            - OutstandingLast: 分析指标表现最差的情况\n            - Attribution: 分析指标表现最高的是否占据绝对优势，对整体指标影响占据主要地位\n            - Evenness: 分析指标是否平稳\n            - Trend: 分析指标趋势，**指标需要有时序**\n            - Correlation: 分析相关性，看两个维度是否具有相同或者相反表现，维度必须是数字类型\n            - ChangePoint: 分析拐点，看数据在哪个点出现转折，**指标需要有时序**\n\n            **必须是上述几种取值**")

    args_schema: Type[BaseModel] = InsightInput
    context: AnalysisContext = None
    session: Session = None

    def __init__(self, context: AnalysisContext, session: Session):
        super().__init__()
        self.context = context
        self.session = session

    def _run(self, df: str, breakdown: str, measure: str, measure_type: str, analysis_method: str) -> List[
        Dict[str, Any]]:
        try:
            SQLBotLogUtil.info("开始调用数据分析工具")
            self.context.queue.put_nowait(
                self.context.create_result(content="当前阶段：分析洞察", message_type="stage"))
            self.context.queue.put_nowait(self.context.create_result(content=f"\n### 数据分析  \n"))
            try:
                df = pd.read_json(df)
            except Exception as e:
                SQLBotLogUtil.error(e)
                SQLBotLogUtil.error("数据分析df转换失败")
                self.context.queue.put_nowait(self.context.create_result(
                    content=f"\n  传入的分析数据工具的df数据格式有误，无法转换成pd.DataFrame格式  \n"))

                return "传入的分析数据df数据格式有误，无法转换成pd.DataFrame格式"

            if analysis_method in ["Trend", "ChangePoint"]:
                target_col = df[breakdown].dropna()
                if not isinstance(target_col, bool) and not target_col.empty():
                    val = str(target_col.iloc[0])
                    if len(val) == 4:
                        format = "%Y"
                    elif len(val) == 6:
                        format = "%Y%m"
                    elif len(val) == 7:
                        format = "%Y-%m"
                    elif len(val) == 8:
                        format = "%Y%m%d"
                    elif len(val) == 10:
                        format = "%Y-%m-%d"
                    else:
                        format = "%Y-%m-%d"
                else:
                    format = "%Y-%m-%d"
                df[breakdown] = pd.to_datetime(df[breakdown], format=format, errors="coerce")

            data_model = DataModel(
                data=df,
                measure=Measure(name=measure, column=measure, agg="sum" if measure_type == "quantity" else "max",
                                type=measure_type),
            )

            breakdown_col = [c for c in data_model.columns if c.name == breakdown][0]
            sibling_group = SiblingGroup(data=data_model, breakdown=breakdown_col)
            insight: InsightType = InsightFactoryDict[analysis_method].from_data(sibling_group)

            if insight:
                self.context.queue.put_nowait(self.context.create_result(content=f"\n  数据分析工具调用成功  \n"))
                return insight.model_dump(exclude={"data", })
            else:
                self.context.queue.put_nowait(
                    self.context.create_result(content=f"\n  数据分析工具调用结果： 无分析结论 \n"))
                return {"description": "无分析结论"}
        except Exception as e:
            SQLBotLogUtil.error(e)
            SQLBotLogUtil.error("数据分析工具调用失败")
            self.context.queue.put_nowait(self.context.create_result(content=f"\n  数据分析工具调用失败  \n"))
            return "数据分析失败，请重新尝试"


class SaveInsightTool(BaseTool):
    name: str = "save_insight"
    description: str = "这是一个分析结论保存工具。请你将你每一步分析得出的**有用的结论或信息**调用此工具保存到数据库中，“无分析结论” 等无效分析结果禁止保存，**不要保存非分析结论的信息**。多个结论可以多次调用"

    class SaveInsightInput(BaseModel):
        df: str = Field(
            description="分析的数据，**必须是 pd.DataFrame 的json类型数据**，用来**直接**展示证明你的分析结论。请提供**变换后直接得到分析结论的 pd.DataFrame 类型数据**，而不是变换前的太长的 pd.DataFrame 类型数据")
        insight: str = Field(
            description="分析洞察，**分析获得的数据或结论**，不是无信息量或者无意义的句子。insight 必须和 df 参数提供的数据对应，禁止出现 df 的数据和 insight 不相关的情况，禁止保存基于 df 的部分数据得出结论，禁止分析结论中存在未知信息或者 XX 等占位符信息。如果有多个洞察则多个洞察之间使用 <sep> 分割")
        analysis_process: str = Field(description="分析过程，**简单总结**使用的分析方法和分析过程")

    args_schema: Type[BaseModel] = SaveInsightInput
    context: AnalysisContext = None
    session: Session = None

    def __init__(self, context: AnalysisContext, session: Session):
        super().__init__()
        self.context = context
        self.session = session

    def _run(self, df: str, insight: str, analysis_process: str) -> str:
        try:
            SQLBotLogUtil.info("开始调用分析结论保存工具")
            self.context.queue.put_nowait(
                self.context.create_result(content="当前阶段：沉淀结论", message_type="stage"))
            self.context.queue.put_nowait(self.context.create_result(content=f"\n### 分析结果保存  \n"))
            self.context.queue.put_nowait(self.context.create_result(content=f"\n#### 分析过程  \n"))
            self.context.queue.put_nowait(self.context.create_result(content=f"\n  {analysis_process}  \n"))
            insights = [i.strip() for i in insight.split("<sep>")]
            insights_result = "\n".join(insights)
            self.context.queue.put_nowait(self.context.create_result(content=f"\n#### 分析结果  \n"))
            self.context.queue.put_nowait(self.context.create_result(content=f"\n  {insights_result}  \n"))

            return self.context.save_insight(df=df, insight=insights, analysis_process=analysis_process)

        except Exception as e:
            SQLBotLogUtil.error(e)
            SQLBotLogUtil.error("分析结论保存失败")
            self.context.queue.put_nowait(self.context.create_result(content=f"\n  分析结果保存失败  \n"))
            return "分析结论保存失败，请重新尝试"


class DataTransTool(BaseTool):
    name: str = "data_trans"
    description: str = (
        "这是一个数据变换工具。可以对数值型指标做占比、排名、与整体均值差、序列增长等变换，"
        "返回 pd.DataFrame 的 json 格式数据。"
        "适用于数值指标分析，不适用于把时间戳/日期字段当作指标做聚合或转换。"
    )

    class DataTransInput(BaseModel):
        df: str = Field(description="分析的数据，必须是 pd.DataFrame 的json类型")
        column: str = Field(description="分析的维度，可以理解为变换中需要 group 的列，或者是时间序列列")
        measure: str = Field(
            description="需要变换的指标维度，必须是 df 数据中的列，禁止捏造指标，指标列只能是数值类型，不能有 nan 值，如果有请合理处理")
        measure_type: str = Field(
            description="指标的类型，只有 quantity、ratio 两种。quantity 表示数量类型指标，ratio 表示比率类型指标。")
        trans_type: str = Field(
            description="数据转换类型，只支持如下类型：\n            - rate: 将某列转换为占比\n            - rank: 按照某列计算排名\n            - increase: 序列分析，计算增长\n            - sub_avg: 算与整体均值的差值")

    args_schema: Type[BaseModel] = DataTransInput
    context: AnalysisContext = None
    session: Session = None

    def __init__(self, context: AnalysisContext, session: Session):
        super().__init__()
        self.context = context
        self.session = session

    @staticmethod
    def _validate_columns(df: pd.DataFrame, column: str, measure: str) -> str | None:
        missing_columns = [name for name in [column, measure] if name not in df.columns]
        if missing_columns:
            return f"数据变换失败，缺少字段: {', '.join(missing_columns)}"
        return None

    @staticmethod
    def _validate_measure_dtype(df: pd.DataFrame, measure: str, trans_type: str) -> str | None:
        measure_series = df[measure]
        if pd.api.types.is_datetime64_any_dtype(measure_series):
            return (
                f"数据变换失败，字段 `{measure}` 是时间/时间戳类型。"
                f"`data_trans` 仅支持对数值型指标做 `{trans_type}` 变换，"
                "不要把时间字段当作 measure；如果需要处理最近一次/最新时间，请直接在 SQL 中完成排序、取最新记录，"
                "或把时间字段作为 column 使用。"
            )
        if not pd.api.types.is_numeric_dtype(measure_series):
            return (
                f"数据变换失败，字段 `{measure}` 不是数值类型。"
                f"`data_trans` 仅支持对数值型指标做 `{trans_type}` 变换，请更换为数值指标列。"
            )
        return None

    def _run(self, df: str, column: str, measure: str, measure_type: str, trans_type: str) -> str:
        try:
            SQLBotLogUtil.info("开始调用数据变换工具")
            self.context.queue.put_nowait(
                self.context.create_result(content="当前阶段：数据变换", message_type="stage"))
            self.context.queue.put_nowait(self.context.create_result(content=f"\n### 数据变换  \n"))

            assert trans_type in ["rate", "rank", "increase", "sub_avg"]
            agg = "sum" if measure_type == "quantity" else "max"
            try:
                df = pd.read_json(df)
            except Exception as e:
                SQLBotLogUtil.error(e)
                SQLBotLogUtil.error("数据变换工具df解析失败")
                self.context.queue.put_nowait(self.context.create_result(
                    content=f"\n  传入的分析数据df数据格式有误，无法转换成pd.DataFrame格式  \n"))
                return "传入的分析数据df数据格式有误，无法转换成pd.DataFrame格式"

            column_error = self._validate_columns(df, column, measure)
            if column_error:
                self.context.queue.put_nowait(self.context.create_result(content=f"\n  {column_error}  \n"))
                return column_error

            dtype_error = self._validate_measure_dtype(df, measure, trans_type)
            if dtype_error:
                self.context.queue.put_nowait(self.context.create_result(content=f"\n  {dtype_error}  \n"))
                return dtype_error

            if trans_type == "rate":
                df = df.groupby(column).agg({measure: agg}).reset_index()
                df[f"Rate({measure})"] = df[measure] / df[measure].sum()
            if trans_type == "increase":
                df = df.groupby(column).agg({measure: agg}) \
                    .sort_values(by=column, ascending=True).reset_index()
                df[f"Increase({measure})"] = df[measure].diff(1)
                df = df.dropna()
            if trans_type == "sub_avg":
                df = df.groupby(column).agg({measure: agg}).reset_index()
                avg = df[measure].sum() / df[measure].size
                df[f"{measure}-avg"] = df[measure] - avg
            if trans_type == "rank":
                df = df.groupby(column).agg({measure: agg}).reset_index()
                df[f"Rank({measure})"] = df[measure].rank(ascending=False, method="dense").astype(int)

            self.context.queue.put_nowait(self.context.create_result(content=f"\n  数据变换工具调用成功  \n"))
            return df.to_json()

        except Exception as e:
            SQLBotLogUtil.error(e)
            SQLBotLogUtil.error("数据变换失败工具调用失败")
            self.context.queue.put_nowait(self.context.create_result(content=f"\n  数据变换工具调用失败  \n"))

            return "数据变换失败，请重新尝试"


class FinalAnswerTool(BaseTool):
    name: str = "final_answer"
    description: str = (
        "输出唯一面向用户的综合分析报告（Markdown）。必须包含六级标题："
        "## 1. 问题与口径 / ## 2. 核心结论（3～5 条）/ ## 3. 数据支撑 / ## 4. 风险与异常 / "
        "## 5. 建议（可执行）/ ## 6. 局限。禁止仅输出几句话。禁止程序代码。"
    )

    class FinalAnswerInput(BaseModel):
        answer: str = Field(
            description=(
                "完整 Markdown 报告，必须依次包含："
                "## 1. 问题与口径（问题、时间范围、主数据源与辅表、指标说明）；"
                "## 2. 核心结论（3～5 条 bullet）；"
                "## 3. 数据支撑（表格+简短解释，可选 SQL）；"
                "## 4. 风险与异常；## 5. 建议；## 6. 局限。"
                "中文，无代码。"
            )
        )

    args_schema: Type[BaseModel] = FinalAnswerInput
    context: AnalysisContext = None
    session: Session = None

    def __init__(self, context: AnalysisContext, session: Session):
        super().__init__()
        self.context = context
        self.session = session

    def _run(self, answer: str) -> str:
        try:
            SQLBotLogUtil.info("开始调用最终结论工具")
            self.context.queue.put_nowait(
                self.context.create_result(content="当前阶段：汇总报告", message_type="stage"))
            result = {
                "insights": self.context.insights or [],
                "summary": answer,
            }

            self.context.queue.put_nowait(
                self.context.create_result(content=answer, message_type="report"))

            return json.dumps(result, ensure_ascii=False)

        except Exception as e:
            SQLBotLogUtil.error(e)
            SQLBotLogUtil.error("final_answer工具调用失败")
            self.context.queue.put_nowait(self.context.create_result(content=f"\n  final_answer工具调用失败  \n"))
            return "最终答案处理失败"
