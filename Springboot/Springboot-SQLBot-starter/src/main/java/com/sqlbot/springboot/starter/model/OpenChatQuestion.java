package com.sqlbot.springboot.starter.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

/**
 * 聊天问题模型
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Data
public class OpenChatQuestion {

    /**
     * 用户问题内容
     */
    @JsonProperty("question")
    private String question;

    /**
     * 聊天会话标识
     */
    @JsonProperty("chat_id")
    private Integer chatId;

    /**
     * 数据源标识
     */
    @JsonProperty("db_id")
    private Integer dbId;

    /**
     * 自定义sql
     */
    @JsonProperty("my_sql")
    private String mySql;

    /**
     * 自定义提示词
     */
    @JsonProperty("my_promote")
    private String myPromote;

    /**
     * 自定义schema
     */
    @JsonProperty("my_schema")
    private String mySchema;

    /**
     * 是否进行意图检测
     */
    @JsonProperty("intent")
    private Boolean intent = false;

    /**
     * 是否分析
     */
    @JsonProperty("analysis")
    private Boolean analysis = false;

    /**
     * 是否预测
     */
    @JsonProperty("predict")
    private Boolean predict = false;

    /**
     * 是否推荐
     */
    @JsonProperty("recommend")
    private Boolean recommend = false;

    /**
     * 逐条分析
     */
    @JsonProperty("every")
    private Boolean every = false;

    /**
     * 不思考
     */
    @JsonProperty("no_reasoning")
    private Boolean noReasoning = true;

    /**
     * 历史信息打开
     */
    @JsonProperty("history_open")
    private Boolean historyOpen = true;
}