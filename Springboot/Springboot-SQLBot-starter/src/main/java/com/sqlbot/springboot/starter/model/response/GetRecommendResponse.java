package com.sqlbot.springboot.starter.model.response;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 获取推荐响应模型（支持流式响应）
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class GetRecommendResponse {
    /**
     * 聊天记录ID
     */
    private Integer chatRecordId;
    
    /**
     * 推荐问题列表
     */
    private List<String> recommendations;
    
    /**
     * 响应状态
     */
    private String status;
    
    /**
     * 是否流式响应
     */
    private Boolean isStream = false;
    
    /**
     * 创建时间
     */
    private String createTime;
}
