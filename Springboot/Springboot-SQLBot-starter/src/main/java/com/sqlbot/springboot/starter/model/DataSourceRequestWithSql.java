package com.sqlbot.springboot.starter.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

/**
 * 数据源和SQL请求模型
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Data
public class DataSourceRequestWithSql {

    /**
     * 数据源ID
     */
    @JsonProperty("db_id")
    private String dbId;

    /**
     * SQL查询语句
     */
    @JsonProperty("sql")
    private String sql;
}