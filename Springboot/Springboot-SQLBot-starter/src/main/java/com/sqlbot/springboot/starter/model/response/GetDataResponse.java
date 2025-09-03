package com.sqlbot.springboot.starter.model.response;

import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

/**
 * 获取数据响应模型（包装结构）
 * 兼容后端新增字段并保持向后兼容
 */
@Data
@NoArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true) // 忽略外层未知字段，增强兼容性
public class GetDataResponse {
    /**
     * 响应状态码，0表示成功
     */
    private Integer code;

    /**
     * 实际数据载荷
     */
    private Payload data;

    /**
     * 响应消息
     */
    private String msg;

    /**
     * 内部载荷，承载原有的业务字段
     */
    @Data
    @NoArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true) // 忽略内部未知字段，避免解析失败
    public static class Payload {
        /** 聊天记录ID（某些接口可能不返回） */
        @JsonProperty("chat_record_id")
        private Integer chatRecordId;
        /** 图表类型（某些接口可能不返回） */
        @JsonProperty("chart_type")
        private String chartType;
        /** 图表标题（某些接口可能不返回） */
        private String title;
        /** 字段名列表（新增字段） */
        private List<String> fields;
        /** 行数据列表 */
        private List<Map<String, Object>> data;
        /** 图表配置（某些接口可能不返回） */
        private Map<String, Object> config;
        /** 响应状态（某些接口可能不返回） */
        private String status;
        /** 创建时间（某些接口可能不返回） */
        @JsonProperty("create_time")
        private String createTime;
        /** 原始SQL（可能为Base64）（新增字段） */
        private String sql;
    }

    // 便捷方法：保持与旧模型的访问方式一致，避免业务代码改动

    /** 是否成功 */
    @JsonIgnore
    public boolean isSuccess() {
        return code != null && code == 0;
    }

    /** 聊天记录ID */
    @JsonIgnore
    public Integer getChatRecordId() {
        return data != null ? data.getChatRecordId() : null;
    }

    /** 图表类型 */
    @JsonIgnore
    public String getChartType() {
        return data != null ? data.getChartType() : null;
    }

    /** 图表标题 */
    @JsonIgnore
    public String getTitle() {
        return data != null ? data.getTitle() : null;
    }

    /** 列字段名列表（新增便捷方法） */
    @JsonIgnore
    public List<String> getFields() {
        return data != null ? data.getFields() : null;
    }

    /** 图表/结果数据（为避免与外层data冲突，命名为getChartData） */
    @JsonIgnore
    public List<Map<String, Object>> getChartData() {
        return data != null ? data.getData() : null;
    }

    /** 图表配置 */
    @JsonIgnore
    public Map<String, Object> getConfig() {
        return data != null ? data.getConfig() : null;
    }

    /** 响应状态 */
    @JsonIgnore
    public String getStatus() {
        return data != null ? data.getStatus() : null;
    }

    /** 创建时间 */
    @JsonIgnore
    public String getCreateTime() {
        return data != null ? data.getCreateTime() : null;
    }

    /** 原始SQL（Base64或明文） */
    @JsonIgnore
    public String getSql() {
        return data != null ? data.getSql() : null;
    }
}
