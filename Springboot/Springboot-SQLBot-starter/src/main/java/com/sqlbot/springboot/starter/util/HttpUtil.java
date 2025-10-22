package com.sqlbot.springboot.starter.util;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sqlbot.springboot.starter.SQLBotProperties;
import com.sqlbot.springboot.starter.exception.SQLBotApiException;
import com.sqlbot.springboot.starter.exception.SQLBotAuthenticationException;
import com.sqlbot.springboot.starter.exception.SQLBotClientException;
import okhttp3.*;
import okhttp3.logging.HttpLoggingInterceptor;
import lombok.extern.slf4j.Slf4j;

import java.io.IOException;
import java.util.concurrent.TimeUnit;

/**
 * HTTP工具类，基于OkHttp实现
 * 提供HTTP请求的封装，支持GET、POST等请求方法
 * 包含重试机制和响应处理
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Slf4j
public class HttpUtil {

    private final SQLBotProperties properties;
    private final OkHttpClient okHttpClient;
    private final ObjectMapper objectMapper;
    private String currentToken;

    /**
     * 构造HttpUtil实例
     *
     * @param properties SQLBot配置属性
     */
    public HttpUtil(SQLBotProperties properties) {
        this.properties = properties;
        this.objectMapper = new ObjectMapper();
        this.okHttpClient = createOkHttpClient();
        log.info("HttpUtil初始化完成 - 服务器地址: {}, 超时配置: 连接={}ms, 读取={}ms, 写入={}ms",
                properties.getUrl(),
                properties.getConnectionTimeout(),
                properties.getReadTimeout(),
                properties.getTimeout());
    }

    /**
     * 创建OkHttp客户端
     *
     * @return 配置好的OkHttpClient实例
     */
    private OkHttpClient createOkHttpClient() {
        OkHttpClient.Builder builder = new OkHttpClient.Builder()
                .connectTimeout(properties.getConnectionTimeout(), TimeUnit.MILLISECONDS)
                .readTimeout(properties.getReadTimeout(), TimeUnit.MILLISECONDS)
                .writeTimeout(properties.getTimeout(), TimeUnit.MILLISECONDS);

        // 添加日志拦截器（仅在开发环境）
        if (Boolean.parseBoolean(System.getProperty("sqlbot.debug", "false"))) {
            HttpLoggingInterceptor loggingInterceptor = new HttpLoggingInterceptor();
            loggingInterceptor.setLevel(HttpLoggingInterceptor.Level.BODY);
            builder.addInterceptor(loggingInterceptor);
            log.debug("已启用HTTP详细日志记录");
        }

        // 添加重试拦截器
        builder.addInterceptor(new RetryInterceptor(properties.getMaxRetries()));
        log.debug("已配置重试拦截器，最大重试次数: {}", properties.getMaxRetries());

        return builder.build();
    }

    /**
     * 执行GET请求 - 使用{@code Class&lt;T&gt;}参数
     *
     * @param <T>          响应类型参数
     * @param url          请求路径
     * @param responseType 响应类型Class对象
     * @return 解析后的响应对象
     * @throws SQLBotApiException 当请求失败时抛出异常
     */
    public <T> T get(String url, Class<T> responseType) {
        log.info("🚀 发起GET请求 - URL: {}, 响应类型: {}", url, responseType.getSimpleName());

        Request.Builder requestBuilder = new Request.Builder()
                .url(url)
                .get();

        // 添加认证头
        if (currentToken != null) {
            requestBuilder.header("Authorization", currentToken);
            requestBuilder.header("X-Sqlbot-Token", currentToken);
            log.debug("已添加认证头 - Token: {}...", currentToken.substring(0, Math.min(20, currentToken.length())));
        } else {
            log.debug("未添加认证头 - 当前无有效Token");
        }

        Request request = requestBuilder.build();
        Response response = null;

        try {
            response = okHttpClient.newCall(request).execute();
            log.info("📥 收到GET响应 - URL: {}, 状态码: {}, 响应大小: {} bytes",
                    url, response.code(), response.body() != null ? response.body().contentLength() : 0);

            T result = handleResponse(response, responseType);
            log.info("✅ GET请求成功 - URL: {}, 响应类型: {}, 结果: {}",
                    url, responseType.getSimpleName(), result != null ? "非空" : "空");
            return result;

        } catch (IOException e) {
            log.error("❌ GET请求失败 - URL: {}, 错误: {}", url, e.getMessage(), e);
            throw new SQLBotApiException("网络请求失败: " + e.getMessage(), e);
        } finally {
            // 确保响应被正确关闭
            if (response != null) {
                try {
                    if (response.body() != null) {
                        response.body().close();
                    }
                    response.close();
                } catch (Exception e) {
                    log.warn("关闭GET响应时发生异常: {}", e.getMessage());
                }
            }
        }
    }

    /**
     * 执行GET请求 - 使用{@code TypeReference&lt;T&gt;}参数
     *
     * @param <T>          响应类型参数
     * @param url          请求路径
     * @param responseType 响应类型引用
     * @return 解析后的响应对象
     * @throws SQLBotApiException 当请求失败时抛出异常
     */
    public <T> T get(String url, TypeReference<T> responseType) {
        log.info("🚀 发起GET请求 - URL: {}, 响应类型: {}", url, responseType.getType());

        Request.Builder requestBuilder = new Request.Builder()
                .url(url)
                .get();

        // 添加认证头
        if (currentToken != null) {
            requestBuilder.header("Authorization", currentToken);
            requestBuilder.header("X-Sqlbot-Token", currentToken);
            log.debug("已添加认证头 - Token: {}...", currentToken.substring(0, Math.min(20, currentToken.length())));
        } else {
            log.debug("未添加认证头 - 当前无有效Token");
        }

        Request request = requestBuilder.build();
        Response response = null;

        try {
            response = okHttpClient.newCall(request).execute();
            log.info("📥 收到GET响应 - URL: {}, 状态码: {}, 响应大小: {} bytes",
                    url, response.code(), response.body() != null ? response.body().contentLength() : 0);

            T result = handleResponse(response, responseType);
            log.info("✅ GET请求成功 - URL: {}, 响应类型: {}, 结果: {}",
                    url, responseType.getType(), result != null ? "非空" : "空");
            return result;

        } catch (IOException e) {
            log.error("❌ GET请求失败 - URL: {}, 错误: {}", url, e.getMessage(), e);
            throw new SQLBotApiException("网络请求失败: " + e.getMessage(), e);
        } finally {
            // 确保响应被正确关闭
            if (response != null) {
                try {
                    if (response.body() != null) {
                        response.body().close();
                    }
                    response.close();
                } catch (Exception e) {
                    log.warn("关闭GET响应时发生异常: {}", e.getMessage());
                }
            }
        }
    }

    /**
     * 执行POST请求
     *
     * @param <T>          响应类型参数
     * @param url          请求路径
     * @param requestBody  请求体对象
     * @param responseType 响应类型Class对象
     * @return 解析后的响应对象
     * @throws SQLBotApiException 当请求失败时抛出异常
     */
    public <T> T post(String url, Object requestBody, Class<T> responseType) {
        log.info("🚀 发起POST请求 - URL: {}, 响应类型: {}", url, responseType.getSimpleName());

        RequestBody body;
        if (requestBody != null) {
            try {
                String json = objectMapper.writeValueAsString(requestBody);
                log.info("📤 请求体 - 类型: {}, 内容: {}",
                        requestBody.getClass().getSimpleName(), json);
                body = RequestBody.create(json, MediaType.get("application/json; charset=utf-8"));
            } catch (Exception e) {
                log.error("❌ 请求参数序列化失败: {}", e.getMessage(), e);
                throw new SQLBotClientException("请求参数序列化失败: " + e.getMessage());
            }
        } else {
            log.debug("请求体为空");
            body = RequestBody.create("{}", MediaType.get("application/json; charset=utf-8"));
        }

        Request.Builder requestBuilder = new Request.Builder()
                .url(url)
                .post(body)
                .header("Content-Type", "application/json");

        // 添加认证头
        if (currentToken != null) {
            requestBuilder.header("Authorization", currentToken);
            requestBuilder.header("X-Sqlbot-Token", currentToken);
            log.debug("已添加认证头 - Token: {}...", currentToken.substring(0, Math.min(20, currentToken.length())));
        } else {
            log.debug("未添加认证头 - 当前无有效Token");
        }

        Request request = requestBuilder.build();
        Response response = null;

        try {
            response = okHttpClient.newCall(request).execute();
            log.info("📥 收到POST响应 - URL: {}, 状态码: {}, 响应大小: {} bytes",
                    url, response.code(), response.body() != null ? response.body().contentLength() : 0);

            T result = handleResponse(response, responseType);
            log.info("✅ POST请求成功 - URL: {}, 响应类型: {}, 结果: {}",
                    url, responseType.getSimpleName(), result != null ? "非空" : "空");
            return result;

        } catch (Exception e) {
            log.error("❌ POST请求失败 - URL: {}, 错误: {}", url, e.getMessage(), e);
            throw new SQLBotApiException("网络请求失败: " + e.getMessage(), e);
        } finally {
            // 确保响应被正确关闭
            if (response != null) {
                try {
                    if (response.body() != null) {
                        response.body().close();
                    }
                    response.close();
                } catch (Exception e) {
                    log.warn("关闭POST响应时发生异常: {}", e.getMessage());
                }
            }
        }
    }

    /**
     * 处理响应 - 使用{@code Class&lt;T&gt;}参数
     * 确保在所有情况下都能正确读取和关闭响应体
     *
     * @param <T>          响应类型参数
     * @param response     HTTP响应对象
     * @param responseType 响应类型Class对象
     * @return 解析后的响应对象
     * @throws IOException 当响应处理失败时抛出异常
     */
    private <T> T handleResponse(Response response, Class<T> responseType) throws IOException {
        String responseBody = "";

        if (!response.isSuccessful()) {
            if (response.body() != null) {
                responseBody = response.body().string();
            }

            switch (response.code()) {
                case 400:
                    throw new SQLBotClientException("请求参数错误: " + responseBody, "BAD_REQUEST");
                case 401:
                    throw new SQLBotAuthenticationException("认证失败: " + responseBody, "UNAUTHORIZED");
                case 403:
                    throw new SQLBotAuthenticationException("权限不足: " + responseBody, "FORBIDDEN");
                case 404:
                    throw new SQLBotApiException("资源不存在: " + responseBody, "NOT_FOUND", 404);
                case 500:
                    throw new SQLBotApiException("服务器内部错误: " + responseBody, "INTERNAL_ERROR", 500);
                default:
                    throw new SQLBotApiException("请求失败 [" + response.code() + "]: " + responseBody, "HTTP_ERROR", response.code());
            }
        }

        try {
            if (response.body() != null) {
                responseBody = response.body().string();
            }
            return objectMapper.readValue(responseBody, responseType);
        } catch (Exception e) {
            throw new SQLBotApiException("响应解析失败: " + e.getMessage(), e);
        }
    }

    /**
     * 处理响应 - 使用{@code TypeReference&lt;T&gt;}参数
     * 确保在所有情况下都能正确读取和关闭响应体
     *
     * @param <T>          响应类型参数
     * @param response     HTTP响应对象
     * @param responseType 响应类型引用
     * @return 解析后的响应对象
     * @throws IOException 当响应处理失败时抛出异常
     */
    private <T> T handleResponse(Response response, TypeReference<T> responseType) throws IOException {
        String responseBody = "";

        if (!response.isSuccessful()) {
            if (response.body() != null) {
                responseBody = response.body().string();
            }

            switch (response.code()) {
                case 400:
                    throw new SQLBotClientException("请求参数错误: " + responseBody, "BAD_REQUEST");
                case 401:
                    throw new SQLBotAuthenticationException("认证失败: " + responseBody, "UNAUTHORIZED");
                case 403:
                    throw new SQLBotAuthenticationException("权限不足: " + responseBody, "FORBIDDEN");
                case 404:
                    throw new SQLBotApiException("资源不存在: " + responseBody, "NOT_FOUND", 404);
                case 500:
                    throw new SQLBotApiException("服务器内部错误: " + responseBody, "INTERNAL_ERROR", 500);
                default:
                    throw new SQLBotApiException("请求失败 [" + response.code() + "]: " + responseBody, "HTTP_ERROR", response.code());
            }
        }

        try {
            // 如果响应体已经被读取（错误情况），直接使用已读取的内容
            if (responseBody.isEmpty() && response.body() != null) {
                responseBody = response.body().string();
            }
            return objectMapper.readValue(responseBody, responseType);
        } catch (Exception e) {
            throw new SQLBotApiException("响应解析失败: " + e.getMessage(), e);
        }
    }

    /**
     * 设置认证令牌
     *
     * @param token 认证令牌，如果为null则清除令牌
     */
    public void setToken(String token) {
        if (token != null && !token.equals(this.currentToken)) {
            log.info("🔑 更新认证令牌 - 旧Token: {}..., 新Token: {}...",
                    this.currentToken != null ? this.currentToken.substring(0, Math.min(20, this.currentToken.length())) : "无",
                    token.substring(0, Math.min(20, token.length())));
            this.currentToken = token;
        } else if (token == null && this.currentToken != null) {
            log.info("🔑 清除认证令牌 - 原Token: {}...",
                    this.currentToken.substring(0, Math.min(20, this.currentToken.length())));
            this.currentToken = null;
        }
    }

    /**
     * 获取当前令牌
     *
     * @return 当前认证令牌，如果没有设置则返回null
     */
    public String getCurrentToken() {
        return currentToken;
    }

    /**
     * 重试拦截器
     * 在请求失败时自动重试，提高请求成功率
     * 注意：重试过程中不关闭响应，让主流程处理响应关闭
     */
    private static class RetryInterceptor implements Interceptor {
        private final int maxRetries;

        /**
         * 构造重试拦截器
         *
         * @param maxRetries 最大重试次数
         */
        public RetryInterceptor(int maxRetries) {
            this.maxRetries = maxRetries;
        }

        @Override
        public Response intercept(Chain chain) throws IOException {
            Request request = chain.request();
            Response response = null;
            IOException lastException = null;

            for (int i = 0; i <= maxRetries; i++) {
                try {
                    if (i > 0) {
                        log.warn("🔄 重试请求 - 第{}次重试, URL: {}", i, request.url());
                    }

                    response = chain.proceed(request);

                    // 如果响应成功，直接返回
                    if (response.isSuccessful()) {
                        if (i > 0) {
                            log.info("✅ 重试成功 - 第{}次重试后成功, URL: {}", i, request.url());
                        }
                        return response;
                    } else {
                        log.warn("⚠️ 请求失败 - 状态码: {}, URL: {}", response.code(), request.url());

                        // 对于非成功的响应，不在这里关闭响应体，让主流程处理
                        // 这样可以避免"closed"异常
                        if (i == maxRetries) {
                            // 最后一次重试失败，返回响应让主流程处理
                            return response;
                        }

                        // 关闭当前响应，准备重试
                        try {
                            if (response.body() != null) {
                                response.body().close();
                            }
                            response.close();
                        } catch (Exception closeException) {
                            log.warn("关闭重试响应时发生异常: {}", closeException.getMessage());
                        }
                    }
                } catch (IOException e) {
                    lastException = e;
                    log.warn("⚠️ 请求异常 - 第{}次尝试, URL: {}, 错误: {}", i + 1, request.url(), e.getMessage());

                    // 确保响应被正确关闭
                    if (response != null) {
                        try {
                            if (response.body() != null) {
                                response.body().close();
                            }
                            response.close();
                        } catch (Exception closeException) {
                            log.warn("关闭响应时发生异常: {}", closeException.getMessage());
                        }
                    }
                }

                // 最后一次重试失败后抛出异常
                if (i == maxRetries) {
                    if (lastException != null) {
                        log.error("❌ 重试次数已达上限 - 最大重试次数: {}, URL: {}, 最终错误: {}",
                                maxRetries, request.url(), lastException.getMessage());
                        throw lastException;
                    }
                    // 如果最后一次重试成功但状态码不成功，返回响应让主流程处理
                    return response;
                }

                // 等待一段时间后重试
                try {
                    long waitTime = 1000 * (i + 1);
                    log.debug("⏳ 等待重试 - 等待时间: {}ms", waitTime);
                    Thread.sleep(waitTime);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    throw new IOException("重试被中断", e);
                }
            }

            return response;
        }
    }
}