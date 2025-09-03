package com.sqlbot.example.service;

import com.sqlbot.example.model.request.TestChatRequest;
import com.sqlbot.example.model.request.TestRecommendRequest;
import com.sqlbot.example.model.request.WorkflowRequest;
import com.sqlbot.example.model.response.WorkflowResult;
import com.sqlbot.springboot.starter.SQLBotClient;
import com.sqlbot.springboot.starter.model.response.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;


import java.util.List;

/**
 * 业务流程服务
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Service
public class WorkflowService {

    @Autowired
    private SQLBotClient sqlBotClient;

    public WorkflowResult executeCompleteWorkflow(WorkflowRequest request) throws Exception {
        WorkflowResult result = new WorkflowResult();

        try {
            // 第一步：用户登录获取令牌
            GetTokenResponse tokenResponse = sqlBotClient.getToken(
                    request.getUsername(), request.getPassword(), true);
            result.addStep("登录", "成功", tokenResponse.getAccessToken());

            // 第二步：获取数据源列表
            List<DataSourceResponse> dataSources = sqlBotClient.getDataSourceList();
            result.addStep("获取数据源", "成功", "共" + dataSources.size() + "个数据源");

            // 第三步：进行聊天对话
            if (!dataSources.isEmpty()) {
                ChatResponse chatResponse = sqlBotClient.chat(
                        dataSources.get(0).getId(),
                        request.getQuestion(),
                        tokenResponse.getChatId());
                result.addStep("聊天对话", "成功", "聊天记录ID: " + chatResponse.getChatRecordId());

                // 第四步：获取聊天数据
                GetDataResponse dataResponse = sqlBotClient.getData(chatResponse.getChatRecordId());
                result.addStep("获取数据", "成功", "图表类型: " + dataResponse.getChartType());

                // 第五步：获取推荐问题
                GetRecommendResponse recommendResponse = sqlBotClient.getRecommend(chatResponse.getChatRecordId());
                result.addStep("获取推荐", "成功", "推荐数量: " +
                        (recommendResponse.getRecommendations() != null ? recommendResponse.getRecommendations().size() : 0));

                // 第六步：清理聊天记录
                CleanResponse cleanResponse = sqlBotClient.cleanAll();
                result.addStep("清理记录", "成功", "清理数量: " + cleanResponse.getSuccessCount());
            }

            result.setSuccess(true);
            result.setMessage("完整业务流程执行成功");

        } catch (Exception e) {
            result.setSuccess(false);
            result.setMessage("业务流程执行失败: " + e.getMessage());
            result.addStep("错误", "失败", e.getMessage());
        }

        return result;
    }

    @Async
    public void executeStreamChat(TestChatRequest request, SseEmitter emitter) {
        try {
            // 发送开始消息
            emitter.send(SseEmitter.event()
                    .name("message")
                    .data("开始流式聊天..."));

            emitter.send(SseEmitter.event()
                    .name("message")
                    .data("问题: " + request.getQuestion()));

            emitter.send(SseEmitter.event()
                    .name("message")
                    .data("正在处理..."));

            emitter.send(SseEmitter.event()
                    .name("message")
                    .data("流式响应完成"));

            // 完成发送
            emitter.complete();

        } catch (Exception e) {
            try {
                emitter.send(SseEmitter.event()
                        .name("message")
                        .data("错误: " + e.getMessage()));
                emitter.complete();
            } catch (Exception ex) {
                emitter.completeWithError(ex);
            }
        }
    }

    @Async
    public void executeStreamRecommend(TestRecommendRequest request, SseEmitter emitter) {
        try {
            // 发送开始消息
            emitter.send(SseEmitter.event()
                    .name("message")
                    .data("开始流式推荐..."));

            emitter.send(SseEmitter.event()
                    .name("message")
                    .data("正在生成推荐问题..."));

            emitter.send(SseEmitter.event()
                    .name("message")
                    .data("推荐问题1: 查询用户表数据"));

            emitter.send(SseEmitter.event()
                    .name("message")
                    .data("推荐问题2: 分析销售趋势"));

            emitter.send(SseEmitter.event()
                    .name("message")
                    .data("推荐问题3: 统计订单数量"));

            emitter.send(SseEmitter.event()
                    .name("message")
                    .data("流式推荐完成"));

            // 完成发送
            emitter.complete();

        } catch (Exception e) {
            try {
                emitter.send(SseEmitter.event()
                        .name("message")
                        .data("错误: " + e.getMessage()));
                emitter.complete();
            } catch (Exception ex) {
                emitter.completeWithError(ex);
            }
        }
    }
}
