package com.sqlbot.springboot.starter.api.terminology;

import com.sqlbot.springboot.starter.SQLBotProperties;
import com.sqlbot.springboot.starter.exception.SQLBotException;
import com.sqlbot.springboot.starter.util.HttpUtil;
import lombok.extern.slf4j.Slf4j;

/**
 * 术语服务类
 * 提供术语管理相关的API接口调用方法
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Slf4j
public class TerminologyService {

    private final SQLBotProperties properties;
    private final HttpUtil httpUtil;

    /**
     * 构造术语服务
     *
     * @param properties SQLBot配置属性
     */
    public TerminologyService(SQLBotProperties properties) {
        this.properties = properties;
        this.httpUtil = new HttpUtil(properties);
        log.info("TerminologyService 初始化完成");
    }

    /**
     * 获取术语分页列表
     *
     * @param token 认证令牌
     * @param currentPage 当前页码
     * @param pageSize 每页大小
     * @param word 搜索术语（可选）
     * @return 术语分页列表
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getTerminologyPage(String token, int currentPage, int pageSize, String word) throws SQLBotException {
        log.debug("正在获取术语分页列表，当前页: {}, 每页大小: {}, 搜索词: {}", currentPage, pageSize, word);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/system/terminology/page/" + currentPage + "/" + pageSize;
            if (word != null && !word.trim().isEmpty()) {
                fullUrl += "?word=" + java.net.URLEncoder.encode(word, "UTF-8");
            }
            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取术语分页列表，当前页: {}", currentPage);
            return response;
        } catch (Exception e) {
            log.error("获取术语分页列表失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取术语分页列表失败: " + e.getMessage(), e);
        }
    }

    /**
     * 创建或更新术语
     *
     * @param token 认证令牌
     * @param terminologyInfo 术语信息
     * @return 操作结果
     * @throws SQLBotException 当操作失败时抛出异常
     */
    public Object createOrUpdateTerminology(String token, Object terminologyInfo) throws SQLBotException {
        log.debug("正在创建或更新术语");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/system/terminology";
            Object response = httpUtil.put(fullUrl, terminologyInfo, Object.class);

            log.info("术语创建或更新完成");
            return response;
        } catch (Exception e) {
            log.error("创建或更新术语失败: {}", e.getMessage(), e);
            throw new SQLBotException("创建或更新术语失败: " + e.getMessage(), e);
        }
    }

    /**
     * 删除术语
     *
     * @param token 认证令牌
     * @param idList 术语ID列表
     * @return 删除结果
     * @throws SQLBotException 当删除失败时抛出异常
     */
    public Object deleteTerminology(String token, java.util.List<Integer> idList) throws SQLBotException {
        log.debug("正在删除术语，ID数量: {}", idList != null ? idList.size() : 0);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        if (idList == null || idList.isEmpty()) {
            throw new SQLBotException("术语ID列表不能为空");
        }

        try {
            httpUtil.setToken(token);

            // 构建请求参数
            java.util.Map<String, Object> params = new java.util.HashMap<>();
            params.put("id_list", idList);

            String fullUrl = properties.getUrl() + "/system/terminology";
            Object response = httpUtil.deleteWithBody(fullUrl, params, Object.class);

            log.info("成功删除术语，ID数量: {}", idList.size());
            return response;
        } catch (Exception e) {
            log.error("删除术语失败: {}", e.getMessage(), e);
            throw new SQLBotException("删除术语失败: " + e.getMessage(), e);
        }
    }
}