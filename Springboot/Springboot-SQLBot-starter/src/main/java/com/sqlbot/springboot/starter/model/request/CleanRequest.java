package com.sqlbot.springboot.starter.model.request;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 清理请求模型
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class CleanRequest {
    /**
     * 要清理的聊天记录ID列表（可选，为空时清理所有记录）
     */
    private List<Integer> chat_ids;
}
