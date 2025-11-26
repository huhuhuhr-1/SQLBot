package com.sqlbot.springboot.starter.api.datasource;

import com.sqlbot.springboot.starter.SQLBotProperties;
import com.sqlbot.springboot.starter.exception.SQLBotException;
import com.sqlbot.springboot.starter.util.HttpUtil;
import lombok.extern.slf4j.Slf4j;

/**
 * 数据源服务类
 * 提供数据源管理相关的API接口调用方法
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Slf4j
public class DataSourceService {

    private final SQLBotProperties properties;
    private final HttpUtil httpUtil;

    /**
     * 构造数据源服务
     *
     * @param properties SQLBot配置属性
     */
    public DataSourceService(SQLBotProperties properties) {
        this.properties = properties;
        this.httpUtil = new HttpUtil(properties);
        log.info("DataSourceService 初始化完成");
    }

    // 这里将包含数据源相关的API方法
    // 由于之前已经在openapi模块中实现了一些数据源方法，这里可以提供更专门的数据源管理功能
    // 例如：创建、更新、删除数据源等
    
    /**
     * 获取数据源列表
     *
     * @param token 认证令牌
     * @return 数据源列表
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getDataSourceList(String token) throws SQLBotException {
        log.debug("正在获取数据源列表");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/openapi/getDataSourceList"; // 这是OpenAPI接口
            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取数据源列表");
            return response;
        } catch (Exception e) {
            log.error("获取数据源列表失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取数据源列表失败: " + e.getMessage(), e);
        }
    }

    // 注意：具体的实现会根据backend的API结构进行调整
    // 这里只是提供一个基础框架
}