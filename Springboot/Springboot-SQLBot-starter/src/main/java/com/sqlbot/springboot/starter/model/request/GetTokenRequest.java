package com.sqlbot.springboot.starter.model.request;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 获取令牌请求模型
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class GetTokenRequest {
    /**
     * 用户名（必填）
     */
    private String username;

    /**
     * 密码（必填）
     */
    private String password;

    /**
     * 是否创建聊天会话（可选，默认false）
     */
    private Boolean create_chat = true;
}