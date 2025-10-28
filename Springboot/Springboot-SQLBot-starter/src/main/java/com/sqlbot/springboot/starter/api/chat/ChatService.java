package com.sqlbot.springboot.starter.api.chat;

import com.sqlbot.springboot.starter.SQLBotProperties;
import com.sqlbot.springboot.starter.exception.SQLBotException;
import com.sqlbot.springboot.starter.util.HttpUtil;
import lombok.extern.slf4j.Slf4j;

/**
 * 聊天服务类
 * 提供聊天相关的API接口调用方法
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Slf4j
public class ChatService {

    private final SQLBotProperties properties;
    private final HttpUtil httpUtil;

    /**
     * 构造聊天服务
     *
     * @param properties SQLBot配置属性
     */
    public ChatService(SQLBotProperties properties) {
        this.properties = properties;
        this.httpUtil = new HttpUtil(properties);
        log.info("ChatService 初始化完成");
    }

    /**
     * 获取聊天列表
     *
     * @param token 认证令牌
     * @return 聊天列表
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getChatList(String token) throws SQLBotException {
        log.debug("正在获取聊天列表");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/chat/list";
            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取聊天列表");
            return response;
        } catch (Exception e) {
            log.error("获取聊天列表失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取聊天列表失败: " + e.getMessage(), e);
        }
    }

    /**
     * 根据聊天ID获取聊天信息
     *
     * @param token 认证令牌
     * @param chatId 聊天ID
     * @return 聊天信息
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getChatById(String token, int chatId) throws SQLBotException {
        log.debug("正在获取聊天信息，聊天ID: {}", chatId);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/chat/" + chatId;
            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取聊天信息，ID: {}", chatId);
            return response;
        } catch (Exception e) {
            log.error("获取聊天信息失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取聊天信息失败: " + e.getMessage(), e);
        }
    }

    /**
     * 根据聊天ID获取带数据的聊天信息
     *
     * @param token 认证令牌
     * @param chatId 聊天ID
     * @return 带数据的聊天信息
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getChatWithDate(String token, int chatId) throws SQLBotException {
        log.debug("正在获取带数据的聊天信息，聊天ID: {}", chatId);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/chat/" + chatId + "/with_data";
            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取带数据的聊天信息，ID: {}", chatId);
            return response;
        } catch (Exception e) {
            log.error("获取带数据的聊天信息失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取带数据的聊天信息失败: " + e.getMessage(), e);
        }
    }

    /**
     * 根据聊天记录ID获取数据
     *
     * @param token 认证令牌
     * @param chartRecordId 聊天记录ID
     * @return 聊天数据
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getChatRecordData(String token, int chartRecordId) throws SQLBotException {
        log.debug("正在获取聊天记录数据，记录ID: {}", chartRecordId);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/chat/record/" + chartRecordId + "/data";
            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取聊天记录数据，ID: {}", chartRecordId);
            return response;
        } catch (Exception e) {
            log.error("获取聊天记录数据失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取聊天记录数据失败: " + e.getMessage(), e);
        }
    }

    /**
     * 重命名聊天
     *
     * @param token 认证令牌
     * @param chatId 聊天ID
     * @param newName 新名称
     * @return 重命名结果
     * @throws SQLBotException 当重命名失败时抛出异常
     */
    public Object renameChat(String token, int chatId, String newName) throws SQLBotException {
        log.debug("正在重命名聊天，ID: {}, 新名称: {}", chatId, newName);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            // 构建请求参数
            java.util.Map<String, Object> params = new java.util.HashMap<>();
            params.put("id", chatId);
            params.put("brief", newName);

            String fullUrl = properties.getUrl() + "/chat/rename";
            Object response = httpUtil.post(fullUrl, params, Object.class);

            log.info("成功重命名聊天，ID: {}", chatId);
            return response;
        } catch (Exception e) {
            log.error("重命名聊天失败: {}", e.getMessage(), e);
            throw new SQLBotException("重命名聊天失败: " + e.getMessage(), e);
        }
    }

    /**
     * 删除聊天
     *
     * @param token 认证令牌
     * @param chatId 聊天ID
     * @return 删除结果
     * @throws SQLBotException 当删除失败时抛出异常
     */
    public Object deleteChat(String token, int chatId) throws SQLBotException {
        log.debug("正在删除聊天，ID: {}", chatId);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/chat/" + chatId;
            Object response = httpUtil.delete(fullUrl, Object.class);

            log.info("成功删除聊天，ID: {}", chatId);
            return response;
        } catch (Exception e) {
            log.error("删除聊天失败: {}", e.getMessage(), e);
            throw new SQLBotException("删除聊天失败: " + e.getMessage(), e);
        }
    }

    /**
     * 开始新聊天
     *
     * @param token 认证令牌
     * @param chatParams 聊天参数
     * @return 开始聊天结果
     * @throws SQLBotException 当开始聊天失败时抛出异常
     */
    public Object startNewChat(String token, Object chatParams) throws SQLBotException {
        log.debug("正在开始新聊天");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/chat/start";
            Object response = httpUtil.post(fullUrl, chatParams, Object.class);

            log.info("成功开始新聊天");
            return response;
        } catch (Exception e) {
            log.error("开始新聊天失败: {}", e.getMessage(), e);
            throw new SQLBotException("开始新聊天失败: " + e.getMessage(), e);
        }
    }
}