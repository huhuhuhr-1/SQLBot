package com.sqlbot.springboot.starter.api.mcp;

import com.sqlbot.springboot.starter.SQLBotProperties;
import com.sqlbot.springboot.starter.exception.SQLBotException;
import com.sqlbot.springboot.starter.util.HttpUtil;
import lombok.extern.slf4j.Slf4j;

/**
 * MCP服务类
 * 提供MCP相关的API接口调用方法
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Slf4j
public class McpService {

    private final SQLBotProperties properties;
    private final HttpUtil httpUtil;

    /**
     * 构造MCP服务
     *
     * @param properties SQLBot配置属性
     */
    public McpService(SQLBotProperties properties) {
        this.properties = properties;
        this.httpUtil = new HttpUtil(properties);
        log.info("McpService 初始化完成");
    }

    /**
     * MCP开始
     *
     * @param token 认证令牌
     * @param mcpParams MCP参数
     * @return 开始结果
     * @throws SQLBotException 当操作失败时抛出异常
     */
    public Object mcpStart(String token, Object mcpParams) throws SQLBotException {
        log.debug("正在执行MCP开始操作");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/mcp/mcp_start";
            Object response = httpUtil.post(fullUrl, mcpParams, Object.class);

            log.info("成功执行MCP开始操作");
            return response;
        } catch (Exception e) {
            log.error("MCP开始操作失败: {}", e.getMessage(), e);
            throw new SQLBotException("MCP开始操作失败: " + e.getMessage(), e);
        }
    }

    /**
     * MCP提问
     *
     * @param token 认证令牌
     * @param questionParams 问题参数
     * @return 提问结果
     * @throws SQLBotException 当操作失败时抛出异常
     */
    public Object mcpQuestion(String token, Object questionParams) throws SQLBotException {
        log.debug("正在执行MCP提问");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/mcp/mcp_question";
            Object response = httpUtil.post(fullUrl, questionParams, Object.class);

            log.info("成功执行MCP提问");
            return response;
        } catch (Exception e) {
            log.error("MCP提问失败: {}", e.getMessage(), e);
            throw new SQLBotException("MCP提问失败: " + e.getMessage(), e);
        }
    }

    /**
     * MCP助手
     *
     * @param token 认证令牌
     * @param assistantParams 助手参数
     * @return 助手结果
     * @throws SQLBotException 当操作失败时抛出异常
     */
    public Object mcpAssistant(String token, Object assistantParams) throws SQLBotException {
        log.debug("正在执行MCP助手操作");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/mcp/mcp_assistant";
            Object response = httpUtil.post(fullUrl, assistantParams, Object.class);

            log.info("成功执行MCP助手操作");
            return response;
        } catch (Exception e) {
            log.error("MCP助手操作失败: {}", e.getMessage(), e);
            throw new SQLBotException("MCP助手操作失败: " + e.getMessage(), e);
        }
    }
}