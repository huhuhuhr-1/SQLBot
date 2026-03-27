# import asyncio
# import contextvars
# import threading
# import traceback
# from typing import Optional
#
# import orjson
# from fastapi import APIRouter, Depends, HTTPException
# from starlette.responses import StreamingResponse
#
# from apps.ai_model.model_factory import create_llm
# from apps.chat.curd.chat import get_chat_record_by_id, create_chat
# from apps.chat.models.chat_model import CreateChat
# from apps.openapi.agent.chat_agent import ChatAgent
# from apps.openapi.agent.plan_agent import PlanAgent
# from apps.openapi.models.openapiModels import OpenChatQuestion, OpenChat, OpenClean, DbBindChat, common_headers
# from apps.openapi.service.openapi_llm import LLMService
# from apps.openapi.service.openapi_service import merge_streaming_chunks, _get_chats_to_clean, \
#     _create_clean_response, _execute_cleanup, _run_analysis_or_predict
# from common.core.deps import SessionDep, CurrentUser, CurrentAssistant
# from common.utils.utils import SQLBotLogUtil
#
# router = APIRouter(tags=["chat"])
#
#
# @router.post("/chat", summary="聊天",
#              description="给定一个提示，模型将返回一条或多条预测消息",
#              dependencies=[Depends(common_headers)])
# async def chat(
#         session: SessionDep,
#         current_user: CurrentUser,
#         chat_question: OpenChatQuestion,
#         current_assistant: CurrentAssistant,
# ):
#     """
#     创建聊天完成（Create Chat Completion）
#
#     给定一个对话历史和用户输入，模型将返回一条或多条预测消息。
#     此接口遵循OpenAI Chat Completions API规范，支持流式响应。
#
#     Args:
#         session: 数据库连接
#         current_user: 当前认证用户信息
#         chat_question: 包含问题内容的请求对象
#         current_assistant: 当前使用的AI助手信息
#
#     Returns:
#         StreamingResponse: 流式响应对象，包含模型生成的回复内容
#
#     Raises:
#         HTTPException: 当处理过程中出现异常时抛出500错误
#     """
#     try:
#         # 传统sqlbot模式
#         if chat_question.chat_mode != "plan":
#             agent = ChatAgent(
#                 session=session,
#                 current_user=current_user,
#                 chat_question=chat_question,
#                 current_assistant=current_assistant)
#
#             # predict or analysis
#             if chat_question.task_type != "chat":
#                 await agent.run_analysis_or_predict()
#                 return StreamingResponse(agent.llm_service.await_result(), media_type="text/event-stream")
#             # chat
#             else:
#                 stream = await agent.run_chat()
#
#                 # 返回经过合并处理的流式响应
#                 return StreamingResponse(
#                     merge_streaming_chunks(stream=stream,
#                                            llm_service=agent.llm_service,
#                                            payload=agent.payload,
#                                            chat_question=agent.chat_question,
#                                            session=session),
#                     media_type="text/event-stream"
#                 )
#         # plan模式
#         else:
#             queue = asyncio.Queue()
#             llm = await create_llm()
#
#             async def _stream(queue):
#                 try:
#                     while True:
#                         try:
#                             # 使用带超时的get，避免无限阻塞
#                             data = await asyncio.wait_for(queue.get(), timeout=1.0)
#                         except asyncio.TimeoutError:
#                             # 超时后检查队列状态，如果队列为空则继续等待
#                             continue
#
#                         yield 'data:' + orjson.dumps(data).decode() + '\n\n'
#
#                         # 检查是否收到finish类型，如果是则结束流式响应
#                         if isinstance(data, dict) and data.get('type') == 'finish':
#                             break
#                         elif isinstance(data, dict) and data.get('type') == 'error':
#                             # 遇到错误也结束
#                             break
#                         else:
#                             # 正常数据，继续循环
#                             continue
#
#                 except GeneratorExit:
#                     # 生成器被外部终止 - 使用return结束整个stream函数
#                     return
#                 except Exception as e:
#                     # 发送错误信息并结束 - 使用return结束整个stream函数
#                     error_data = {
#                         "type": "error",
#                         "content": f"Stream error: {str(e)}"
#                     }
#                     yield 'data:' + orjson.dumps(error_data).decode() + '\n\n'
#                     return
#
#             def run_task(context,
#                          current_user,
#                          chat_question,
#                          current_assistant,
#                          queue):
#                 # 为子线程创建独立的数据库session，确保线程安全
#                 from common.core.db import get_db_session
#
#                 with get_db_session() as thread_session:
#                     context.run(lambda: asyncio.run(
#                         PlanAgent(
#                             session=thread_session,
#                             current_user=current_user,
#                             chat_question=chat_question,
#                             current_assistant=current_assistant,
#                             queue=queue,
#                             llm=llm).execute_plan()))
#
#             thread = threading.Thread(target=run_task,
#                                       args=(contextvars.copy_context(),
#                                             current_user,
#                                             chat_question,
#                                             current_assistant, queue),
#                                       daemon=True)
#             thread.start()
#             return StreamingResponse(
#                 _stream(queue),
#                 media_type="text/event-stream"
#             )
#
#     except Exception as e:
#         # 记录异常信息用于调试
#         SQLBotLogUtil.error(f"聊天接口异常: {str(e)}")
#         traceback.print_exc()
#         raise HTTPException(
#             status_code=500,
#             detail=f"聊天处理失败: {str(e)}"
#         )
#
#
# @router.post("/createRecordAndBindDb")
# async def bind_data_source(session: SessionDep, current_user: CurrentUser, db_bind_chat: DbBindChat):
#     """
#     绑定数据源并开始聊天
#
#     根据指定的数据源ID和用户输入，创建一个新的聊天记录并开始聊天。
#
#     Args:
#         session: 数据库会话依赖
#         current_user: 当前认证用户信息
#         db_bind_chat: 包含数据源ID和用户输入的请求对象
#
#     Returns:
#         创建的聊天记录对象
#
#     Raises:
#         HTTPException: 当处理过程中出现异常时抛出500错误
#     """
#     try:
#         create_chat_obj = CreateChat(
#             datasource=db_bind_chat.db_id,
#             question=db_bind_chat.title
#         )
#         return create_chat(session, current_user, create_chat_obj)
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=str(e)
#         )
#
#
# @router.post("/getRecommend", dependencies=[Depends(common_headers)])
# async def get_recommend(
#         session: SessionDep,
#         current_user: CurrentUser,
#         chat_record: OpenChat,
#         current_assistant: CurrentAssistant
# ):
#     """
#     流式生成推荐问题
#
#     基于指定的聊天记录，异步生成推荐问题并以流式方式返回结果。
#
#     Args:
#         session: 数据库连接
#         current_user: 当前认证用户信息
#         chat_record: 聊天对象，包含聊天记录ID
#         current_assistant: 当前使用的AI助手信息
#
#     Returns:
#         StreamingResponse: 流式响应，包含生成的推荐问题
#
#     Raises:
#         HTTPException: 当聊天记录不存在或处理异常时抛出相应错误
#     """
#     try:
#         chat_record_id = chat_record.chat_record_id
#         # 获取聊天记录
#         record = None
#         from common.core.db import get_session
#         for session in get_session():
#             record = get_chat_record_by_id(session, chat_record_id)
#         # 验证聊天记录是否存在
#         if record is None:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"Chat record with id {chat_record_id} not found"
#             )
#
#         # 创建问题请求对象
#         chat_question = OpenChatQuestion(
#             chat_id=record.chat_id,
#             question=record.question if record.question else ''
#         )
#
#         # 创建LLM服务实例并设置推荐问题模式
#         llm_service = await LLMService.create(
#             session=session,
#             current_user=current_user,
#             chat_question=chat_question,
#             current_assistant=current_assistant,
#             no_reasoning=chat_record.no_reasoning,
#             embedding=True
#         )
#
#         # 设置聊天记录
#         llm_service.set_record(record)
#
#         # 异步运行推荐问题生成任务
#         llm_service.run_recommend_questions_task_async()
#     except Exception as e:
#         # 打印异常堆栈信息用于调试
#         traceback.print_exc()
#         raise HTTPException(
#             status_code=500,
#             detail=str(e)
#         )
#
#     # 返回流式响应
#     return StreamingResponse(llm_service.await_result(), media_type="text/event-stream")
#
#
# @router.post("/deleteChats", summary="清理",
#              description="清理当前用户的所有聊天记录",
#              dependencies=[Depends(common_headers)])
# async def clean_all_chat_record(
#         session: SessionDep,
#         current_user: CurrentUser,
#         clean: OpenClean
# ):
#     """
#     清理当前用户的聊天记录
#
#     Args:
#         session: 数据库会话依赖
#         current_user: 当前认证用户信息
#         clean: 清理对象，包含要清理的聊天记录ID列表
#
#     Returns:
#         dict: 操作结果，包含成功和失败的记录数
#     """
#     try:
#         # 获取要清理的聊天记录列表
#         chat_list = _get_chats_to_clean(session, current_user, clean)
#
#         if not chat_list:
#             return _create_clean_response(0, 0, 0)
#
#         # 执行清理操作
#         success_count, failed_count, failed_records = _execute_cleanup(
#             session,
#             chat_list
#         )
#
#         # 返回操作结果
#         return _create_clean_response(success_count, failed_count, len(chat_list))
#
#     except Exception as e:
#         SQLBotLogUtil.error(f"清理聊天记录异常: {str(e)}")
#         traceback.print_exc()
#         raise HTTPException(
#             status_code=500,
#             detail=f"清理聊天记录失败: {str(e)}"
#         )
#
#
# @router.post("/analysis", summary="分析",
#              description="对指定聊天记录进行分析",
#              dependencies=[Depends(common_headers)])
# async def analysis_chat_record(
#         session: SessionDep,
#         current_user: CurrentUser,
#         chat_record: OpenChat,
#         current_assistant: CurrentAssistant
# ):
#     """
#     对指定聊天记录进行分析
#
#     Args:
#         session: 数据库连接
#         current_user: 当前认证用户信息
#         chat_record: 聊天对象，包含聊天记录ID
#         current_assistant: 当前使用的AI助手信息
#
#     Returns:
#         StreamingResponse: 流式响应，包含分析结果
#     """
#     return await _run_analysis_or_predict(session, current_user, chat_record, current_assistant, 'analysis')
#
#
# @router.post("/predict", summary="预测",
#              description="对指定聊天记录进行预测",
#              dependencies=[Depends(common_headers)])
# async def predict_chat_record(
#         session: SessionDep,
#         current_user: CurrentUser,
#         chat_record: OpenChat,
#         current_assistant: CurrentAssistant
# ):
#     """
#     对指定聊天记录进行预测
#
#     Args:
#         session: 数据库连接
#         current_user: 当前认证用户信息
#         chat_record: 聊天对象，包含聊天记录ID
#         current_assistant: 当前使用的AI助手信息
#
#     Returns:
#         StreamingResponse: 流式响应，包含预测结果
#     """
#     return await _run_analysis_or_predict(session, current_user, chat_record, current_assistant, 'predict')