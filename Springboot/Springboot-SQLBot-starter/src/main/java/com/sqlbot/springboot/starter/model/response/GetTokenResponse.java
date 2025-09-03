package com.sqlbot.springboot.starter.model.response;

import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 获取令牌响应模型
 * 对应API返回的完整响应结构
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
@Data
@NoArgsConstructor
public class GetTokenResponse {
    
    /**
     * 响应状态码，0表示成功
     */
    private Integer code;
    
    /**
     * 响应数据
     */
    private TokenData data;
    
    /**
     * 响应消息
     */
    private String msg;
    
    /**
     * 令牌数据内部类
     */
    @Data
    @NoArgsConstructor
    public static class TokenData {
        /**
         * 完整的访问令牌字符串
         */
        @JsonProperty("access_token")
        private String accessToken;
        
        /**
         * 令牌类型，固定为 "bearer"
         */
        @JsonProperty("token_type")
        private String tokenType;
        
        /**
         * 令牌过期时间，格式为 "YYYY-MM-DD HH:MM:SS"
         */
        private String expire;
        
        /**
         * 聊天会话ID，仅在 create_chat=true 时返回
         */
        @JsonProperty("chat_id")
        private Integer chatId;
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
     * 获取访问令牌（便捷方法）
     *
     * @return 访问令牌
     */
    @JsonIgnore
    public String getAccessToken() {
        return data != null ? data.getAccessToken() : null;
    }
    
    /**
     * 获取令牌类型（便捷方法）
     *
     * @return 令牌类型
     */
    @JsonIgnore
    public String getTokenType() {
        return data != null ? data.getTokenType() : null;
    }
    
    /**
     * 获取过期时间（便捷方法）
     *
     * @return 过期时间
     */
    @JsonIgnore
    public String getExpire() {
        return data != null ? data.getExpire() : null;
    }
    
    /**
     * 获取聊天ID（便捷方法）
     *
     * @return 聊天ID
     */
    @JsonIgnore
    public Integer getChatId() {
        return data != null ? data.getChatId() : null;
    }
}
