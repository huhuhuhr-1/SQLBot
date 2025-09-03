package com.sqlbot.springboot.starter.model.request;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 获取推荐请求模型
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class GetRecommendRequest {
    /**
     * 聊天记录ID（必填）
     */
    private Integer chat_record_id;
}
