package com.sqlbot.springboot.starter.api.aimodel;

import com.sqlbot.springboot.starter.SQLBotProperties;
import com.sqlbot.springboot.starter.exception.SQLBotException;
import com.sqlbot.springboot.starter.util.HttpUtil;
import lombok.extern.slf4j.Slf4j;

/**
 * AI模型服务类
 * 提供AI模型管理相关的API接口调用方法
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Slf4j
public class AiModelService {

    private final SQLBotProperties properties;
    private final HttpUtil httpUtil;

    /**
     * 构造AI模型服务
     *
     * @param properties SQLBot配置属性
     */
    public AiModelService(SQLBotProperties properties) {
        this.properties = properties;
        this.httpUtil = new HttpUtil(properties);
        log.info("AiModelService 初始化完成");
    }

    /**
     * 检查LLM状态
     *
     * @param token 认证令牌
     * @param modelInfo 模型信息（需要根据实际模型类构造）
     * @return 检查结果
     * @throws SQLBotException 当检查失败时抛出异常
     */
    public Object checkLLMStatus(String token, Object modelInfo) throws SQLBotException {
        log.debug("正在检查LLM状态");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/system/aimodel/status";
            Object response = httpUtil.post(fullUrl, modelInfo, Object.class);

            log.info("LLM状态检查完成");
            return response;
        } catch (Exception e) {
            log.error("检查LLM状态失败: {}", e.getMessage(), e);
            throw new SQLBotException("检查LLM状态失败: " + e.getMessage(), e);
        }
    }

    /**
     * 获取默认AI模型
     *
     * @param token 认证令牌
     * @return 默认AI模型
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getDefaultModel(String token) throws SQLBotException {
        log.debug("正在获取默认AI模型");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/system/aimodel/default";
            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取默认AI模型");
            return response;
        } catch (Exception e) {
            log.error("获取默认AI模型失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取默认AI模型失败: " + e.getMessage(), e);
        }
    }

    /**
     * 设置默认AI模型
     *
     * @param token 认证令牌
     * @param id 模型ID
     * @return 设置结果
     * @throws SQLBotException 当设置失败时抛出异常
     */
    public Object setDefaultModel(String token, int id) throws SQLBotException {
        log.debug("正在设置默认AI模型，ID: {}", id);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/system/aimodel/default/" + id;
            Object response = httpUtil.put(fullUrl, null, Object.class);

            log.info("成功设置默认AI模型，ID: {}", id);
            return response;
        } catch (Exception e) {
            log.error("设置默认AI模型失败: {}", e.getMessage(), e);
            throw new SQLBotException("设置默认AI模型失败: " + e.getMessage(), e);
        }
    }

    /**
     * 获取AI模型列表
     *
     * @param token 认证令牌
     * @param keyword 搜索关键字（可选）
     * @return AI模型列表
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getModelList(String token, String keyword) throws SQLBotException {
        log.debug("正在获取AI模型列表，关键字: {}", keyword);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/system/aimodel";
            if (keyword != null && !keyword.trim().isEmpty()) {
                fullUrl += "?keyword=" + java.net.URLEncoder.encode(keyword, "UTF-8");
            }
            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取AI模型列表");
            return response;
        } catch (Exception e) {
            log.error("获取AI模型列表失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取AI模型列表失败: " + e.getMessage(), e);
        }
    }

    /**
     * 根据ID获取AI模型
     *
     * @param token 认证令牌
     * @param id 模型ID
     * @return AI模型信息
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getModelById(String token, int id) throws SQLBotException {
        log.debug("正在获取AI模型，ID: {}", id);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/system/aimodel/" + id;
            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取AI模型，ID: {}", id);
            return response;
        } catch (Exception e) {
            log.error("获取AI模型失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取AI模型失败: " + e.getMessage(), e);
        }
    }
}