package com.sqlbot.springboot.starter.model.response;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 聊天响应模型（支持流式响应）
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ChatResponse {
    /**
     * 聊天记录ID
     */
    private Integer chatRecordId;
    
    /**
     * 聊天会话ID
     */
    private Integer chatId;
    
    /**
     * 数据源ID
     */
    private Integer dbId;
    
    /**
     * 用户问题
     */
    private String question;
    
    /**
     * AI回复内容
     */
    private String answer;
    
    /**
     * 响应状态
     */
    private String status;
    
    /**
     * 创建时间
     */
    private String createTime;
    
    /**
     * 是否流式响应
     */
    private Boolean isStream = false;
}
