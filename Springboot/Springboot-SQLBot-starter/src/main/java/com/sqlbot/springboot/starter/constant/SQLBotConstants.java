package com.sqlbot.springboot.starter.constant;

/**
 * SQLBot常量定义
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
public final class SQLBotConstants {

    /**
     * API路径常量
     */
    public static final class ApiPaths {
        /**
         * 获取令牌接口路径
         */
        public static final String GET_TOKEN = "/openapi/getToken";

        /**
         * 获取数据源列表接口路径
         */
        public static final String GET_DATASOURCE_LIST = "/openapi/getDataSourceList";

        /**
         * 聊天接口路径
         */
        public static final String CHAT = "/openapi/chat";

        /**
         * 获取数据接口路径
         */
        public static final String GET_DATA = "/openapi/getData";

        /**
         * 获取推荐接口路径
         */
        public static final String GET_RECOMMEND = "/openapi/getRecommend";

        /**
         * 清理接口路径
         */
        public static final String CLEAN = "/openapi/deleteChats";

        /**
         * 新增pg
         */
        public static final String ADD_PG = "/openapi/addPg";

        /**
         * 根据ID或名称获取数据源接口路径
         */
        public static final String GET_DATASOURCE_BY_ID_OR_NAME = "/openapi/getDataSourceByIdOrName";

        /**
         * 通过dbid和sql获取数据接口路径
         */
        public static final String GET_DATA_BY_DB_ID_AND_SQL = "/openapi/getDataByDbIdAndSql";

        /**
         * 创建记录并绑定数据源接口路径
         */
        public static final String CREATE_RECORD_AND_BIND_DB = "/openapi/createRecordAndBindDb";

        /**
         * 分析接口路径
         */
        public static final String ANALYSIS = "/openapi/analysis";

        /**
         * 预测接口路径
         */
        public static final String PREDICT = "/openapi/predict";

        /**
         * 上传Excel并创建数据源接口路径
         */
        public static final String UPLOAD_EXCEL_AND_CREATE_DATASOURCE = "/openapi/uploadExcelAndCreateDatasource";

        /**
         * 智能规划执行接口路径
         */
        public static final String PLAN = "/openapi/plan";

        /**
         * 删除数据源接口路径
         */
        public static final String DELETE_DATASOURCE = "/openapi/deleteDatasource";

        /**
         * 清空excel接口路径
         */
        public static final String DELETE_EXCELS = "/openapi/deleteExcels";

        private ApiPaths() {
        }
    }

    /**
     * HTTP头常量
     */
    public static final class Headers {
        /**
         * 授权头
         */
        public static final String AUTHORIZATION = "Authorization";

        /**
         * SQLBot令牌头
         */
        public static final String X_SQLBOT_TOKEN = "X-Sqlbot-Token";

        /**
         * 内容类型头
         */
        public static final String CONTENT_TYPE = "Content-Type";

        /**
         * JSON内容类型
         */
        public static final String APPLICATION_JSON = "application/json";

        /**
         * 事件流内容类型
         */
        public static final String TEXT_EVENT_STREAM = "text/event-stream";

        private Headers() {
        }
    }

    /**
     * 错误码常量
     */
    public static final class ErrorCodes {
        /**
         * 未知错误
         */
        public static final String UNKNOWN_ERROR = "UNKNOWN_ERROR";

        /**
         * 客户端错误
         */
        public static final String CLIENT_ERROR = "CLIENT_ERROR";

        /**
         * 认证错误
         */
        public static final String AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR";

        /**
         * API错误
         */
        public static final String API_ERROR = "API_ERROR";

        /**
         * 网络错误
         */
        public static final String NETWORK_ERROR = "NETWORK_ERROR";

        /**
         * 参数错误
         */
        public static final String BAD_REQUEST = "BAD_REQUEST";

        /**
         * 未授权
         */
        public static final String UNAUTHORIZED = "UNAUTHORIZED";

        /**
         * 禁止访问
         */
        public static final String FORBIDDEN = "FORBIDDEN";

        /**
         * 资源不存在
         */
        public static final String NOT_FOUND = "NOT_FOUND";

        /**
         * 服务器内部错误
         */
        public static final String INTERNAL_ERROR = "INTERNAL_ERROR";

        /**
         * HTTP错误
         */
        public static final String HTTP_ERROR = "HTTP_ERROR";

        private ErrorCodes() {
        }
    }

    /**
     * 响应状态常量
     */
    public static final class ResponseStatus {
        /**
         * 成功
         */
        public static final String SUCCESS = "success";

        /**
         * 失败
         */
        public static final String FAILED = "failed";

        /**
         * 处理中
         */
        public static final String PROCESSING = "processing";

        /**
         * 完成
         */
        public static final String COMPLETED = "completed";

        private ResponseStatus() {
        }
    }

    /**
     * 配置前缀
     */
    public static final String CONFIG_PREFIX = "sqlbot";

    /**
     * 默认配置值
     */
    public static final class DefaultValues {
        /**
         * 默认超时时间（毫秒）
         */
        public static final int DEFAULT_TIMEOUT = 30000;

        /**
         * 默认连接超时时间（毫秒）
         */
        public static final int DEFAULT_CONNECTION_TIMEOUT = 10000;

        /**
         * 默认读取超时时间（毫秒）
         */
        public static final int DEFAULT_READ_TIMEOUT = 30000;

        /**
         * 默认最大重试次数
         */
        public static final int DEFAULT_MAX_RETRIES = 3;

        /**
         * 默认服务器地址
         */
        public static final String DEFAULT_URL = "http://localhost:8000";

        /**
         * 默认启用状态
         */
        public static final boolean DEFAULT_ENABLED = true;

        private DefaultValues() {
        }
    }

    private SQLBotConstants() {
        // 防止实例化
    }
}

