package com.sqlbot.springboot.starter.api.user;

import com.sqlbot.springboot.starter.SQLBotProperties;
import com.sqlbot.springboot.starter.exception.SQLBotException;
import com.sqlbot.springboot.starter.util.HttpUtil;
import lombok.extern.slf4j.Slf4j;

/**
 * 用户服务类
 * 提供用户管理相关的API接口调用方法
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Slf4j
public class UserService {

    private final SQLBotProperties properties;
    private final HttpUtil httpUtil;

    /**
     * 构造用户服务
     *
     * @param properties SQLBot配置属性
     */
    public UserService(SQLBotProperties properties) {
        this.properties = properties;
        this.httpUtil = new HttpUtil(properties);
        log.info("UserService 初始化完成");
    }

    /**
     * 获取当前用户信息
     *
     * @param token 认证令牌
     * @return 用户信息
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getUserInfo(String token) throws SQLBotException {
        log.debug("正在获取用户信息");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/user/info";
            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取用户信息");
            return response;
        } catch (Exception e) {
            log.error("获取用户信息失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取用户信息失败: " + e.getMessage(), e);
        }
    }

    /**
     * 获取默认密码
     *
     * @return 默认密码
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public String getDefaultPassword() throws SQLBotException {
        log.debug("正在获取默认密码");

        try {
            String fullUrl = properties.getUrl() + "/user/defaultPwd";
            String response = httpUtil.get(fullUrl, String.class);

            log.info("成功获取默认密码");
            return response;
        } catch (Exception e) {
            log.error("获取默认密码失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取默认密码失败: " + e.getMessage(), e);
        }
    }

    /**
     * 获取用户分页列表
     *
     * @param token 认证令牌
     * @param pageNum 页码
     * @param pageSize 每页大小
     * @param keyword 搜索关键字（可选）
     * @param status 状态（可选）
     * @return 用户分页列表
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getUserPager(String token, int pageNum, int pageSize, String keyword, Integer status) throws SQLBotException {
        log.debug("正在获取用户分页列表，页码: {}, 每页大小: {}, 关键字: {}, 状态: {}", pageNum, pageSize, keyword, status);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            // 构建查询参数
            String queryParams = "?pageNum=" + pageNum + "&pageSize=" + pageSize;
            if (keyword != null && !keyword.trim().isEmpty()) {
                queryParams += "&keyword=" + java.net.URLEncoder.encode(keyword, "UTF-8");
            }
            if (status != null) {
                queryParams += "&status=" + status;
            }

            String fullUrl = properties.getUrl() + "/user/pager/" + pageNum + "/" + pageSize;
            if (keyword != null || status != null) {
                fullUrl += "?";
                boolean hasParam = false;
                if (keyword != null && !keyword.trim().isEmpty()) {
                    fullUrl += "keyword=" + java.net.URLEncoder.encode(keyword, "UTF-8");
                    hasParam = true;
                }
                if (status != null) {
                    if (hasParam) fullUrl += "&";
                    fullUrl += "status=" + status;
                }
            }

            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取用户分页列表");
            return response;
        } catch (Exception e) {
            log.error("获取用户分页列表失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取用户分页列表失败: " + e.getMessage(), e);
        }
    }

    /**
     * 获取用户工作空间选项
     *
     * @param token 认证令牌
     * @return 工作空间选项
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getUserWorkspaceOptions(String token) throws SQLBotException {
        log.debug("正在获取用户工作空间选项");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/user/ws";
            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取用户工作空间选项");
            return response;
        } catch (Exception e) {
            log.error("获取用户工作空间选项失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取用户工作空间选项失败: " + e.getMessage(), e);
        }
    }

    /**
     * 获取单个用户信息
     *
     * @param token 认证令牌
     * @param userId 用户ID
     * @return 用户信息
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getUserById(String token, int userId) throws SQLBotException {
        log.debug("正在获取用户信息，用户ID: {}", userId);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/user/" + userId;
            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取用户信息，ID: {}", userId);
            return response;
        } catch (Exception e) {
            log.error("获取用户信息失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取用户信息失败: " + e.getMessage(), e);
        }
    }
}