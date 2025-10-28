package com.sqlbot.springboot.starter.api.dashboard;

import com.sqlbot.springboot.starter.SQLBotProperties;
import com.sqlbot.springboot.starter.exception.SQLBotException;
import com.sqlbot.springboot.starter.util.HttpUtil;
import lombok.extern.slf4j.Slf4j;

/**
 * 仪表板服务类
 * 提供仪表板相关的API接口调用方法
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Slf4j
public class DashboardService {

    private final SQLBotProperties properties;
    private final HttpUtil httpUtil;

    /**
     * 构造仪表板服务
     *
     * @param properties SQLBot配置属性
     */
    public DashboardService(SQLBotProperties properties) {
        this.properties = properties;
        this.httpUtil = new HttpUtil(properties);
        log.info("DashboardService 初始化完成");
    }

    /**
     * 列出资源
     *
     * @param token 认证令牌
     * @param params 参数
     * @return 资源列表
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object listResource(String token, Object params) throws SQLBotException {
        log.debug("正在列出资源");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/dashboard/list_resource";
            Object response = httpUtil.post(fullUrl, params, Object.class);

            log.info("成功列出资源");
            return response;
        } catch (Exception e) {
            log.error("列出资源失败: {}", e.getMessage(), e);
            throw new SQLBotException("列出资源失败: " + e.getMessage(), e);
        }
    }

    /**
     * 加载资源
     *
     * @param token 认证令牌
     * @param params 参数
     * @return 加载的资源
     * @throws SQLBotException 当加载失败时抛出异常
     */
    public Object loadResource(String token, Object params) throws SQLBotException {
        log.debug("正在加载资源");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/dashboard/load_resource";
            Object response = httpUtil.post(fullUrl, params, Object.class);

            log.info("成功加载资源");
            return response;
        } catch (Exception e) {
            log.error("加载资源失败: {}", e.getMessage(), e);
            throw new SQLBotException("加载资源失败: " + e.getMessage(), e);
        }
    }

    /**
     * 创建资源
     *
     * @param token 认证令牌
     * @param resourceInfo 资源信息
     * @return 创建的资源
     * @throws SQLBotException 当创建失败时抛出异常
     */
    public Object createResource(String token, Object resourceInfo) throws SQLBotException {
        log.debug("正在创建资源");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/dashboard/create_resource";
            Object response = httpUtil.post(fullUrl, resourceInfo, Object.class);

            log.info("成功创建资源");
            return response;
        } catch (Exception e) {
            log.error("创建资源失败: {}", e.getMessage(), e);
            throw new SQLBotException("创建资源失败: " + e.getMessage(), e);
        }
    }

    /**
     * 更新资源
     *
     * @param token 认证令牌
     * @param resourceInfo 资源信息
     * @return 更新的资源
     * @throws SQLBotException 当更新失败时抛出异常
     */
    public Object updateResource(String token, Object resourceInfo) throws SQLBotException {
        log.debug("正在更新资源");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/dashboard/update_resource";
            Object response = httpUtil.post(fullUrl, resourceInfo, Object.class);

            log.info("成功更新资源");
            return response;
        } catch (Exception e) {
            log.error("更新资源失败: {}", e.getMessage(), e);
            throw new SQLBotException("更新资源失败: " + e.getMessage(), e);
        }
    }

    /**
     * 删除资源
     *
     * @param token 认证令牌
     * @param resourceId 资源ID
     * @return 删除结果
     * @throws SQLBotException 当删除失败时抛出异常
     */
    public Object deleteResource(String token, int resourceId) throws SQLBotException {
        log.debug("正在删除资源，ID: {}", resourceId);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/dashboard/delete_resource/" + resourceId;
            Object response = httpUtil.delete(fullUrl, Object.class);

            log.info("成功删除资源，ID: {}", resourceId);
            return response;
        } catch (Exception e) {
            log.error("删除资源失败: {}", e.getMessage(), e);
            throw new SQLBotException("删除资源失败: " + e.getMessage(), e);
        }
    }

    /**
     * 创建画布
     *
     * @param token 认证令牌
     * @param canvasInfo 画布信息
     * @return 创建的画布
     * @throws SQLBotException 当创建失败时抛出异常
     */
    public Object createCanvas(String token, Object canvasInfo) throws SQLBotException {
        log.debug("正在创建画布");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/dashboard/create_canvas";
            Object response = httpUtil.post(fullUrl, canvasInfo, Object.class);

            log.info("成功创建画布");
            return response;
        } catch (Exception e) {
            log.error("创建画布失败: {}", e.getMessage(), e);
            throw new SQLBotException("创建画布失败: " + e.getMessage(), e);
        }
    }

    /**
     * 更新画布
     *
     * @param token 认证令牌
     * @param canvasInfo 画布信息
     * @return 更新的画布
     * @throws SQLBotException 当更新失败时抛出异常
     */
    public Object updateCanvas(String token, Object canvasInfo) throws SQLBotException {
        log.debug("正在更新画布");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/dashboard/update_canvas";
            Object response = httpUtil.post(fullUrl, canvasInfo, Object.class);

            log.info("成功更新画布");
            return response;
        } catch (Exception e) {
            log.error("更新画布失败: {}", e.getMessage(), e);
            throw new SQLBotException("更新画布失败: " + e.getMessage(), e);
        }
    }

    /**
     * 检查名称
     *
     * @param token 认证令牌
     * @param nameParams 名称参数
     * @return 检查结果
     * @throws SQLBotException 当检查失败时抛出异常
     */
    public Object checkName(String token, Object nameParams) throws SQLBotException {
        log.debug("正在检查名称");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/dashboard/check_name";
            Object response = httpUtil.post(fullUrl, nameParams, Object.class);

            log.info("成功检查名称");
            return response;
        } catch (Exception e) {
            log.error("检查名称失败: {}", e.getMessage(), e);
            throw new SQLBotException("检查名称失败: " + e.getMessage(), e);
        }
    }
}