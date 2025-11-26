package com.sqlbot.springboot.starter.api.workspace;

import com.sqlbot.springboot.starter.SQLBotProperties;
import com.sqlbot.springboot.starter.exception.SQLBotException;
import com.sqlbot.springboot.starter.util.HttpUtil;
import lombok.extern.slf4j.Slf4j;

/**
 * 工作空间服务类
 * 提供工作空间管理相关的API接口调用方法
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Slf4j
public class WorkspaceService {

    private final SQLBotProperties properties;
    private final HttpUtil httpUtil;

    /**
     * 构造工作空间服务
     *
     * @param properties SQLBot配置属性
     */
    public WorkspaceService(SQLBotProperties properties) {
        this.properties = properties;
        this.httpUtil = new HttpUtil(properties);
        log.info("WorkspaceService 初始化完成");
    }

    /**
     * 获取工作空间用户选项分页列表
     *
     * @param token 认证令牌
     * @param pageNum 页码
     * @param pageSize 每页大小
     * @param oid 空间ID
     * @param keyword 搜索关键字（可选）
     * @return 工作空间用户选项分页列表
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getWorkspaceUserOptionPage(String token, int pageNum, int pageSize, int oid, String keyword) throws SQLBotException {
        log.debug("正在获取工作空间用户选项分页列表，页码: {}, 每页大小: {}, 空间ID: {}, 关键字: {}", pageNum, pageSize, oid, keyword);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/system/workspace/uws/option/pager/" + pageNum + "/" + pageSize + "?oid=" + oid;
            if (keyword != null && !keyword.trim().isEmpty()) {
                fullUrl += "&keyword=" + java.net.URLEncoder.encode(keyword, "UTF-8");
            }
            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取工作空间用户选项分页列表，页码: {}", pageNum);
            return response;
        } catch (Exception e) {
            log.error("获取工作空间用户选项分页列表失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取工作空间用户选项分页列表失败: " + e.getMessage(), e);
        }
    }

    /**
     * 获取工作空间用户选项
     *
     * @param token 认证令牌
     * @param keyword 搜索关键字
     * @return 工作空间用户选项
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getWorkspaceUserOption(String token, String keyword) throws SQLBotException {
        log.debug("正在获取工作空间用户选项，关键字: {}", keyword);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        if (keyword == null || keyword.trim().isEmpty()) {
            throw new SQLBotException("搜索关键字不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/system/workspace/uws/option?keyword=" + java.net.URLEncoder.encode(keyword, "UTF-8");
            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取工作空间用户选项");
            return response;
        } catch (Exception e) {
            log.error("获取工作空间用户选项失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取工作空间用户选项失败: " + e.getMessage(), e);
        }
    }

    /**
     * 获取工作空间用户分页列表
     *
     * @param token 认证令牌
     * @param pageNum 页码
     * @param pageSize 每页大小
     * @param keyword 搜索关键字（可选）
     * @param oid 空间ID（可选）
     * @return 工作空间用户分页列表
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getWorkspaceUserPage(String token, int pageNum, int pageSize, String keyword, Integer oid) throws SQLBotException {
        log.debug("正在获取工作空间用户分页列表，页码: {}, 每页大小: {}, 关键字: {}, 空间ID: {}", pageNum, pageSize, keyword, oid);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/system/workspace/uws/pager/" + pageNum + "/" + pageSize;
            fullUrl += "?";
            boolean hasParam = false;
            if (keyword != null && !keyword.trim().isEmpty()) {
                fullUrl += "keyword=" + java.net.URLEncoder.encode(keyword, "UTF-8");
                hasParam = true;
            }
            if (oid != null) {
                if (hasParam) fullUrl += "&";
                fullUrl += "oid=" + oid;
            }
            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取工作空间用户分页列表，页码: {}", pageNum);
            return response;
        } catch (Exception e) {
            log.error("获取工作空间用户分页列表失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取工作空间用户分页列表失败: " + e.getMessage(), e);
        }
    }

    /**
     * 创建工作空间用户关联
     *
     * @param token 认证令牌
     * @param createUserWsData 创建数据
     * @return 创建结果
     * @throws SQLBotException 当创建失败时抛出异常
     */
    public Object createWorkspaceUser(String token, Object createUserWsData) throws SQLBotException {
        log.debug("正在创建工作空间用户关联");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/system/workspace/uws";
            Object response = httpUtil.post(fullUrl, createUserWsData, Object.class);

            log.info("成功创建工作空间用户关联");
            return response;
        } catch (Exception e) {
            log.error("创建工作空间用户关联失败: {}", e.getMessage(), e);
            throw new SQLBotException("创建工作空间用户关联失败: " + e.getMessage(), e);
        }
    }

    /**
     * 编辑工作空间用户关联
     *
     * @param token 认证令牌
     * @param updateUserWsData 更新数据
     * @return 编辑结果
     * @throws SQLBotException 当编辑失败时抛出异常
     */
    public Object editWorkspaceUser(String token, Object updateUserWsData) throws SQLBotException {
        log.debug("正在编辑工作空间用户关联");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/system/workspace/uws";
            Object response = httpUtil.put(fullUrl, updateUserWsData, Object.class);

            log.info("成功编辑工作空间用户关联");
            return response;
        } catch (Exception e) {
            log.error("编辑工作空间用户关联失败: {}", e.getMessage(), e);
            throw new SQLBotException("编辑工作空间用户关联失败: " + e.getMessage(), e);
        }
    }

    /**
     * 删除工作空间用户关联
     *
     * @param token 认证令牌
     * @param deleteData 删除数据
     * @return 删除结果
     * @throws SQLBotException 当删除失败时抛出异常
     */
    public Object deleteWorkspaceUser(String token, Object deleteData) throws SQLBotException {
        log.debug("正在删除工作空间用户关联");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/system/workspace/uws";
            Object response = httpUtil.deleteWithBody(fullUrl, deleteData, Object.class);

            log.info("成功删除工作空间用户关联");
            return response;
        } catch (Exception e) {
            log.error("删除工作空间用户关联失败: {}", e.getMessage(), e);
            throw new SQLBotException("删除工作空间用户关联失败: " + e.getMessage(), e);
        }
    }

    /**
     * 获取工作空间列表
     *
     * @param token 认证令牌
     * @return 工作空间列表
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getWorkspaceList(String token) throws SQLBotException {
        log.debug("正在获取工作空间列表");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/system/workspace";
            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取工作空间列表");
            return response;
        } catch (Exception e) {
            log.error("获取工作空间列表失败: {}", e.getMessage(), e);
            throw new SQLBotException("获取工作空间列表失败: " + e.getMessage(), e);
        }
    }

    /**
     * 根据ID获取工作空间
     *
     * @param token 认证令牌
     * @param id 工作空间ID
     * @return 工作空间信息
     * @throws SQLBotException 当获取失败时抛出异常
     */
    public Object getWorkspaceById(String token, int id) throws SQLBotException {
        log.debug("正在获取工作空间，ID: {}", id);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/system/workspace/" + id;
            Object response = httpUtil.get(fullUrl, Object.class);

            log.info("成功获取工作空间，ID: {}", id);
            return response;
        } catch (Exception e) {
            log.error("根据ID获取工作空间失败: {}", e.getMessage(), e);
            throw new SQLBotException("根据ID获取工作空间失败: " + e.getMessage(), e);
        }
    }

    /**
     * 创建工作空间
     *
     * @param token 认证令牌
     * @param workspaceData 工作空间数据
     * @return 创建结果
     * @throws SQLBotException 当创建失败时抛出异常
     */
    public Object createWorkspace(String token, Object workspaceData) throws SQLBotException {
        log.debug("正在创建工作空间");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/system/workspace";
            Object response = httpUtil.post(fullUrl, workspaceData, Object.class);

            log.info("成功创建工作空间");
            return response;
        } catch (Exception e) {
            log.error("创建工作空间失败: {}", e.getMessage(), e);
            throw new SQLBotException("创建工作空间失败: " + e.getMessage(), e);
        }
    }

    /**
     * 更新工作空间
     *
     * @param token 认证令牌
     * @param workspaceData 工作空间数据
     * @return 更新结果
     * @throws SQLBotException 当更新失败时抛出异常
     */
    public Object updateWorkspace(String token, Object workspaceData) throws SQLBotException {
        log.debug("正在更新工作空间");

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/system/workspace";
            Object response = httpUtil.put(fullUrl, workspaceData, Object.class);

            log.info("成功更新工作空间");
            return response;
        } catch (Exception e) {
            log.error("更新工作空间失败: {}", e.getMessage(), e);
            throw new SQLBotException("更新工作空间失败: " + e.getMessage(), e);
        }
    }

    /**
     * 删除工作空间
     *
     * @param token 认证令牌
     * @param id 工作空间ID
     * @return 删除结果
     * @throws SQLBotException 当删除失败时抛出异常
     */
    public Object deleteWorkspace(String token, int id) throws SQLBotException {
        log.debug("正在删除工作空间，ID: {}", id);

        if (token == null || token.trim().isEmpty()) {
            throw new SQLBotException("认证令牌不能为空");
        }

        try {
            httpUtil.setToken(token);

            String fullUrl = properties.getUrl() + "/system/workspace/" + id;
            Object response = httpUtil.delete(fullUrl, Object.class);

            log.info("成功删除工作空间，ID: {}", id);
            return response;
        } catch (Exception e) {
            log.error("删除工作空间失败: {}", e.getMessage(), e);
            throw new SQLBotException("删除工作空间失败: " + e.getMessage(), e);
        }
    }
}