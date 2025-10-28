package com.sqlbot.springboot.starter.api.demo;

import com.sqlbot.springboot.starter.SQLBotProperties;
import com.sqlbot.springboot.starter.exception.SQLBotException;
import com.sqlbot.springboot.starter.util.HttpUtil;
import lombok.extern.slf4j.Slf4j;

/**
 * Demo服务类
 * 提供Demo相关的API接口调用方法
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Slf4j
public class DemoService {

    private final SQLBotProperties properties;
    private final HttpUtil httpUtil;

    /**
     * 构造Demo服务
     *
     * @param properties SQLBot配置属性
     */
    public DemoService(SQLBotProperties properties) {
        this.properties = properties;
        this.httpUtil = new HttpUtil(properties);
        log.info("DemoService 初始化完成");
    }

    /**
     * Demo提问
     *
     * @param token 认证令牌
     * @param askParams 提问参数
     * @return 提问结果
     * @throws SQLBotException 当操作失败时抛出异常
     */
    public Object askDemo(String token, Object askParams) throws SQLBotException {
        log.debug("正在执行Demo提问");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/demo/ask";
            Object response = httpUtil.post(fullUrl, askParams, Object.class);

            log.info("成功执行Demo提问");
            return response;
        } catch (Exception e) {
            log.error("Demo提问失败: {}", e.getMessage(), e);
            throw new SQLBotException("Demo提问失败: " + e.getMessage(), e);
        }
    }

    /**
     * Demo流式提问
     *
     * @param token 认证令牌
     * @param askParams 提问参数
     * @param dataConsumer 数据消费函数
     * @param errorConsumer 错误处理函数
     * @param completeCallback 完成回调函数
     */
    public void askStreamDemo(String token, Object askParams, 
                              java.util.function.Consumer<String> dataConsumer,
                              java.util.function.Consumer<Exception> errorConsumer,
                              Runnable completeCallback) {
        log.debug("正在执行Demo流式提问");

        if (token == null || token.trim().isEmpty()) {
            if (errorConsumer != null) {
                errorConsumer.accept(new SQLBotException("认证令牌不能为空"));
            }
            return;
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/demo/ask-stream";
            httpUtil.postStream(fullUrl, askParams, dataConsumer, errorConsumer, completeCallback);

            log.info("成功发起Demo流式提问");
        } catch (Exception e) {
            log.error("Demo流式提问失败: {}", e.getMessage(), e);
            if (errorConsumer != null) {
                errorConsumer.accept(new SQLBotException("Demo流式提问失败: " + e.getMessage(), e));
            }
        }
    }

    /**
     * Demo智能体
     *
     * @param token 认证令牌
     * @param agentParams 智能体参数
     * @return 智能体结果
     * @throws SQLBotException 当操作失败时抛出异常
     */
    public Object agentDemo(String token, Object agentParams) throws SQLBotException {
        log.debug("正在执行Demo智能体");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/demo/agent";
            Object response = httpUtil.post(fullUrl, agentParams, Object.class);

            log.info("成功执行Demo智能体");
            return response;
        } catch (Exception e) {
            log.error("Demo智能体失败: {}", e.getMessage(), e);
            throw new SQLBotException("Demo智能体失败: " + e.getMessage(), e);
        }
    }
}