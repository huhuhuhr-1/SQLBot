package com.sqlbot.springboot.starter;

import com.sqlbot.springboot.starter.model.response.*;
import com.sqlbot.springboot.starter.exception.*;
import lombok.extern.slf4j.Slf4j;

import java.util.List;
import java.util.function.Consumer;

/**
 * SQLBot模板类
 * 提供更高级的抽象接口和链式调用方法
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
@Slf4j
public class SQLBotTemplate {
    
    private final SQLBotClient client;
    private GetTokenResponse lastTokenResponse;
    private List<DataSourceResponse> lastDataSources;
    private ChatResponse lastChatResponse;
    private GetDataResponse lastDataResponse;
    private GetRecommendResponse lastRecommendResponse;
    private CleanResponse lastCleanResponse;
    
    /**
     * 构造SQLBot模板
     *
     * @param client SQLBot客户端实例
     */
    public SQLBotTemplate(SQLBotClient client) {
        this.client = client;
        log.debug("SQLBotTemplate 初始化完成");
    }
    
    /**
     * 用户登录
     * 
     * @param username 用户名
     * @param password 密码
     * @return 当前模板实例，支持链式调用
     * @throws SQLBotException 登录失败时抛出异常
     */
    public SQLBotTemplate login(String username, String password) throws SQLBotException {
        return login(username, password, true);
    }
    
    /**
     * 用户登录
     * 
     * @param username 用户名
     * @param password 密码
     * @param createChat 是否创建聊天会话
     * @return 当前模板实例，支持链式调用
     * @throws SQLBotException 登录失败时抛出异常
     */
    public SQLBotTemplate login(String username, String password, boolean createChat) throws SQLBotException {
        log.debug("模板方法：用户登录，用户名: {}, 创建聊天: {}", username, createChat);
        this.lastTokenResponse = client.getToken(username, password, createChat);
        log.info("登录成功，令牌过期时间: {}", lastTokenResponse.getExpire());
        return this;
    }
    
    /**
     * 选择数据源
     * 
     * @param dbId 数据源ID
     * @return 当前模板实例，支持链式调用
     * @throws SQLBotException 获取数据源失败时抛出异常
     */
    public SQLBotTemplate selectDataSource(Integer dbId) throws SQLBotException {
        log.debug("模板方法：选择数据源，数据源ID: {}", dbId);
        
        // 获取数据源列表
        this.lastDataSources = client.getDataSourceList();
        
        // 验证数据源ID是否存在
        if (dbId != null && lastDataSources != null) {
            boolean found = lastDataSources.stream()
                .anyMatch(ds -> dbId.equals(ds.getId()));
            if (!found) {
                throw new SQLBotClientException("数据源ID " + dbId + " 不存在或无权限访问");
            }
        }
        
        log.info("数据源选择成功，可用数据源数量: {}", lastDataSources.size());
        return this;
    }
    
    /**
     * 提问
     * 
     * @param question 问题内容
     * @return 当前模板实例，支持链式调用
     * @throws SQLBotException 提问失败时抛出异常
     */
    public SQLBotTemplate ask(String question) throws SQLBotException {
        return ask(question, null);
    }
    
    /**
     * 提问
     * 
     * @param question 问题内容
     * @param dbId 数据源ID（可选，为空时使用第一个可用数据源）
     * @return 当前模板实例，支持链式调用
     * @throws SQLBotException 提问失败时抛出异常
     */
    public SQLBotTemplate ask(String question, Integer dbId) throws SQLBotException {
        log.debug("模板方法：提问，问题: {}, 数据源ID: {}", question, dbId);
        
        // 如果没有指定数据源ID，使用第一个可用的数据源
        if (dbId == null && lastDataSources != null && !lastDataSources.isEmpty()) {
            dbId = lastDataSources.get(0).getId();
            log.debug("使用第一个可用数据源，ID: {}", dbId);
        }
        
        if (dbId == null) {
            throw new SQLBotClientException("未指定数据源ID且没有可用的数据源");
        }
        
        this.lastChatResponse = client.chat(dbId, question, client.getCurrentChatId());
        log.info("提问成功，聊天记录ID: {}", lastChatResponse.getChatRecordId());
        return this;
    }
    
    /**
     * 获取数据
     * 
     * @return 当前模板实例，支持链式调用
     * @throws SQLBotException 获取数据失败时抛出异常
     */
    public SQLBotTemplate getData() throws SQLBotException {
        log.debug("模板方法：获取数据");
        
        if (lastChatResponse == null || lastChatResponse.getChatRecordId() == null) {
            throw new SQLBotClientException("没有可用的聊天记录ID，请先调用ask方法");
        }
        
        this.lastDataResponse = client.getData(lastChatResponse.getChatRecordId());
        log.info("获取数据成功，图表类型: {}", lastDataResponse.getChartType());
        return this;
    }
    
    /**
     * 获取推荐问题
     * 
     * @return 当前模板实例，支持链式调用
     * @throws SQLBotException 获取推荐失败时抛出异常
     */
    public SQLBotTemplate getRecommendations() throws SQLBotException {
        log.debug("模板方法：获取推荐问题");
        
        if (lastChatResponse == null || lastChatResponse.getChatRecordId() == null) {
            throw new SQLBotClientException("没有可用的聊天记录ID，请先调用ask方法");
        }
        
        this.lastRecommendResponse = client.getRecommend(lastChatResponse.getChatRecordId());
        log.info("获取推荐问题成功，推荐数量: {}", 
            lastRecommendResponse.getRecommendations() != null ? 
            lastRecommendResponse.getRecommendations().size() : 0);
        return this;
    }
    
    /**
     * 清理聊天记录
     * 
     * @return 当前模板实例，支持链式调用
     * @throws SQLBotException 清理失败时抛出异常
     */
    public SQLBotTemplate cleanup() throws SQLBotException {
        return cleanup(null);
    }
    
    /**
     * 清理指定聊天记录
     * 
     * @param chatIds 要清理的聊天记录ID列表（为空时清理所有）
     * @return 当前模板实例，支持链式调用
     * @throws SQLBotException 清理失败时抛出异常
     */
    public SQLBotTemplate cleanup(List<Integer> chatIds) throws SQLBotException {
        log.debug("模板方法：清理聊天记录，记录数: {}", chatIds != null ? chatIds.size() : "全部");
        
        if (chatIds != null && !chatIds.isEmpty()) {
            this.lastCleanResponse = client.clean(chatIds);
        } else {
            this.lastCleanResponse = client.cleanAll();
        }
        
        log.info("清理完成，成功: {}, 失败: {}", 
            lastCleanResponse.getSuccessCount(), lastCleanResponse.getFailedCount());
        return this;
    }
    
    /**
     * 流式聊天
     * 
     * @param question 问题内容
     * @param dataConsumer 数据消费函数
     * @return 当前模板实例，支持链式调用
     */
    public SQLBotTemplate askStream(String question, Consumer<String> dataConsumer) {
        return askStream(question, null, dataConsumer, null, null);
    }
    
    /**
     * 流式聊天
     * 
     * @param question 问题内容
     * @param dbId 数据源ID
     * @param dataConsumer 数据消费函数
     * @param errorConsumer 错误处理函数
     * @param completeCallback 完成回调函数
     * @return 当前模板实例，支持链式调用
     */
    public SQLBotTemplate askStream(String question, Integer dbId,
                                   Consumer<String> dataConsumer,
                                   Consumer<Exception> errorConsumer,
                                   Runnable completeCallback) {
        log.debug("模板方法：流式提问，问题: {}, 数据源ID: {}", question, dbId);
        
        // 如果没有指定数据源ID，使用第一个可用的数据源
        if (dbId == null && lastDataSources != null && !lastDataSources.isEmpty()) {
            dbId = lastDataSources.get(0).getId();
        }
        
        client.chatStream(dbId, question, client.getCurrentChatId(),
            dataConsumer, 
            errorConsumer != null ? errorConsumer : (error -> log.error("流式聊天错误", error)),
            completeCallback);
        
        return this;
    }
    
    /**
     * 流式获取推荐问题
     * 
     * @param dataConsumer 数据消费函数
     * @return 当前模板实例，支持链式调用
     */
    public SQLBotTemplate getRecommendationsStream(Consumer<String> dataConsumer) {
        return getRecommendationsStream(dataConsumer, null, null);
    }
    
    /**
     * 流式获取推荐问题
     * 
     * @param dataConsumer 数据消费函数
     * @param errorConsumer 错误处理函数
     * @param completeCallback 完成回调函数
     * @return 当前模板实例，支持链式调用
     */
    public SQLBotTemplate getRecommendationsStream(Consumer<String> dataConsumer,
                                                  Consumer<Exception> errorConsumer,
                                                  Runnable completeCallback) {
        log.debug("模板方法：流式获取推荐问题");
        
        if (lastChatResponse == null || lastChatResponse.getChatRecordId() == null) {
            Exception error = new SQLBotClientException("没有可用的聊天记录ID，请先调用ask方法");
            if (errorConsumer != null) {
                errorConsumer.accept(error);
            } else {
                log.error("流式获取推荐问题错误", error);
            }
            return this;
        }
        
        client.recommendStream(lastChatResponse.getChatRecordId(),
            dataConsumer,
            errorConsumer != null ? errorConsumer : (error -> log.error("流式推荐错误", error)),
            completeCallback);
        
        return this;
    }
    
    /**
     * 执行完成（用于链式调用的结束）
     * 
     * @return 执行结果摘要
     */
    public String execute() {
        StringBuilder result = new StringBuilder("SQLBot执行完成:\n");
        
        if (lastTokenResponse != null) {
            result.append("- 登录成功，令牌过期时间: ").append(lastTokenResponse.getExpire()).append("\n");
        }
        
        if (lastDataSources != null) {
            result.append("- 数据源列表获取成功，共 ").append(lastDataSources.size()).append(" 个数据源\n");
        }
        
        if (lastChatResponse != null) {
            result.append("- 聊天完成，聊天记录ID: ").append(lastChatResponse.getChatRecordId()).append("\n");
        }
        
        if (lastDataResponse != null) {
            result.append("- 数据获取成功，图表类型: ").append(lastDataResponse.getChartType()).append("\n");
        }
        
        if (lastRecommendResponse != null) {
            result.append("- 推荐问题获取成功，共 ")
                .append(lastRecommendResponse.getRecommendations() != null ? 
                    lastRecommendResponse.getRecommendations().size() : 0)
                .append(" 条推荐\n");
        }
        
        if (lastCleanResponse != null) {
            result.append("- 清理完成，成功: ").append(lastCleanResponse.getSuccessCount())
                .append(", 失败: ").append(lastCleanResponse.getFailedCount()).append("\n");
        }
        
        String resultStr = result.toString();
        log.info("执行摘要: {}", resultStr);
        return resultStr;
    }
    
    // Getter方法用于获取最后的响应结果
    
    /**
     * 获取最后一次令牌响应
     *
     * @return 最后一次令牌响应
     */
    public GetTokenResponse getLastTokenResponse() {
        return lastTokenResponse;
    }

    /**
     * 获取最后一次数据源列表
     *
     * @return 最后一次数据源列表
     */
    public List<DataSourceResponse> getLastDataSources() {
        return lastDataSources;
    }

    /**
     * 获取最后一次聊天响应
     *
     * @return 最后一次聊天响应
     */
    public ChatResponse getLastChatResponse() {
        return lastChatResponse;
    }

    /**
     * 获取最后一次数据响应
     *
     * @return 最后一次数据响应
     */
    public GetDataResponse getLastDataResponse() {
        return lastDataResponse;
    }

    /**
     * 获取最后一次推荐响应
     *
     * @return 最后一次推荐响应
     */
    public GetRecommendResponse getLastRecommendResponse() {
        return lastRecommendResponse;
    }

    /**
     * 获取最后一次清理响应
     *
     * @return 最后一次清理响应
     */
    public CleanResponse getLastCleanResponse() {
        return lastCleanResponse;
    }
    
    /**
     * 获取底层客户端
     * 
     * @return SQLBotClient实例
     */
    public SQLBotClient getClient() {
        return client;
    }
    
    /**
     * 清除所有缓存的响应结果
     */
    public void clearCache() {
        this.lastTokenResponse = null;
        this.lastDataSources = null;
        this.lastChatResponse = null;
        this.lastDataResponse = null;
        this.lastRecommendResponse = null;
        this.lastCleanResponse = null;
        log.debug("已清除所有缓存的响应结果");
    }
}