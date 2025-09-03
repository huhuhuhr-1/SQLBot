package com.sqlbot.example.controller;

import com.sqlbot.example.model.request.TestChatRequest;
import com.sqlbot.example.model.request.TestRecommendRequest;
import com.sqlbot.example.model.request.WorkflowRequest;
import com.sqlbot.example.model.response.WorkflowResult;
import com.sqlbot.example.service.WorkflowService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

/**
 * 业务流程测试控制器
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@RestController
@RequestMapping("/api/workflow")
@Tag(name = "业务流程测试接口", description = "完整业务流程和流式响应测试")
public class WorkflowController {

    @Autowired
    private WorkflowService workflowService;

    @PostMapping("/complete")
    @Operation(summary = "测试完整业务流程", description = "执行完整的6步SQLBot业务流程")
    public WorkflowResult testCompleteWorkflow(@RequestBody WorkflowRequest request) {
        try {
            return workflowService.executeCompleteWorkflow(request);
        } catch (Exception e) {
            return WorkflowResult.error("业务流程执行失败: " + e.getMessage());
        }
    }

    @PostMapping("/stream-chat")
    @Operation(summary = "测试流式聊天", description = "测试实时流式聊天响应")
    public SseEmitter testStreamChat(@RequestBody TestChatRequest request) {
        SseEmitter emitter = new SseEmitter(30000L); // 30秒超时

        // 异步执行，避免阻塞
        workflowService.executeStreamChat(request, emitter);

        return emitter;
    }

    @PostMapping("/stream-recommend")
    @Operation(summary = "测试流式推荐", description = "测试实时流式推荐响应")
    public SseEmitter testStreamRecommend(@RequestBody TestRecommendRequest request) {
        SseEmitter emitter = new SseEmitter(30000L); // 30秒超时

        // 异步执行，避免阻塞
        workflowService.executeStreamRecommend(request, emitter);

        return emitter;
    }
}
