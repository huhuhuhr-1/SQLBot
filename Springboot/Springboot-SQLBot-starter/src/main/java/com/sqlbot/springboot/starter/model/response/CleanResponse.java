package com.sqlbot.springboot.starter.model.response;

import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 清理响应模型
 * 对应API返回的完整响应结构
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class CleanResponse {
    /**
     * 响应状态码，0表示成功
     */
    private Integer code;
    
    /**
     * 响应数据
     */
    private CleanData data;
    
    /**
     * 响应消息
     */
    private String msg;
    
    /**
     * 清理数据内部类
     */
    @Data
    @NoArgsConstructor
    public static class CleanData {
        /**
         * 操作结果描述
         */
        private String message;
        
        /**
         * 成功清理的记录数量
         */
        @JsonProperty("success_count")
        private Integer successCount;
        
        /**
         * 清理失败的记录数量
         */
        @JsonProperty("failed_count")
        private Integer failedCount;
        
        /**
         * 总记录数量
         */
        @JsonProperty("total_count")
        private Integer totalCount;
        
        /**
         * 失败记录详情列表（仅在失败时返回）
         */
        @JsonProperty("failed_records")
        private List<String> failedRecords;
    }
    
    /**
     * 检查响应是否成功
     *
     * @return 是否成功
     */
    @JsonIgnore
    public boolean isSuccess() {
        return code != null && code == 0;
    }
    
    /**
     * 获取操作结果描述（便捷方法）
     *
     * @return 操作结果描述
     */
    @JsonIgnore
    public String getMessage() {
        return data != null ? data.getMessage() : null;
    }
    
    /**
     * 获取成功清理的记录数量（便捷方法）
     *
     * @return 成功清理的记录数量
     */
    @JsonIgnore
    public Integer getSuccessCount() {
        return data != null ? data.getSuccessCount() : null;
    }
    
    /**
     * 获取清理失败的记录数量（便捷方法）
     *
     * @return 清理失败的记录数量
     */
    @JsonIgnore
    public Integer getFailedCount() {
        return data != null ? data.getFailedCount() : null;
    }
    
    /**
     * 获取总记录数量（便捷方法）
     *
     * @return 总记录数量
     */
    @JsonIgnore
    public Integer getTotalCount() {
        return data != null ? data.getTotalCount() : null;
    }
    
    /**
     * 获取失败记录详情列表（便捷方法）
     *
     * @return 失败记录详情列表
     */
    @JsonIgnore
    public List<String> getFailedRecords() {
        return data != null ? data.getFailedRecords() : null;
    }
}
