package com.sqlbot.springboot.starter;

import com.sqlbot.springboot.starter.constant.SQLBotConstants;
import com.sqlbot.springboot.starter.model.request.*;
import com.sqlbot.springboot.starter.model.response.*;
import com.sqlbot.springboot.starter.exception.*;
import com.sqlbot.springboot.starter.util.HttpUtil;
import lombok.Getter;
import lombok.Setter;
import lombok.extern.slf4j.Slf4j;

import java.util.List;
import java.util.function.Consumer;

/**
 * SQLBot客户端类
 * 提供所有SQLBot API接口的调用方法
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Slf4j
public class SQLBotClient {

    private final SQLBotProperties properties;
    private final HttpUtil httpUtil;
    /**
     * -- GETTER --
     * 获取当前令牌
     *
     * @return 当前令牌
     */
    @Getter
    private String currentToken;
    /**
     * -- GETTER --
     * 获取当前聊天会话ID
     * <p>
     * <p>
     * -- SETTER --
     * 设置聊天会话ID
     *
     * @return 当前聊天会话ID
     * @param chatId 聊天会话ID
     */
    @Setter
    @Getter
    private Integer currentChatId;

    /**
     * 构造SQLBot客户端
     *
     * @param properties SQLBot配置属性
     */
    public SQLBotClient(SQLBotProperties properties) {
        this.properties = properties;
        this.httpUtil = new HttpUtil(properties);
        log.info("SQLBotClient 初始化完成，服务器地址: {}", properties.getUrl());
    }

    /**
     * 第一步：获取访问令牌
     *
     * @param username   用户名（必填）
     * @param password   密码（必填）
     * @param createChat 是否创建聊天会话（可选，默认false）
     * @return 获取令牌响应
     * @throws SQLBotException 当认证失败时抛出异常
     */
    public GetTokenResponse getToken(String username, String password, boolean createChat) throws SQLBotException {
        log.debug("正在获取访问令牌，用户名: {}, 创建聊天: {}", username, createChat);

        // 参数验证
        if (username == null || username.trim().isEmpty()) {
            throw new SQLBotClientException("用户名不能为空");
        }
        if (password == null || password.trim().isEmpty()) {
            throw new SQLBotClientException("密码不能为空");
        }

        try {
            GetTokenRequest request = new GetTokenRequest(username, password, createChat);
            GetTokenResponse response = httpUtil.post(
                    properties.getUrl() + SQLBotConstants.ApiPaths.GET_TOKEN, request, GetTokenResponse.class);

            log.info("成功获取访问令牌，过期时间: {}, 聊天ID: {}",
                    response.getExpire(), response.getChatId());

            // 保存令牌和聊天ID
            this.currentToken = response.getAccessToken();
            this.currentChatId = response.getChatId();
            this.httpUtil.setToken(this.currentToken);

            return response;

        } catch (Exception e) {
            log.error("获取访问令牌失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取访问令牌失败: " + e.getMessage(), e);
        }
    }

    /**
     * 第二步：获取数据源列表
     *
     * @return 数据源列表
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public List<DataSourceResponse> getDataSourceList() throws SQLBotException {
        log.debug("正在获取数据源列表");

        ensureAuthenticated();

        try {
            // 使用GetTokenResponse类似的包装结构
            DataSourceListResponse response = httpUtil.get(
                    properties.getUrl() + SQLBotConstants.ApiPaths.GET_DATASOURCE_LIST,
                    DataSourceListResponse.class);

            if (response.isSuccess()) {
                List<DataSourceResponse> dataSources = response.getData();
                log.info("成功获取数据源列表，共 {} 个数据源", dataSources != null ? dataSources.size() : 0);
                return dataSources;
            } else {
                throw new SQLBotApiException("获取数据源列表失败: " + response.getMsg());
            }

        } catch (Exception e) {
            log.error("获取数据源列表失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取数据源列表失败: " + e.getMessage(), e);
        }
    }

    /**
     * 第三步：进行聊天对话
     *
     * @param dbId     数据源ID（必填）
     * @param question 用户问题（必填）
     * @param chatId   聊天会话ID（必填）
     * @return 聊天响应
     * @throws SQLBotException 当聊天失败时抛出异常
     */
    public ChatResponse chat(Integer dbId, String question, Integer chatId) throws SQLBotException {
        log.debug("正在发送聊天请求，数据源ID: {}, 问题: {}, 聊天ID: {}", dbId, question, chatId);

        ensureAuthenticated();

        // 参数验证
        if (dbId == null) {
            throw new SQLBotClientException("数据源ID不能为空");
        }
        if (question == null || question.trim().isEmpty()) {
            throw new SQLBotClientException("问题不能为空");
        }
        if (chatId == null) {
            chatId = this.currentChatId;
            if (chatId == null) {
                throw new SQLBotClientException("聊天会话ID不能为空，请先获取令牌或指定聊天ID");
            }
        }

        try {
            ChatRequest request = new ChatRequest(dbId, question, chatId);
            String fullUrl = properties.getUrl() + SQLBotConstants.ApiPaths.CHAT;
            ChatResponse response = httpUtil.post(fullUrl, request, ChatResponse.class);

            log.info("聊天请求发送成功，聊天记录ID: {}", response.getChatRecordId());

            return response;

        } catch (Exception e) {
            log.error("聊天请求失败: {}", e.getMessage(), e);
            throw new SQLBotException("聊天请求失败: " + e.getMessage(), e);
        }
    }

    /**
     * 第四步：获取聊天记录数据
     *
     * @param chatRecordId 聊天记录ID（必填）
     * @return 获取数据响应
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public GetDataResponse getData(Integer chatRecordId) throws SQLBotException {
        log.debug("正在获取聊天记录数据，聊天记录ID: {}", chatRecordId);

        ensureAuthenticated();

        if (chatRecordId == null) {
            throw new SQLBotClientException("聊天记录ID不能为空");
        }

        try {
            GetDataRequest request = new GetDataRequest(chatRecordId);
            String fullUrl = properties.getUrl() + SQLBotConstants.ApiPaths.GET_DATA;
            GetDataResponse response = httpUtil.post(fullUrl, request, GetDataResponse.class);

            log.info("成功获取聊天记录数据，图表类型: {}", response.getChartType());

            return response;

        } catch (Exception e) {
            log.error("获取聊天记录数据失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取聊天记录数据失败: " + e.getMessage(), e);
        }
    }

    /**
     * 第五步：获取推荐问题
     *
     * @param chatRecordId 聊天记录ID（必填）
     * @return 获取推荐响应
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public GetRecommendResponse getRecommend(Integer chatRecordId) throws SQLBotException {
        log.debug("正在获取推荐问题，聊天记录ID: {}", chatRecordId);

        ensureAuthenticated();

        if (chatRecordId == null) {
            throw new SQLBotClientException("聊天记录ID不能为空");
        }

        try {
            GetRecommendRequest request = new GetRecommendRequest(chatRecordId);
            String fullUrl = properties.getUrl() + SQLBotConstants.ApiPaths.GET_RECOMMEND;
            GetRecommendResponse response = httpUtil.post(fullUrl, request, GetRecommendResponse.class);

            log.info("成功获取推荐问题，共 {} 条推荐",
                    response.getRecommendations() != null ? response.getRecommendations().size() : 0);

            return response;

        } catch (Exception e) {
            log.error("获取推荐问题失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取推荐问题失败: " + e.getMessage(), e);
        }
    }

    /**
     * 第六步：清理指定聊天记录
     *
     * @param chatIds 要清理的聊天记录ID列表
     * @return 清理响应
     * @throws SQLBotException 当清理失败时抛出异常
     */
    public CleanResponse clean(List<Integer> chatIds) throws SQLBotException {
        log.debug("正在清理指定聊天记录，记录数: {}", chatIds != null ? chatIds.size() : 0);

        ensureAuthenticated();

        try {
            // 过滤空ID，避免发送 [null]
            java.util.List<Integer> filtered = new java.util.ArrayList<>();
            if (chatIds != null) {
                for (Integer id : chatIds) {
                    if (id != null) {
                        filtered.add(id);
                    }
                }
            }
            // 若过滤后为空，则改为清理全部
            if (filtered.isEmpty()) {
                log.warn("chatIds为空或仅包含null，回退为清理全部记录");
                return cleanAll();
            }

            CleanRequest request = new CleanRequest(filtered);
            String fullUrl = properties.getUrl() + SQLBotConstants.ApiPaths.CLEAN;
            CleanResponse response = httpUtil.post(fullUrl, request, CleanResponse.class);

            log.info("聊天记录清理完成，成功: {}, 失败: {}, 总计: {}",
                    response.getSuccessCount(), response.getFailedCount(), response.getTotalCount());

            return response;

        } catch (Exception e) {
            log.error("清理聊天记录失败: {}", e.getMessage(), e);
            throw new SQLBotException("清理聊天记录失败: " + e.getMessage(), e);
        }
    }

    /**
     * 第六步：清理所有聊天记录
     *
     * @return 清理响应
     * @throws SQLBotException 当清理失败时抛出异常
     */
    public CleanResponse cleanAll() throws SQLBotException {
        log.debug("正在清理所有聊天记录");

        ensureAuthenticated();

        try {
            String fullUrl = properties.getUrl() + SQLBotConstants.ApiPaths.CLEAN;
            CleanResponse response = httpUtil.post(fullUrl, null, CleanResponse.class);

            log.info("所有聊天记录清理完成，成功: {}, 失败: {}, 总计: {}",
                    response.getSuccessCount(), response.getFailedCount(), response.getTotalCount());

            return response;

        } catch (Exception e) {
            log.error("清理所有聊天记录失败: {}", e.getMessage(), e);
            throw new SQLBotException("清理所有聊天记录失败: " + e.getMessage(), e);
        }
    }

    /**
     * 处理聊天流式响应
     *
     * @param dbId             数据源ID
     * @param question         用户问题
     * @param chatId           聊天会话ID
     * @param dataConsumer     数据消费函数
     * @param errorConsumer    错误处理函数
     * @param completeCallback 完成回调函数
     */
    public void chatStream(Integer dbId, String question, Integer chatId,
                           Consumer<String> dataConsumer,
                           Consumer<Exception> errorConsumer,
                           Runnable completeCallback) {
        log.debug("正在处理聊天流式响应，数据源ID: {}, 问题: {}, 聊天ID: {}", dbId, question, chatId);

        ensureAuthenticated();

        if (dbId == null) {
            errorConsumer.accept(new SQLBotClientException("数据源ID不能为空"));
            return;
        }
        if (question == null || question.trim().isEmpty()) {
            errorConsumer.accept(new SQLBotClientException("问题不能为空"));
            return;
        }
        if (chatId == null) {
            chatId = this.currentChatId;
            if (chatId == null) {
                errorConsumer.accept(new SQLBotClientException("聊天会话ID不能为空"));
                return;
            }
        }

        try {
            // 这里需要实现流式请求的逻辑
            // 由于HttpUtil目前不支持流式请求，这里提供一个基础实现框架
            ChatResponse response = chat(dbId, question, chatId);

            if (dataConsumer != null) {
                dataConsumer.accept(response.getAnswer());
            }

            if (completeCallback != null) {
                completeCallback.run();
            }

        } catch (Exception e) {
            log.error("流式聊天失败: {}", e.getMessage(), e);
            errorConsumer.accept(e);
        }
    }

    /**
     * 处理推荐问题流式响应
     *
     * @param chatRecordId     聊天记录ID
     * @param dataConsumer     数据消费函数
     * @param errorConsumer    错误处理函数
     * @param completeCallback 完成回调函数
     */
    public void recommendStream(Integer chatRecordId,
                                Consumer<String> dataConsumer,
                                Consumer<Exception> errorConsumer,
                                Runnable completeCallback) {
        log.debug("正在处理推荐问题流式响应，聊天记录ID: {}", chatRecordId);

        ensureAuthenticated();

        if (chatRecordId == null) {
            errorConsumer.accept(new SQLBotClientException("聊天记录ID不能为空"));
            return;
        }

        try {
            GetRecommendResponse response = getRecommend(chatRecordId);

            if (response.getRecommendations() != null) {
                for (String recommendation : response.getRecommendations()) {
                    if (dataConsumer != null) {
                        dataConsumer.accept(recommendation);
                    }
                }
            }

            if (completeCallback != null) {
                completeCallback.run();
            }

        } catch (Exception e) {
            log.error("流式推荐失败: {}", e.getMessage(), e);
            errorConsumer.accept(e);
        }
    }

    /**
     * 检查是否已认证
     *
     * @return 是否已认证
     */
    public boolean isAuthenticated() {
        return currentToken != null && !currentToken.trim().isEmpty();
    }

    /**
     * 清除认证信息
     */
    public void clearAuthentication() {
        this.currentToken = null;
        this.currentChatId = null;
        this.httpUtil.setToken(null);
        log.debug("已清除认证信息");
    }

    /**
     * 确保已认证
     *
     * @throws SQLBotAuthenticationException 当未认证时抛出异常
     */
    private void ensureAuthenticated() throws SQLBotAuthenticationException {
        if (!isAuthenticated()) {
            throw new SQLBotAuthenticationException("用户未认证，请先调用getToken方法获取访问令牌");
        }
    }

    /**
     * 添加 PostgreSQL 数据源
     *
     * @param request PostAddPgRequest 请求参数
     * @return CommonDataResponse 响应数据
     * @throws SQLBotException 当请求失败时抛出
     */
    public CommonDataResponse addPg(PostAddPgRequest request) throws SQLBotException {
        log.debug("正在创建 PostgreSQL 数据源，表名: {}", request.getTableName());

        ensureAuthenticated();

        if (request == null) {
            throw new SQLBotClientException("请求对象不能为空");
        }

        try {
            String fullUrl = properties.getUrl() + SQLBotConstants.ApiPaths.ADD_PG;
            CommonDataResponse response = httpUtil.post(fullUrl, request, CommonDataResponse.class);

            log.info("成功添加 PostgreSQL 数据源，返回消息: {}", response.getMsg());

            return response;

        } catch (Exception e) {
            log.error("添加 PostgreSQL 数据源失败: {}", e.getMessage(), e);
            throw new SQLBotException("添加 PostgreSQL 数据源失败: " + e.getMessage(), e);
        }
    }

    /**
     * 根据ID或名称获取数据源
     *
     * @param request 数据源ID或名称请求
     * @return 数据源响应
     * @throws SQLBotException 当请求失败时抛出异常
     */
    public DataSourceResponse getDataSourceByIdOrName(DataSourceIdNameRequest request) throws SQLBotException {
        log.debug("正在根据ID或名称获取数据源，请求: {}", request);

        ensureAuthenticated();

        if (request == null) {
            throw new SQLBotClientException("请求对象不能为空");
        }

        try {
            String fullUrl = properties.getUrl() + SQLBotConstants.ApiPaths.GET_DATASOURCE_BY_ID_OR_NAME;
            DataSourceResponse response = httpUtil.post(fullUrl, request, DataSourceResponse.class);

            log.info("成功获取数据源，数据源ID: {}, 名称: {}", response.getId(), response.getName());

            return response;

        } catch (Exception e) {
            log.error("获取数据源失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取数据源失败: " + e.getMessage(), e);
        }
    }

    /**
     * 通过dbid和sql获取数据
     *
     * @param request 数据源ID和SQL请求
     * @return 数据响应
     * @throws SQLBotException 当请求失败时抛出异常
     */
    public Object getDataByDbIdAndSql(DataSourceRequestWithSql request) throws SQLBotException {
        log.debug("正在通过dbid和sql获取数据，请求: {}", request);

        ensureAuthenticated();

        if (request == null || request.getDbId() == null || request.getSql() == null) {
            throw new SQLBotClientException("数据源ID和SQL不能为空");
        }

        try {
            String fullUrl = properties.getUrl() + SQLBotConstants.ApiPaths.GET_DATA_BY_DB_ID_AND_SQL;
            Object response = httpUtil.post(fullUrl, request, Object.class);

            log.info("成功通过dbid和sql获取数据");

            return response;

        } catch (Exception e) {
            log.error("通过dbid和sql获取数据失败: {}", e.getMessage(), e);
            throw new SQLBotException("通过dbid和sql获取数据失败: " + e.getMessage(), e);
        }
    }

    /**
     * 创建记录并绑定数据源
     *
     * @param request 数据源绑定聊天请求
     * @return 绑定响应
     * @throws SQLBotException 当请求失败时抛出异常
     */
    public Object createRecordAndBindDb(DbBindChat request) throws SQLBotException {
        log.debug("正在创建记录并绑定数据源，请求: {}", request);

        ensureAuthenticated();

        if (request == null || request.getDbId() == null) {
            throw new SQLBotClientException("数据源ID不能为空");
        }

        try {
            String fullUrl = properties.getUrl() + SQLBotConstants.ApiPaths.CREATE_RECORD_AND_BIND_DB;
            Object response = httpUtil.post(fullUrl, request, Object.class);

            log.info("成功创建记录并绑定数据源");

            return response;

        } catch (Exception e) {
            log.error("创建记录并绑定数据源失败: {}", e.getMessage(), e);
            throw new SQLBotException("创建记录并绑定数据源失败: " + e.getMessage(), e);
        }
    }

    /**
     * 分析数据
     *
     * @param request 分析请求
     * @param dataConsumer 数据消费函数（用于处理流式响应）
     * @param errorConsumer 错误处理函数
     * @param completeCallback 完成回调函数
     */
    public void analysisStream(Object request, Consumer<String> dataConsumer,
                               Consumer<Exception> errorConsumer, Runnable completeCallback) {
        log.debug("正在分析数据，请求: {}", request);

        ensureAuthenticated();

        try {
            String fullUrl = properties.getUrl() + SQLBotConstants.ApiPaths.ANALYSIS;
            // 由于分析是流式响应，需要特殊处理
            // 这里使用HTTP流式处理逻辑
            httpUtil.postStream(fullUrl, request, dataConsumer, errorConsumer, completeCallback);

            log.debug("分析请求发送完成");

        } catch (Exception e) {
            log.error("分析数据失败: {}", e.getMessage(), e);
            errorConsumer.accept(new SQLBotException("分析数据失败: " + e.getMessage(), e));
        }
    }

    /**
     * 预测数据
     *
     * @param request 预测请求
     * @param dataConsumer 数据消费函数（用于处理流式响应）
     * @param errorConsumer 错误处理函数
     * @param completeCallback 完成回调函数
     */
    public void predictStream(Object request, Consumer<String> dataConsumer,
                              Consumer<Exception> errorConsumer, Runnable completeCallback) {
        log.debug("正在预测数据，请求: {}", request);

        ensureAuthenticated();

        try {
            String fullUrl = properties.getUrl() + SQLBotConstants.ApiPaths.PREDICT;
            // 由于预测是流式响应，需要特殊处理
            httpUtil.postStream(fullUrl, request, dataConsumer, errorConsumer, completeCallback);

            log.debug("预测请求发送完成");

        } catch (Exception e) {
            log.error("预测数据失败: {}", e.getMessage(), e);
            errorConsumer.accept(new SQLBotException("预测数据失败: " + e.getMessage(), e));
        }
    }

    /**
     * 上传Excel并创建数据源
     *
     * @param filePath Excel文件路径
     * @param params 参数
     * @return 数据源响应
     * @throws SQLBotException 当请求失败时抛出异常
     */
    public DataSourceResponse uploadExcelAndCreateDatasource(String filePath, java.util.Map<String, Object> params) throws SQLBotException {
        log.debug("正在上传Excel并创建数据源，文件路径: {}", filePath);

        ensureAuthenticated();

        if (filePath == null || filePath.trim().isEmpty()) {
            throw new SQLBotClientException("Excel文件路径不能为空");
        }

        try {
            String fullUrl = properties.getUrl() + SQLBotConstants.ApiPaths.UPLOAD_EXCEL_AND_CREATE_DATASOURCE;
            DataSourceResponse response = httpUtil.uploadFile(fullUrl, filePath, params, DataSourceResponse.class);

            log.info("成功上传Excel并创建数据源，数据源ID: {}", response.getId());

            return response;

        } catch (Exception e) {
            log.error("上传Excel并创建数据源失败: {}", e.getMessage(), e);
            throw new SQLBotException("上传Excel并创建数据源失败: " + e.getMessage(), e);
        }
    }

    /**
     * 智能规划执行
     *
     * @param request Plan请求
     * @param dataConsumer 数据消费函数（用于处理流式响应）
     * @param errorConsumer 错误处理函数
     * @param completeCallback 完成回调函数
     */
    public void planStream(OpenPlanQuestion request, Consumer<String> dataConsumer,
                           Consumer<Exception> errorConsumer, Runnable completeCallback) {
        log.debug("正在执行智能规划，请求: {}", request);

        ensureAuthenticated();

        if (request == null || request.getQuestion() == null || request.getQuestion().trim().isEmpty()) {
            errorConsumer.accept(new SQLBotClientException("问题不能为空"));
            return;
        }

        try {
            String fullUrl = properties.getUrl() + SQLBotConstants.ApiPaths.PLAN;
            httpUtil.postStream(fullUrl, request, dataConsumer, errorConsumer, completeCallback);

            log.debug("智能规划请求发送完成");

        } catch (Exception e) {
            log.error("智能规划执行失败: {}", e.getMessage(), e);
            errorConsumer.accept(new SQLBotException("智能规划执行失败: " + e.getMessage(), e));
        }
    }

    /**
     * 删除数据源
     *
     * @param id 数据源ID
     * @return 删除结果
     * @throws SQLBotException 当请求失败时抛出异常
     */
    public Object deleteDatasource(int id) throws SQLBotException {
        log.debug("正在删除数据源，ID: {}", id);

        ensureAuthenticated();

        try {
            String fullUrl = properties.getUrl() + SQLBotConstants.ApiPaths.DELETE_DATASOURCE;
            Object response = httpUtil.post(fullUrl, id, Object.class);

            log.info("成功删除数据源，ID: {}", id);

            return response;

        } catch (Exception e) {
            log.error("删除数据源失败: {}", e.getMessage(), e);
            throw new SQLBotException("删除数据源失败: " + e.getMessage(), e);
        }
    }

    /**
     * 清空Excel
     *
     * @return 清空结果
     * @throws SQLBotException 当请求失败时抛出异常
     */
    public Object deleteExcels() throws SQLBotException {
        log.debug("正在清空Excel");

        ensureAuthenticated();

        try {
            String fullUrl = properties.getUrl() + SQLBotConstants.ApiPaths.DELETE_EXCELS;
            Object response = httpUtil.post(fullUrl, null, Object.class);

            log.info("成功清空Excel");

            return response;

        } catch (Exception e) {
            log.error("清空Excel失败: {}", e.getMessage(), e);
            throw new SQLBotException("清空Excel失败: " + e.getMessage(), e);
        }
    }

}