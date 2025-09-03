package com.sqlbot.example.service;

import com.sqlbot.example.model.request.*;
import com.sqlbot.springboot.starter.SQLBotClient;
import com.sqlbot.springboot.starter.model.response.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;

/**
 * SQLBot测试服务
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
@Service
public class SQLBotTestService {
    
    @Autowired
    private SQLBotClient sqlBotClient;
    
    public GetTokenResponse testLogin(TestLoginRequest request) throws Exception {
        return sqlBotClient.getToken(request.getUsername(), request.getPassword(), request.getCreateChat());
    }
    
    public List<DataSourceResponse> testGetDataSources() throws Exception {
        return sqlBotClient.getDataSourceList();
    }
    
    public ChatResponse testChat(TestChatRequest request) throws Exception {
        return sqlBotClient.chat(request.getDbId(), request.getQuestion(), request.getChatId());
    }
    
    @Async
    public void testChatStream(TestChatRequest request, SseEmitter emitter) {
        try {
            // 发送聊天ID
            emitter.send(SseEmitter.event()
                .name("message")
                .data("{\"type\":\"id\",\"id\":123}"));
            
            // 发送开始消息
            emitter.send(SseEmitter.event()
                .name("message")
                .data("{\"type\":\"start\",\"message\":\"开始处理您的问题...\"}"));
            
            // 模拟SQL生成过程
            emitter.send(SseEmitter.event()
                .name("message")
                .data("{\"type\":\"sql-result\",\"content\":\"正在分析您的问题...\"}"));
            
            emitter.send(SseEmitter.event()
                .name("message")
                .data("{\"type\":\"sql-result\",\"content\":\"生成SQL查询语句...\"}"));
            
            // 模拟最终SQL
            String sql = "SELECT * FROM " + request.getQuestion().toLowerCase().replaceAll("[^a-zA-Z0-9]", "_");
            emitter.send(SseEmitter.event()
                .name("message")
                .data("{\"type\":\"sql\",\"content\":\"" + sql + "\"}"));
            
            // 模拟图表配置生成
            emitter.send(SseEmitter.event()
                .name("message")
                .data("{\"type\":\"chart-result\",\"content\":\"正在生成图表配置...\"}"));
            
            emitter.send(SseEmitter.event()
                .name("message")
                .data("{\"type\":\"chart\",\"content\":\"{\\\"type\\\":\\\"bar\\\",\\\"title\\\":\\\"查询结果\\\"}\"}"));
            
            // 发送结束信号
            emitter.send(SseEmitter.event()
                .name("message")
                .data("{\"type\":\"finish\"}"));
            
            // 完成发送
            emitter.complete();
            
        } catch (Exception e) {
            try {
                emitter.send(SseEmitter.event()
                    .name("message")
                    .data("{\"type\":\"error\",\"message\":\"" + e.getMessage() + "\"}"));
                emitter.complete();
            } catch (Exception ex) {
                emitter.completeWithError(ex);
            }
        }
    }
    
    public GetDataResponse testGetData(TestDataRequest request) throws Exception {
        return sqlBotClient.getData(request.getChatRecordId());
    }
    
    public GetRecommendResponse testRecommend(TestRecommendRequest request) throws Exception {
        return sqlBotClient.getRecommend(request.getChatRecordId());
    }
    
    @Async
    public void testRecommendStream(TestRecommendRequest request, SseEmitter emitter) {
        try {
            // 发送开始消息
            emitter.send(SseEmitter.event()
                .name("message")
                .data("{\"type\":\"start\",\"message\":\"正在生成推荐问题...\"}"));
            
            // 模拟推荐问题生成
            emitter.send(SseEmitter.event()
                .name("message")
                .data("{\"type\":\"recommend\",\"content\":\"查询用户表数据\"}"));
            
            emitter.send(SseEmitter.event()
                .name("message")
                .data("{\"type\":\"recommend\",\"content\":\"分析销售趋势\"}"));
            
            emitter.send(SseEmitter.event()
                .name("message")
                .data("{\"type\":\"recommend\",\"content\":\"统计订单数量\"}"));
            
            // 发送结束信号
            emitter.send(SseEmitter.event()
                .name("message")
                .data("{\"type\":\"finish\"}"));
            
            // 完成发送
            emitter.complete();
            
        } catch (Exception e) {
            try {
                emitter.send(SseEmitter.event()
                    .name("message")
                    .data("{\"type\":\"error\",\"message\":\"" + e.getMessage() + "\"}"));
                emitter.complete();
            } catch (Exception ex) {
                emitter.completeWithError(ex);
            }
        }
    }
    
    public CleanResponse testClean(TestCleanRequest request) throws Exception {
        if (request.getChatIds() != null && !request.getChatIds().isEmpty()) {
            return sqlBotClient.clean(request.getChatIds());
        } else {
            return sqlBotClient.cleanAll();
        }
    }
}
