package com.sqlbot.springboot.starter.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

/**
 * 数据源绑定聊天请求模型
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Data
public class DbBindChat {

    /**
     * 标题
     */
    @JsonProperty("title")
    private String title;

    /**
     * 数据库标记
     */
    @JsonProperty("db_id")
    private Integer dbId;

    /**
     * 来源标识
     * 0是页面上，mcp是1，小助手是2
     */
    @JsonProperty("origin")
    private Integer origin = 0;
}