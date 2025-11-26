package com.sqlbot.springboot.starter.api.settings;

import com.sqlbot.springboot.starter.SQLBotProperties;
import com.sqlbot.springboot.starter.exception.SQLBotException;
import com.sqlbot.springboot.starter.util.HttpUtil;
import lombok.extern.slf4j.Slf4j;

/**
 * 设置服务类
 * 提供设置相关的API接口调用方法
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Slf4j
public class SettingsService {

    private final SQLBotProperties properties;
    private final HttpUtil httpUtil;

    /**
     * 构造设置服务
     *
     * @param properties SQLBot配置属性
     */
    public SettingsService(SQLBotProperties properties) {
        this.properties = properties;
        this.httpUtil = new HttpUtil(properties);
        log.info("SettingsService 初始化完成");
    }

    /**
     * 获取术语分页列表
     *
     * @param token 认证令牌
     * @param pageNum 页码
     * @param pageSize 每页大小
     * @return 术语分页列表
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getTerminologyPager(String token, int pageNum, int pageSize) throws SQLBotException {
        log.debug("正在获取术语分页列表，页码: {}, 每页大小: {}", pageNum, pageSize);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/settings/terminology/pager/" + pageNum + "/" + pageSize;
            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取术语分页列表，页码: {}", pageNum);
            return response;
        } catch (Exception e) {
            log.error("获取术语分页列表失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取术语分页列表失败: " + e.getMessage(), e);
        }
    }

    /**
     * 根据ID获取术语
     *
     * @param token 认证令牌
     * @param id 术语ID
     * @return 术语信息
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getTerminologyById(String token, int id) throws SQLBotException {
        log.debug("正在获取术语，ID: {}", id);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/settings/terminology/" + id;
            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取术语，ID: {}", id);
            return response;
        } catch (Exception e) {
            log.error("根据ID获取术语失败: {}", e.getMessage(), e);
            throw new SQLBotException("根据ID获取术语失败: " + e.getMessage(), e);
        }
    }

    /**
     * 添加术语
     *
     * @param token 认证令牌
     * @param terminologyData 术语数据
     * @return 添加结果
     * @throws SQLBotException 当添加失败时抛出异常
     */
    public Object addTerminology(String token, Object terminologyData) throws SQLBotException {
        log.debug("正在添加术语");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/settings/terminology";
            Object response = httpUtil.post(fullUrl, terminologyData, Object.class);

            log.info("成功添加术语");
            return response;
        } catch (Exception e) {
            log.error("添加术语失败: {}", e.getMessage(), e);
            throw new SQLBotException("添加术语失败: " + e.getMessage(), e);
        }
    }

    /**
     * 更新术语
     *
     * @param token 认证令牌
     * @param terminologyData 术语数据
     * @return 更新结果
     * @throws SQLBotException 当更新失败时抛出异常
     */
    public Object updateTerminology(String token, Object terminologyData) throws SQLBotException {
        log.debug("正在更新术语");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/settings/terminology";
            Object response = httpUtil.put(fullUrl, terminologyData, Object.class);

            log.info("成功更新术语");
            return response;
        } catch (Exception e) {
            log.error("更新术语失败: {}", e.getMessage(), e);
            throw new SQLBotException("更新术语失败: " + e.getMessage(), e);
        }
    }

    /**
     * 删除术语
     *
     * @param token 认证令牌
     * @param id 术语ID
     * @return 删除结果
     * @throws SQLBotException 当删除失败时抛出异常
     */
    public Object deleteTerminology(String token, int id) throws SQLBotException {
        log.debug("正在删除术语，ID: {}", id);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/settings/terminology/" + id;
            Object response = httpUtil.delete(fullUrl, Object.class);

            log.info("成功删除术语，ID: {}", id);
            return response;
        } catch (Exception e) {
            log.error("删除术语失败: {}", e.getMessage(), e);
            throw new SQLBotException("删除术语失败: " + e.getMessage(), e);
        }
    }
}