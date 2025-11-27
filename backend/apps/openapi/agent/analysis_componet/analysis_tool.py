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
    description: str = "这是一个取数智能体。可以使用此工具获取需要的数据，非常聪明，能够准确理解你的取数需求，返回 pd.DataFrame 的json格式数据"

    class GetDataInput(BaseModel):
        query: str = Field(
            description="当前需要获取的数据，是人类的的自然语言描述。\n\n            ## 要求  \n\n            1. **一次性取全维度**：取数描述**必须一次性包含所有需要的相关维度**数据，禁止分多次请求\n                - 无明确要求下，**优先使用离散维度**；连续数据不利于分析\n                - **维度必须是 表Schema 中的维度**  \n            2. **一次取整个时间段**：**仅仅在明确取数时间的情况下**，取数描述必须一次性包含所有需要的时间段数据，禁止分多次请求，效率低下\n                - 时间段要表述清楚，如：近一年、昨天、上个月、2023年5月1日-2023年8月13日等\n                - **时间段跨度超过半年（6个月）的取月度数据**\n                - 没有给定的时间段则不需要带上时间段\n            3. **简洁描述**：描述需精炼，仅包含必要的筛选条件、时间段、维度和指标信息，剔除所有无关说明  \n            4. **单指标原则**：每次请求仅限获取 1 个指标数据  \n                - 只支持获取聚合指标（如：销售额、订单量、用户数、访问次数、点击率、退货量、库存量、离职率等）  \n            5. **筛选条件规则**  \n                - **禁止漏掉任务明确要求的筛选条件**，将其添加到筛选条件中，**使用原始词，禁止解释、转译、引申、改写、扩展等**  \n                - 筛选条件分为两种模式：\n                    - 表达式模式：例如 筛选城市为北京、品牌为Apple，筛选天气为雨天 等  \n                    - 关键词模式：例如 筛选北京，筛选CFO、算法工程师 等\n                - **筛选条件选择与分析任务中的模式一致**（分析任务中只提供关键词的用关键词模式，用表达式模式的用表达式），**禁止将关键词模式转换成表达式模式**  \n            6. 分析任务中有**分析我们部门/我们团队/我们小组/我部门/我团队/我小组等相关表达，则**表示限定取数范围**，**必须作为取数的筛选条件**  \n                - 此条件直接将原文放在筛选中，**禁止翻译成 维度=值 这种条件表达式**\n                - 仅有此条规则不用考虑维度必须是表 Schema 中的维度这条要求  \n            7. **筛选条件无法确定是哪个维度上的条件时，直接使用值来表达筛选条件**  \n\n            ## 返回格式  \n\n            筛选[条件1]、[条件2]、...、、[条件N] ，根据[维度1]、[维度2]、...、[维度N] 进行分组，统计[时间段]的[聚合指标]\n\n            注：筛选条件是可选项，如无必要不添加筛选条件，保证获取全的维度的数据；**[时间段] 是可选项，只在用户表达了时间的情况下存在**\n\n            ## 示例 (严格遵守上述格式与要求)\n\n            ### 无筛选条件例子  \n            例子一（没有给定时间段）：\n            根据商品类目、店铺进行分组，统计销售额\n            例子二：\n            根据大区、省份、城市、商品类别进行分组，统计最近一周的订单量\n            例子三：\n            根据新老客类型、注册渠道、用户性别进行分组，统计上月的购买用户数\n            例子四：\n            根据小时进行分组，统计过去24小时的网站访问次数\n            例子五：\n            根据销售渠道、商品品牌进行分组，统计本季度的退货量\n            例子六（没有给定时间段）：\n            根据仓库、SKU进行分组，统计库存量\n            例子七（时间跨度超过一年）：\n            根据商品类目、店铺、供应商进行分组，统计2024全年各月的退货率\n            例子八：\n            根据商家进行分组，统计最近30天的退款金额\n            例子九：\n            根据促销活动、商品类目、渠道进行分组，统计活动期间的曝光次数\n            例子十（时间跨度超过一年）：\n            根据商品类型、商家、店铺等级、SKU进行分组，统计2024年6月至2025年5月各月的销售量\n\n            ### 有筛选条件例子  \n            例子一：\n            筛选在线支付、未退货，根据商品类目、省份进行分组，统计2023年Q4的订单总额\n            例子二（要求 6）：\n            筛选我团队、日志级别为ERROR，根据应用服务名、服务器节点进行分组，统计今日00:00至今的错误日志数量\n            例子三（没有给定时间段）：\n            筛选iOS、访问频次大于等于3，根据用户年龄段、用户性别、注册渠道、页面类别进行分组，统计平均停留时长\n            例子四（要求 6）：\n            筛选我们部门、审批流程为报销、状态为未完成，根据报销类别、报销项目、报销金额区间进行分组，统计上个月的平均审批耗时\n            例子五（时间跨度超过一年）：\n            筛选原料批次为AX-2024、检测标准为ISO9001，根据生产线、班组长、时间段进行分组，统计本年度各月的次品率\n            例子六（要求 6）：\n            筛选我们小组，根据咨询产品类别进行分组，统计每周的平均会话响应时长\n            例子七（条件 7）：\n            筛选CFO，根据咨询产品类别进行分组，统计每周的平均会话响应时长\n\n            ---  \n            再次强调**禁止取明细数据**，必须明确说明聚合指标名  \n            不要漏掉筛选条件，避免获取错误的数据，并保证获取数据比较全面、完整")

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
                self.context.create_result(content=f"\n### 智能取数  \n"))

            await self.context.queue.put(
                self.context.create_result(content=f"\n#### 1. 取数 Query\n{query}  \n"))

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
                    return "获取数据异常,请重新尝试"

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
            self.context.queue.put_nowait(self.context.create_result(content=f"\n### 分析结果保存  \n"))
            self.context.queue.put_nowait(self.context.create_result(content=f"\n#### 分析过程  \n"))
            self.context.queue.put_nowait(self.context.create_result(content=f"\n  {analysis_process}  \n"))
            insights = [i.strip() for i in insight.split("<sep>")]
            insights_result = "\n".join(insights)
            self.context.queue.put_nowait(self.context.create_result(content=f"\n#### 分析结果  \n"))
            self.context.queue.put_nowait(self.context.create_result(content=f"\n  {insights_result}  \n"))

            return self.context.save_insight(df="None", insight=insights, analysis_process=analysis_process)

        except Exception as e:
            SQLBotLogUtil.error(e)
            SQLBotLogUtil.error("分析结论保存失败")
            self.context.queue.put_nowait(self.context.create_result(content=f"\n  分析结果保存失败  \n"))
            return "分析结论保存失败，请重新尝试"


