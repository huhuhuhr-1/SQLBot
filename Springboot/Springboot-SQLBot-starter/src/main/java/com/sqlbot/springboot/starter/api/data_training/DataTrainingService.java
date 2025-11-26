package com.sqlbot.springboot.starter.api.data_training;

import com.sqlbot.springboot.starter.SQLBotProperties;
import com.sqlbot.springboot.starter.exception.SQLBotException;
import com.sqlbot.springboot.starter.util.HttpUtil;
import lombok.extern.slf4j.Slf4j;

/**
 * 数据训练服务类
 * 提供数据训练管理相关的API接口调用方法
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Slf4j
public class DataTrainingService {

    private final SQLBotProperties properties;
    private final HttpUtil httpUtil;

    /**
     * 构造数据训练服务
     *
     * @param properties SQLBot配置属性
     */
    public DataTrainingService(SQLBotProperties properties) {
        this.properties = properties;
        this.httpUtil = new HttpUtil(properties);
        log.info("DataTrainingService 初始化完成");
    }

    /**
     * 获取数据训练分页列表
     *
     * @param token 认证令牌
     * @param currentPage 当前页码
     * @param pageSize 每页大小
     * @param question 搜索问题（可选）
     * @return 数据训练分页列表
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getDataTrainingPage(String token, int currentPage, int pageSize, String question) throws SQLBotException {
        log.debug("正在获取数据训练分页列表，当前页: {}, 每页大小: {}, 搜索问题: {}", currentPage, pageSize, question);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/system/data-training/page/" + currentPage + "/" + pageSize;
            if (question != null && !question.trim().isEmpty()) {
                fullUrl += "?question=" + java.net.URLEncoder.encode(question, "UTF-8");
            }
            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取数据训练分页列表，当前页: {}", currentPage);
            return response;
        } catch (Exception e) {
            log.error("获取数据训练分页列表失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取数据训练分页列表失败: " + e.getMessage(), e);
        }
    }

    /**
     * 创建或更新数据训练
     *
     * @param token 认证令牌
     * @param trainingInfo 数据训练信息
     * @return 操作结果
     * @throws SQLBotException 当操作失败时抛出异常
     */
    public Object createOrUpdateTraining(String token, Object trainingInfo) throws SQLBotException {
        log.debug("正在创建或更新数据训练");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/system/data-training";
            Object response = httpUtil.put(fullUrl, trainingInfo, Object.class);

            log.info("数据训练创建或更新完成");
            return response;
        } catch (Exception e) {
            log.error("创建或更新数据训练失败: {}", e.getMessage(), e);
            throw new SQLBotException("创建或更新数据训练失败: " + e.getMessage(), e);
        }
    }

    /**
     * 删除数据训练
     *
     * @param token 认证令牌
     * @param idList 数据训练ID列表
     * @return 删除结果
     * @throws SQLBotException 当删除失败时抛出异常
     */
    public Object deleteTraining(String token, java.util.List<Integer> idList) throws SQLBotException {
        log.debug("正在删除数据训练，ID数量: {}", idList != null ? idList.size() : 0);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        if (idList == null || idList.isEmpty()) {
            throw new SQLBotException("数据训练ID列表不能为空");
        }

        try {
            httpUtil.setToken(token);

            // 构建请求参数
            java.util.Map<String, Object> params = new java.util.HashMap<>();
            params.put("id_list", idList);

            String fullUrl = properties.getUrl() + "/system/data-training";
            Object response = httpUtil.deleteWithBody(fullUrl, params, Object.class);

            log.info("成功删除数据训练，ID数量: {}", idList.size());
            return response;
        } catch (Exception e) {
            log.error("删除数据训练失败: {}", e.getMessage(), e);
            throw new SQLBotException("删除数据训练失败: " + e.getMessage(), e);
        }
    }
}