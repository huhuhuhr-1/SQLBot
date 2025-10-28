package com.sqlbot.springboot.starter.api.table_relation;

import com.sqlbot.springboot.starter.SQLBotProperties;
import com.sqlbot.springboot.starter.exception.SQLBotException;
import com.sqlbot.springboot.starter.util.HttpUtil;
import lombok.extern.slf4j.Slf4j;

/**
 * 表关系服务类
 * 提供表关系管理相关的API接口调用方法
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Slf4j
public class TableRelationService {

    private final SQLBotProperties properties;
    private final HttpUtil httpUtil;

    /**
     * 构造表关系服务
     *
     * @param properties SQLBot配置属性
     */
    public TableRelationService(SQLBotProperties properties) {
        this.properties = properties;
        this.httpUtil = new HttpUtil(properties);
        log.info("TableRelationService 初始化完成");
    }

    /**
     * 保存表关系
     *
     * @param token 认证令牌
     * @param dsId 数据源ID
     * @param relationData 关系数据
     * @return 保存结果
     * @throws SQLBotException 当保存失败时抛出异常
     */
    public Object saveTableRelation(String token, int dsId, Object relationData) throws SQLBotException {
        log.debug("正在保存表关系，数据源ID: {}", dsId);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/table_relation/save/" + dsId;
            Object response = httpUtil.post(fullUrl, relationData, Object.class);

            log.info("成功保存表关系，数据源ID: {}", dsId);
            return response;
        } catch (Exception e) {
            log.error("保存表关系失败: {}", e.getMessage(), e);
            throw new SQLBotException("保存表关系失败: " + e.getMessage(), e);
        }
    }

    /**
     * 获取表关系
     *
     * @param token 认证令牌
     * @param dsId 数据源ID
     * @return 表关系数据
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getTableRelation(String token, int dsId) throws SQLBotException {
        log.debug("正在获取表关系，数据源ID: {}", dsId);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/table_relation/get/" + dsId;
            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取表关系，数据源ID: {}", dsId);
            return response;
        } catch (Exception e) {
            log.error("获取表关系失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取表关系失败: " + e.getMessage(), e);
        }
    }
}