class DataTransTool(BaseTool):
    name: str = "data_trans"
    description: str = "这是一个数据变换工具。可以使用此工具对数据的某一列计算占比、计算排名、计算和整体均值差以及计算增长，返回 pd.DataFrame 的json格式的数据"

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

    def _run(self, df: str, column: str, measure: str, measure_type: str, trans_type: str) -> str:
        try:
            SQLBotLogUtil.info("开始调用数据变换工具")
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
    description: str = "为用户的任务提供最终答案"

    class FinalAnswerInput(BaseModel):
        answer: str = Field(
            description="如果完成分析任务则返回完成分析结论，如果没有完成则给出没有完成的原因\n\n            ## 要求\n            1. 如果完成分析，则返回分析结论\n            2. 如果没有完成分析，则返回没有完成分析的原因\n            3. **必须使用中文回答，禁止给出任何程序代码**\n            4. 使用 **markdown** 格式")

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
            result = {
                "insights": self.context.insights or [],
                "summary": answer,
            }

            self.context.queue.put_nowait(self.context.create_result(content=f"\n### 总结结果  \n"))
            self.context.queue.put_nowait(self.context.create_result(content=f"\n  {answer}  \n"))

            return json.dumps(result, ensure_ascii=False)

        except Exception as e:
            SQLBotLogUtil.error(e)
            SQLBotLogUtil.error("final_answer工具调用失败")
            self.context.queue.put_nowait(self.context.create_result(content=f"\n  final_answer工具调用失败  \n"))
            return "最终答案处理失败"
