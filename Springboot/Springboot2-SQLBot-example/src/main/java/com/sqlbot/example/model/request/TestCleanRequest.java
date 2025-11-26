package com.sqlbot.example.model.request;

import lombok.Data;
import java.util.List;

/**
 * 测试清理请求模型
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
@Data
public class TestCleanRequest {
    private List<Integer> chatIds;
}
