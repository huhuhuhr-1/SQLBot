package com.sqlbot.example.model.request;

import lombok.Data;

/**
 * 测试聊天请求模型
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
@Data
public class TestChatRequest {
    private Integer dbId;
    private String question;
    private String chatId;  // 改为String类型，因为前端发送的是字符串格式
}
