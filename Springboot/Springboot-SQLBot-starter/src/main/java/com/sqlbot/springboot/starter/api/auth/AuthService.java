package com.sqlbot.springboot.starter.api.auth;

import com.sqlbot.springboot.starter.SQLBotProperties;
import com.sqlbot.springboot.starter.constant.SQLBotConstants;
import com.sqlbot.springboot.starter.exception.SQLBotException;
import com.sqlbot.springboot.starter.util.HttpUtil;
import lombok.extern.slf4j.Slf4j;

/**
 * 认证服务类
 * 提供登录相关的API接口调用方法
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Slf4j
public class AuthService {

    private final SQLBotProperties properties;
    private final HttpUtil httpUtil;

    /**
     * 构造认证服务
     *
     * @param properties SQLBot配置属性
     */
    public AuthService(SQLBotProperties properties) {
        this.properties = properties;
        this.httpUtil = new HttpUtil(properties);
        log.info("AuthService 初始化完成");
    }

    /**
     * 本地登录获取访问令牌
     *
     * @param username 用户名
     * @param password 密码
     * @return 访问令牌
     * @throws SQLBotException 当登录失败时抛出异常
     */
    public String localLogin(String username, String password) throws SQLBotException {
        log.debug("正在执行本地登录，用户名: {}", username);

        try {
            // 准备表单数据（使用OAuth2标准格式）
            java.util.Map<String, String> formData = new java.util.HashMap<>();
            formData.put("username", username);
            formData.put("password", password);
            // grant_type通常为"password"或"client_credentials"，这里根据需要设置
            formData.put("grant_type", "password");

            String fullUrl = properties.getUrl() + "/login/access-token";
            // 登录接口通常不需要认证头
            String response = httpUtil.post(fullUrl, formData, String.class);

            log.info("本地登录成功");
            return response;
        } catch (Exception e) {
            log.error("本地登录失败: {}", e.getMessage(), e);
            throw new SQLBotException("本地登录失败: " + e.getMessage(), e);
        }
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
            // 设置认证令牌
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
}