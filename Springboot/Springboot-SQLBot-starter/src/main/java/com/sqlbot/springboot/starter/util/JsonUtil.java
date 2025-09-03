package com.sqlbot.springboot.starter.util;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.sqlbot.springboot.starter.exception.SQLBotClientException;

import java.text.SimpleDateFormat;
import java.util.List;
import java.util.Map;

/**
 * JSON工具类，提供JSON序列化和反序列化功能
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
public class JsonUtil {
    
    private static final ObjectMapper OBJECT_MAPPER;
    
    static {
        OBJECT_MAPPER = new ObjectMapper();
        
        // 配置Jackson
        OBJECT_MAPPER.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
        OBJECT_MAPPER.configure(SerializationFeature.FAIL_ON_EMPTY_BEANS, false);
        OBJECT_MAPPER.configure(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS, false);
        
        // 设置日期格式
        OBJECT_MAPPER.setDateFormat(new SimpleDateFormat("yyyy-MM-dd HH:mm:ss"));
        
        // 设置属性命名策略（支持下划线转驼峰）
        OBJECT_MAPPER.setPropertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE);
    }
    
    /**
     * 对象转JSON字符串
     * 
     * @param object 要转换的对象
     * @return JSON字符串
     */
    public static String toJson(Object object) {
        if (object == null) {
            return null;
        }
        
        try {
            return OBJECT_MAPPER.writeValueAsString(object);
        } catch (JsonProcessingException e) {
            throw new SQLBotClientException("对象序列化为JSON失败: " + e.getMessage(), e);
        }
    }
    
    /**
     * 对象转格式化的JSON字符串
     * 
     * @param object 要转换的对象
     * @return 格式化的JSON字符串
     */
    public static String toPrettyJson(Object object) {
        if (object == null) {
            return null;
        }
        
        try {
            return OBJECT_MAPPER.writerWithDefaultPrettyPrinter().writeValueAsString(object);
        } catch (JsonProcessingException e) {
            throw new SQLBotClientException("对象序列化为格式化JSON失败: " + e.getMessage(), e);
        }
    }
    
    /**
     * JSON字符串转对象
     * 
     * @param <T> 目标类型参数
     * @param json JSON字符串
     * @param clazz 目标类型
     * @return 转换后的对象
     */
    public static <T> T fromJson(String json, Class<T> clazz) {
        if (json == null || json.trim().isEmpty()) {
            return null;
        }
        
        try {
            return OBJECT_MAPPER.readValue(json, clazz);
        } catch (JsonProcessingException e) {
            throw new SQLBotClientException("JSON反序列化失败: " + e.getMessage(), e);
        }
    }
    
    /**
     * JSON字符串转对象（支持泛型）
     * 
     * @param <T> 目标类型参数
     * @param json JSON字符串
     * @param typeReference 类型引用
     * @return 转换后的对象
     */
    public static <T> T fromJson(String json, TypeReference<T> typeReference) {
        if (json == null || json.trim().isEmpty()) {
            return null;
        }
        
        try {
            return OBJECT_MAPPER.readValue(json, typeReference);
        } catch (JsonProcessingException e) {
            throw new SQLBotClientException("JSON反序列化失败: " + e.getMessage(), e);
        }
    }
    
    /**
     * JSON字符串转List
     * 
     * @param <T> 元素类型参数
     * @param json JSON字符串
     * @param elementClass 元素类型
     * @return List对象
     */
    public static <T> List<T> fromJsonToList(String json, Class<T> elementClass) {
        if (json == null || json.trim().isEmpty()) {
            return null;
        }
        
        try {
            return OBJECT_MAPPER.readValue(json, 
                OBJECT_MAPPER.getTypeFactory().constructCollectionType(List.class, elementClass));
        } catch (JsonProcessingException e) {
            throw new SQLBotClientException("JSON反序列化为List失败: " + e.getMessage(), e);
        }
    }
    
    /**
     * JSON字符串转Map
     * 
     * @param json JSON字符串
     * @return Map对象
     */
    public static Map<String, Object> fromJsonToMap(String json) {
        return fromJson(json, new TypeReference<Map<String, Object>>() {});
    }
    
    /**
     * 对象转Map
     * 
     * @param object 要转换的对象
     * @return Map对象
     */
    public static Map<String, Object> objectToMap(Object object) {
        if (object == null) {
            return null;
        }
        
        return OBJECT_MAPPER.convertValue(object, new TypeReference<Map<String, Object>>() {});
    }
    
    /**
     * Map转对象
     * 
     * @param <T> 目标类型参数
     * @param map Map对象
     * @param clazz 目标类型
     * @return 转换后的对象
     */
    public static <T> T mapToObject(Map<String, Object> map, Class<T> clazz) {
        if (map == null) {
            return null;
        }
        
        return OBJECT_MAPPER.convertValue(map, clazz);
    }
    
    /**
     * 检查字符串是否为有效的JSON
     * 
     * @param json 要检查的字符串
     * @return 是否为有效JSON
     */
    public static boolean isValidJson(String json) {
        if (json == null || json.trim().isEmpty()) {
            return false;
        }
        
        try {
            OBJECT_MAPPER.readTree(json);
            return true;
        } catch (JsonProcessingException e) {
            return false;
        }
    }
    
    /**
     * 深拷贝对象
     * 
     * @param <T> 目标类型参数
     * @param object 要拷贝的对象
     * @param clazz 目标类型
     * @return 拷贝后的对象
     */
    public static <T> T deepCopy(Object object, Class<T> clazz) {
        if (object == null) {
            return null;
        }
        
        String json = toJson(object);
        return fromJson(json, clazz);
    }
    
    /**
     * 获取ObjectMapper实例
     * 
     * @return ObjectMapper实例
     */
    public static ObjectMapper getObjectMapper() {
        return OBJECT_MAPPER;
    }
}
