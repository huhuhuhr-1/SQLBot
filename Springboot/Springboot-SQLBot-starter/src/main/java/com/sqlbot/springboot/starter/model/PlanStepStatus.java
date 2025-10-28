package com.sqlbot.springboot.starter.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

/**
 * Plan步骤状态模型
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Data
public class PlanStepStatus {

    /**
     * 步骤序号
     */
    @JsonProperty("step")
    private Integer step;

    /**
     * 当前采取的行动
     */
    @JsonProperty("action")
    private String action;

    /**
     * 行动结果/观察
     */
    @JsonProperty("observation")
    private String observation;

    /**
     * 时间戳
     */
    @JsonProperty("timestamp")
    private LocalDateTime timestamp;

    /**
     * 详细信息
     */
    @JsonProperty("details")
    private Map<String, Object> details;
}