package com.sqlbot.example.service;

import com.sqlbot.example.model.request.*;
import com.sqlbot.springboot.starter.SQLBotClient;
import com.sqlbot.springboot.starter.model.response.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import com.sqlbot.springboot.starter.SQLBotProperties;
import com.sqlbot.springboot.starter.constant.SQLBotConstants;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeUnit;

/**
 * SQLBot测试服务
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Service
public class SQLBotTestService {

    private static final Logger log = LoggerFactory.getLogger(SQLBotTestService.class);

    @Autowired
    private SQLBotClient sqlBotClient;

    // 注入Starter的配置，获取后端基础URL
    @Autowired
    private SQLBotProperties properties;

    // 专用于SSE的OkHttp客户端（读超时为0，保证长连接不断）
    private final OkHttpClient sseClient = new OkHttpClient.Builder()
            .readTimeout(0, TimeUnit.MILLISECONDS)
            .build();

    public GetTokenResponse testLogin(TestLoginRequest request) {
        log.info("🧪 开始测试登录功能 - 用户名: {}", request.getUsername());
        try {
            GetTokenResponse response = sqlBotClient.getToken(request.getUsername(), request.getPassword(), request.getCreate_chat());
            log.info("✅ 登录测试成功 - 过期时间: {}, 聊天ID: {}", response.getExpire(), response.getChatId());
            return response;
        } catch (Exception e) {
            log.error("❌ 登录测试失败 - 用户名: {}, 错误: {}", request.getUsername(), e.getMessage(), e);
            throw e;
        }
    }

    public List<DataSourceResponse> testGetDataSources() throws Exception {
        log.info("🧪 开始测试获取数据源列表功能");

        try {
            log.info("📤 调用SQLBot获取数据源列表接口");

            List<DataSourceResponse> response = sqlBotClient.getDataSourceList();

            log.info("✅ 获取数据源列表测试成功 - 数据源数量: {}", response != null ? response.size() : 0);

            if (response != null && !response.isEmpty()) {
                log.debug("📋 数据源详情:");
                for (DataSourceResponse ds : response) {
                    log.debug("  - ID: {}, 名称: {}, 类型: {}, 状态: {}",
                            ds.getId(), ds.getName(), ds.getType(), ds.getStatus());
                }
            }

            return response;

        } catch (Exception e) {
            log.error("❌ 获取数据源列表测试失败 - 错误: {}", e.getMessage(), e);
            throw new Exception("获取数据源列表测试失败: " + e.getMessage(), e);
        }
    }

    public ChatResponse testChat(TestChatRequest request) throws Exception {
        log.info("🧪 开始测试聊天功能 - 数据源ID: {}, 问题: {}", request.getDbId(), request.getQuestion());

        // 处理chatId类型转换
        Integer chatId = null;
        if (request.getChatId() != null && !request.getChatId().trim().isEmpty()) {
            try {
                // 尝试将字符串转换为整数
                chatId = Integer.parseInt(request.getChatId());
                log.info("✅ chatId类型转换成功 - 字符串: '{}' -> 整数: {}", request.getChatId(), chatId);
            } catch (NumberFormatException e) {
                // 如果转换失败，使用默认值或生成一个新的chatId
                chatId = (int) System.currentTimeMillis() % 1000000; // 使用时间戳生成一个6位数ID
                log.warn("⚠️ chatId类型转换失败，使用生成的ID - 原值: '{}', 新ID: {}, 错误: {}",
                        request.getChatId(), chatId, e.getMessage());
            }
        } else {
            log.info("ℹ️ chatId为空，将使用默认值");
        }

        try {
            ChatResponse response = sqlBotClient.chat(request.getDbId(), request.getQuestion(), chatId);
            log.info("✅ 聊天测试成功 - 聊天记录ID: {}, 响应状态: {}",
                    response.getChatRecordId(), response.getStatus());
            return response;
        } catch (Exception e) {
            log.error("❌ 聊天测试失败 - 数据源ID: {}, 问题: {}, 错误: {}",
                    request.getDbId(), request.getQuestion(), e.getMessage(), e);
            throw e;
        }
    }

    @Async
    public void testChatStream(TestChatRequest request, SseEmitter emitter) {
        log.info("🌊 开始处理聊天流式响应 - 数据源ID: {}, 问题: {}", request.getDbId(), request.getQuestion());
        
        // 1) 校验token是否已获取
        String token = sqlBotClient.getCurrentToken();
        if (token == null || token.trim().isEmpty()) {
            log.error("未获取到访问令牌，请先调用登录接口获取token");
            try {
                emitter.send(SseEmitter.event().data("{\"type\":\"error\",\"message\":\"未登录，请先获取token\"}"));
            } catch (Exception ignore) {}
            emitter.complete();
            return;
        }
        
        // 2) 处理chatId（为空时尝试使用当前会话ID）
        Integer chatId = null;
        if (request.getChatId() != null && !request.getChatId().trim().isEmpty()) {
            try {
                chatId = Integer.parseInt(request.getChatId());
            } catch (NumberFormatException e) {
                chatId = sqlBotClient.getCurrentChatId();
                log.warn("chatId解析失败，回退为当前会话ID: {}", chatId);
            }
        } else {
            chatId = sqlBotClient.getCurrentChatId();
        }
        if (chatId == null) {
            log.error("聊天会话ID缺失");
            try {
                emitter.send(SseEmitter.event().data("{\"type\":\"error\",\"message\":\"聊天会话ID为空\"}"));
            } catch (Exception ignore) {}
            emitter.complete();
            return;
        }
        
        // 3) 组装请求体
        ObjectMapper mapper = new ObjectMapper();
        ObjectNode payload = mapper.createObjectNode();
        payload.put("question", request.getQuestion());
        payload.put("chat_id", chatId);
        payload.put("db_id", request.getDbId());
        
        String url = properties.getUrl() + SQLBotConstants.ApiPaths.CHAT;
        log.info("SSE目标URL: {}", url);
        
        RequestBody body = RequestBody.create(
                payload.toString(),
                MediaType.parse("application/json")
        );
        
        Request httpReq = new Request.Builder()
                .url(url)
                .header("X-Sqlbot-Token", token)
                .header("Accept", "text/event-stream")
                .header("Content-Type", "application/json;text/event-stream")
                .post(body)
                .build();
        
        // 4) 发起请求并逐行转发SSE数据
        try (Response response = sseClient.newCall(httpReq).execute()) {
            if (!response.isSuccessful() || response.body() == null) {
                String err = "SSE请求失败，状态码: " + (response != null ? response.code() : -1);
                log.error(err);
                emitter.send(SseEmitter.event().data("{\"type\":\"error\",\"message\":\"" + err + "\"}"));
                emitter.complete();
                return;
            }
            
            // 按行读取SSE（服务器以 data: 开头的行）
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(response.body().byteStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    // 跳过注释/空行
                    if (line.isEmpty() || line.startsWith(":")) {
                        continue;
                    }
                    // 仅转发以 data: 开头的内容，保持与示例一致
                    if (line.startsWith("data:")) {
                        String data = line.substring(5).trim();
                        emitter.send(SseEmitter.event().data(data));
                    } else {
                        // 非标准行也原样透传，便于调试
                        emitter.send(SseEmitter.event().data(line));
                    }
                }
            }
            
            emitter.complete();
            log.info("✅ 聊天流式响应转发完成");
        } catch (Exception e) {
            log.error("❌ 聊天流式响应失败 - 错误: {}", e.getMessage(), e);
            try {
                emitter.send(SseEmitter.event().data("{\"type\":\"error\",\"message\":\"" + e.getMessage() + "\"}"));
                emitter.complete();
            } catch (Exception ex) {
                emitter.completeWithError(ex);
            }
        }
    }

    public GetDataResponse testGetData(TestDataRequest request) throws Exception {
        log.info("📊 开始测试获取数据功能 - 聊天记录ID: {}", request.getChatRecordId());
        try {
            GetDataResponse response = sqlBotClient.getData(request.getChatRecordId());
            log.info("✅ 获取数据测试成功 - 图表类型: {}, 标题: {}", response.getChartType(), response.getTitle());
            return response;
        } catch (Exception e) {
            log.error("❌ 获取数据测试失败 - 聊天记录ID: {}, 错误: {}", request.getChatRecordId(), e.getMessage(), e);
            throw e;
        }
    }

    public GetRecommendResponse testRecommend(TestRecommendRequest request) throws Exception {
        log.info("💡 开始测试推荐功能 - 聊天记录ID: {}", request.getChatRecordId());
        try {
            GetRecommendResponse response = sqlBotClient.getRecommend(request.getChatRecordId());
            log.info("✅ 推荐测试成功 - 推荐数量: {}",
                    response.getRecommendations() != null ? response.getRecommendations().size() : 0);
            return response;
        } catch (Exception e) {
            log.error("❌ 推荐测试失败 - 聊天记录ID: {}, 错误: {}", request.getChatRecordId(), e.getMessage(), e);
            throw e;
        }
    }

    @Async
    public void testRecommendStream(TestRecommendRequest request, SseEmitter emitter) {
        log.info("💡 开始处理推荐流式响应 - 聊天记录ID: {}", request.getChatRecordId());
        
        // 1) 校验token
        String token = sqlBotClient.getCurrentToken();
        if (token == null || token.trim().isEmpty()) {
            log.error("未获取到访问令牌，请先调用登录接口获取token");
            try {
                emitter.send(SseEmitter.event().data("{\"type\":\"error\",\"message\":\"未登录，请先获取token\"}"));
            } catch (Exception ignore) {}
            emitter.complete();
            return;
        }
        
        if (request.getChatRecordId() == null) {
            log.error("聊天记录ID不能为空");
            try {
                emitter.send(SseEmitter.event().data("{\"type\":\"error\",\"message\":\"聊天记录ID不能为空\"}"));
            } catch (Exception ignore) {}
            emitter.complete();
            return;
        }
        
        // 2) 组装请求
        ObjectMapper mapper = new ObjectMapper();
        ObjectNode payload = mapper.createObjectNode();
        payload.put("chat_record_id", request.getChatRecordId());
        
        String url = properties.getUrl() + SQLBotConstants.ApiPaths.GET_RECOMMEND;
        log.info("Recommend SSE目标URL: {}", url);
        
        RequestBody body = RequestBody.create(
                payload.toString(),
                MediaType.parse("application/json")
        );
        
        Request httpReq = new Request.Builder()
                .url(url)
                .header("X-Sqlbot-Token", token)
                .header("Accept", "text/event-stream")
                .header("Content-Type", "application/json;text/event-stream")
                .post(body)
                .build();
        
        // 3) 发起请求并逐行转发
        try (Response response = sseClient.newCall(httpReq).execute()) {
            if (!response.isSuccessful() || response.body() == null) {
                String err = "SSE请求失败，状态码: " + (response != null ? response.code() : -1);
                log.error(err);
                emitter.send(SseEmitter.event().data("{\"type\":\"error\",\"message\":\"" + err + "\"}"));
                emitter.complete();
                return;
            }
            
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(response.body().byteStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    if (line.isEmpty() || line.startsWith(":")) {
                        continue;
                    }
                    if (line.startsWith("data:")) {
                        String data = line.substring(5).trim();
                        emitter.send(SseEmitter.event().data(data));
                    } else {
                        emitter.send(SseEmitter.event().data(line));
                    }
                }
            }
            
            emitter.complete();
            log.info("✅ 推荐流式响应转发完成");
        } catch (Exception e) {
            log.error("❌ 推荐流式响应失败 - 错误: {}", e.getMessage(), e);
            try {
                emitter.send(SseEmitter.event().data("{\"type\":\"error\",\"message\":\"" + e.getMessage() + "\"}"));
                emitter.complete();
            } catch (Exception ex) {
                emitter.completeWithError(ex);
            }
        }
    }

    public CleanResponse testClean(TestCleanRequest request) throws Exception {
        log.info("🧹 开始测试清理功能 - 聊天记录ID数量: {}",
                request.getChatIds() != null ? request.getChatIds().size() : 0);
        try {
            CleanResponse response;
            if (request.getChatIds() != null && !request.getChatIds().isEmpty()) {
                response = sqlBotClient.clean(request.getChatIds());
                log.info("✅ 清理指定聊天记录成功 - 成功: {}, 失败: {}, 总计: {}",
                        response.getSuccessCount(), response.getFailedCount(), response.getTotalCount());
            } else {
                response = sqlBotClient.cleanAll();
                log.info("✅ 清理所有聊天记录成功 - 成功: {}, 失败: {}, 总计: {}",
                        response.getSuccessCount(), response.getFailedCount(), response.getTotalCount());
            }
            return response;
        } catch (Exception e) {
            log.error("❌ 清理测试失败 - 错误: {}", e.getMessage(), e);
            throw e;
        }
    }
}
