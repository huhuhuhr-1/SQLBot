package com.sqlbot.example.model.request;

import lombok.Data;

/**
 * 测试登录请求模型
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
@Data
public class TestLoginRequest {
    private String username;
    private String password;
    private Boolean createChat = true;
}
