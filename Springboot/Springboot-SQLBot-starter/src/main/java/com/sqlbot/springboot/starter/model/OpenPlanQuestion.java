package com.sqlbot.springboot.starter.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.util.Map;

/**
 * Plan接口问题模型
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Data
@EqualsAndHashCode(callSuper = true)
public class OpenPlanQuestion extends OpenChatQuestion {

    /**
     * 最大执行步骤数
     */
    @JsonProperty("max_steps")
    private Integer maxSteps = 10;

    /**
     * 是否启用重试机制
     */
    @JsonProperty("enable_retry")
    private Boolean enableRetry = true;

    /**
     * 最大重试次数
     */
    @JsonProperty("max_retries")
    private Integer maxRetries = 3;

    /**
     * 执行上下文
     */
    @JsonProperty("context")
    private Map<String, Object> context;
}