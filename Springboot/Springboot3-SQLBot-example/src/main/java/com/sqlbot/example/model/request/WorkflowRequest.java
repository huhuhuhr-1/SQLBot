package com.sqlbot.example.model.request;

import lombok.Data;

/**
 * 业务流程请求模型
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
@Data
public class WorkflowRequest {
    private String username;
    private String password;
    private String question;
}
