package com.sqlbot.example.controller;

import com.sqlbot.example.model.request.*;
import com.sqlbot.example.model.response.TestResult;
import com.sqlbot.example.service.SQLBotTestService;
import com.sqlbot.springboot.starter.model.response.*;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;

/**
 * SQLBot测试控制器
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@RestController
@RequestMapping("/api/test")
@Tag(name = "SQLBot API测试接口", description = "SQLBot核心功能测试接口")
public class SQLBotTestController {

    @Autowired
    private SQLBotTestService sqlBotTestService;

    @PostMapping("/login")
    @Operation(summary = "测试登录接口", description = "测试用户登录获取访问令牌")
    public TestResult<GetTokenResponse> testLogin(@RequestBody TestLoginRequest request) {
        try {
            GetTokenResponse response = sqlBotTestService.testLogin(request);
            return TestResult.success(response);
        } catch (Exception e) {
            return TestResult.error("登录测试失败: " + e.getMessage());
        }
    }

    @GetMapping("/datasources")
    @Operation(summary = "测试获取数据源接口", description = "测试获取可用的数据源列表")
    public TestResult<List<DataSourceResponse>> testGetDataSources() {
        try {
            List<DataSourceResponse> response = sqlBotTestService.testGetDataSources();
            return TestResult.success(response);
        } catch (Exception e) {
            return TestResult.error("获取数据源测试失败: " + e.getMessage());
        }
    }

    @PostMapping("/chat")
    @Operation(summary = "测试聊天接口 - SSE流式返回", description = "测试AI智能对话功能，支持SSE流式响应")
    public SseEmitter testChat(@RequestBody TestChatRequest request) {
        SseEmitter emitter = new SseEmitter(30000L); // 30秒超时
        
        // 异步执行，避免阻塞
        sqlBotTestService.testChatStream(request, emitter);
        
        return emitter;
    }

    @PostMapping("/getData")
    @Operation(summary = "测试获取数据接口", description = "测试获取聊天记录的结构化数据")
    public TestResult<GetDataResponse> testGetData(@RequestBody TestDataRequest request) {
        try {
            GetDataResponse response = sqlBotTestService.testGetData(request);
            return TestResult.success(response);
        } catch (Exception e) {
            return TestResult.error("获取数据测试失败: " + e.getMessage());
        }
    }

    @PostMapping("/recommend")
    @Operation(summary = "测试推荐接口 - SSE流式返回", description = "测试智能问题推荐功能，支持SSE流式响应")
    public SseEmitter testRecommend(@RequestBody TestRecommendRequest request) {
        SseEmitter emitter = new SseEmitter(30000L); // 30秒超时
        
        // 异步执行，避免阻塞
        sqlBotTestService.testRecommendStream(request, emitter);
        
        return emitter;
    }

    @PostMapping("/clean")
    @Operation(summary = "测试清理接口", description = "测试聊天记录清理功能")
    public TestResult<CleanResponse> testClean(@RequestBody TestCleanRequest request) {
        try {
            CleanResponse response = sqlBotTestService.testClean(request);
            return TestResult.success(response);
        } catch (Exception e) {
            return TestResult.error("清理测试失败: " + e.getMessage());
        }
    }
}
