package com.sqlbot.example.model.response;

import lombok.Data;
import java.util.ArrayList;
import java.util.List;

/**
 * 业务流程结果响应模型
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
@Data
public class WorkflowResult {
    private boolean success;
    private String message;
    private List<WorkflowStep> steps;
    private long timestamp;
    
    public WorkflowResult() {
        this.steps = new ArrayList<>();
        this.timestamp = System.currentTimeMillis();
    }
    
    public void addStep(String name, String status, String detail) {
        WorkflowStep step = new WorkflowStep();
        step.setName(name);
        step.setStatus(status);
        step.setDetail(detail);
        step.setTimestamp(System.currentTimeMillis());
        this.steps.add(step);
    }
    
    public static WorkflowResult error(String message) {
        WorkflowResult result = new WorkflowResult();
        result.setSuccess(false);
        result.setMessage(message);
        return result;
    }
    
    @Data
    public static class WorkflowStep {
        private String name;
        private String status;
        private String detail;
        private long timestamp;
    }
}
