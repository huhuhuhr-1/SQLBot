package com.sqlbot.springboot.starter.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.List;
import java.util.Map;

/**
 * Plan响应模型
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Data
public class PlanResponse {

    /**
     * 计划ID
     */
    @JsonProperty("plan_id")
    private String planId;

    /**
     * 状态：planning, executing, completed, failed
     */
    @JsonProperty("status")
    private String status;

    /**
     * 执行步骤列表
     */
    @JsonProperty("steps")
    private List<PlanStepStatus> steps;

    /**
     * 结果数据
     */
    @JsonProperty("result")
    private Map<String, Object> result;

    /**
     * 错误信息
     */
    @JsonProperty("error")
    private String error;
}