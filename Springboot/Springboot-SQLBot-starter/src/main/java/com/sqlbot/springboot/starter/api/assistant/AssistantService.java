package com.sqlbot.springboot.starter.api.assistant;

import com.sqlbot.springboot.starter.SQLBotProperties;
import com.sqlbot.springboot.starter.exception.SQLBotException;
import com.sqlbot.springboot.starter.util.HttpUtil;
import lombok.extern.slf4j.Slf4j;

/**
 * 助手服务类
 * 提供助手管理相关的API接口调用方法
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Slf4j
public class AssistantService {

    private final SQLBotProperties properties;
    private final HttpUtil httpUtil;

    /**
     * 构造助手服务
     *
     * @param properties SQLBot配置属性
     */
    public AssistantService(SQLBotProperties properties) {
        this.properties = properties;
        this.httpUtil = new HttpUtil(properties);
        log.info("AssistantService 初始化完成");
    }

    /**
     * 根据ID获取助手信息
     *
     * @param token 认证令牌
     * @param id 助手ID
     * @return 助手信息
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getAssistantInfo(String token, int id) throws SQLBotException {
        log.debug("正在获取助手信息，ID: {}", id);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/system/assistant/info/" + id;
            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取助手信息，ID: {}", id);
            return response;
        } catch (Exception e) {
            log.error("获取助手信息失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取助手信息失败: " + e.getMessage(), e);
        }
    }

    /**
     * 根据应用ID获取助手信息
     *
     * @param token 认证令牌
     * @param appId 应用ID
     * @return 助手信息
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getAssistantByAppId(String token, String appId) throws SQLBotException {
        log.debug("正在根据应用ID获取助手信息，应用ID: {}", appId);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        if (appId == null || appId.trim().isEmpty()) {
            throw new SQLBotException("应用ID不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/system/assistant/app/" + appId;
            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取助手信息，应用ID: {}", appId);
            return response;
        } catch (Exception e) {
            log.error("根据应用ID获取助手信息失败: {}", e.getMessage(), e);
            throw new SQLBotException("根据应用ID获取助手信息失败: " + e.getMessage(), e);
        }
    }

    /**
     * 获取助手验证器
     *
     * @param token 认证令牌
     * @param id 助手ID
     * @param virtual 虚拟ID（可选）
     * @return 助手验证器
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getAssistantValidator(String token, int id, Integer virtual) throws SQLBotException {
        log.debug("正在获取助手验证器，ID: {}, 虚拟ID: {}", id, virtual);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/system/assistant/validator?id=" + id;
            if (virtual != null) {
                fullUrl += "&virtual=" + virtual;
            }
            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取助手验证器，ID: {}", id);
            return response;
        } catch (Exception e) {
            log.error("获取助手验证器失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取助手验证器失败: " + e.getMessage(), e);
        }
    }

    /**
     * 获取助手列表
     *
     * @param token 认证令牌
     * @return 助手列表
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getAssistantList(String token) throws SQLBotException {
        log.debug("正在获取助手列表");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/system/assistant";
            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取助手列表");
            return response;
        } catch (Exception e) {
            log.error("获取助手列表失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取助手列表失败: " + e.getMessage(), e);
        }
    }

    /**
     * 获取单个助手信息
     *
     * @param token 认证令牌
     * @param id 助手ID
     * @return 助手信息
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getAssistantById(String token, int id) throws SQLBotException {
        log.debug("正在获取单个助手信息，ID: {}", id);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/system/assistant/" + id;
            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取单个助手信息，ID: {}", id);
            return response;
        } catch (Exception e) {
            log.error("获取单个助手信息失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取单个助手信息失败: " + e.getMessage(), e);
        }
    }
}