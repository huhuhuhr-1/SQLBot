package com.sqlbot.springboot.starter.util;

import com.sqlbot.springboot.starter.exception.SQLBotApiException;
import okhttp3.Response;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.function.Consumer;

/**
 * 流式响应处理器
 * 用于处理Server-Sent Events (SSE)格式的流式响应
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
public class StreamResponseHandler {
    
    /**
     * 处理流式响应
     * 
     * @param response HTTP响应对象
     * @param dataConsumer 数据消费函数，每接收到一行数据时调用
     * @param errorConsumer 错误处理函数
     * @param completeCallback 完成回调函数
     */
    public static void handleStreamResponse(Response response, 
                                          Consumer<String> dataConsumer,
                                          Consumer<Exception> errorConsumer,
                                          Runnable completeCallback) {
        if (response.body() == null) {
            errorConsumer.accept(new SQLBotApiException("响应体为空"));
            return;
        }
        
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(response.body().byteStream(), StandardCharsets.UTF_8))) {
            
            String line;
            StringBuilder eventData = new StringBuilder();
            
            while ((line = reader.readLine()) != null) {
                // 处理Server-Sent Events格式
                if (line.startsWith("data: ")) {
                    // 提取数据部分
                    String data = line.substring(6);
                    eventData.append(data);
                } else if (line.trim().isEmpty()) {
                    // 空行表示一个事件结束
                    if (eventData.length() > 0) {
                        dataConsumer.accept(eventData.toString());
                        eventData.setLength(0); // 清空缓冲区
                    }
                } else if (line.startsWith("event: ")) {
                    // 事件类型（可以根据需要处理）
                    String eventType = line.substring(7);
                    // 这里可以根据事件类型进行不同的处理
                } else if (line.startsWith("id: ")) {
                    // 事件ID（可以用于重连）
                    String eventId = line.substring(4);
                    // 这里可以保存事件ID用于断线重连
                } else if (line.startsWith("retry: ")) {
                    // 重连间隔（毫秒）
                    String retryTime = line.substring(7);
                    // 这里可以设置重连间隔
                } else {
                    // 普通文本行，直接作为数据处理
                    dataConsumer.accept(line);
                }
            }
            
            // 处理最后的数据（如果没有以空行结束）
            if (eventData.length() > 0) {
                dataConsumer.accept(eventData.toString());
            }
            
            if (completeCallback != null) {
                completeCallback.run();
            }
            
        } catch (IOException e) {
            errorConsumer.accept(new SQLBotApiException("流式响应处理失败: " + e.getMessage(), e));
        }
    }
    
    /**
     * 处理流式响应（简化版本）
     * 
     * @param response HTTP响应对象
     * @param dataConsumer 数据消费函数
     */
    public static void handleStreamResponse(Response response, Consumer<String> dataConsumer) {
        handleStreamResponse(response, dataConsumer, 
            error -> { throw new SQLBotApiException("流式响应处理失败", error); }, 
            null);
    }
    
    /**
     * 同步处理流式响应，将所有数据收集到一个字符串中
     * 
     * @param response HTTP响应对象
     * @return 完整的响应内容
     */
    public static String collectStreamResponse(Response response) {
        StringBuilder result = new StringBuilder();
        
        handleStreamResponse(response, 
            data -> {
                result.append(data);
                result.append("\n");
            },
            error -> { throw new SQLBotApiException("流式响应收集失败", error); },
            null
        );
        
        return result.toString();
    }
    
    /**
     * 异步处理流式响应
     * 
     * @param response HTTP响应对象
     * @param dataConsumer 数据消费函数
     * @param errorConsumer 错误处理函数
     * @param completeCallback 完成回调函数
     */
    public static void handleStreamResponseAsync(Response response, 
                                               Consumer<String> dataConsumer,
                                               Consumer<Exception> errorConsumer,
                                               Runnable completeCallback) {
        new Thread(() -> {
            try {
                handleStreamResponse(response, dataConsumer, errorConsumer, completeCallback);
            } catch (Exception e) {
                if (errorConsumer != null) {
                    errorConsumer.accept(e);
                }
            }
        }).start();
    }
}