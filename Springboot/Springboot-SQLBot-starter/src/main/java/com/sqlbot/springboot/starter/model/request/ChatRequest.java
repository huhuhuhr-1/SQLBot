package com.sqlbot.springboot.starter.model.request;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 聊天请求模型
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ChatRequest {
    /**
     * 数据源ID（必填）
     */
    private Integer db_id;

    /**
     * 用户问题（必填）
     */
    private String question;

    /**
     * 聊天会话ID（必填）
     */
    private Integer chat_id;
}
