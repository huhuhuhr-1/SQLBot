package com.sqlbot.springboot.starter.model.request;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;

/**
 * 添加 PostgreSQL 数据源请求模型
 * <p>
 * 对应 JSON 示例：
 * {
 * "host": "172.28.147.208",
 * "port": "12432",
 * "username": "sqlbot",
 * "password": "sqlbot",
 * "database": "data-ai",
 * "extraJdbc": "",
 * "dbSchema": "public",
 * "filename": "",
 * "sheets": [],
 * "mode": "service_name",
 * "timeout": 30,
 * "tableName": "test123",
 * "tableComment": "测试数据集1"
 * }
 *
 * @author SQLBot
 * @since 1.0.0
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class PostAddPgRequest {

    /**
     * 主机地址
     */
    private String host = "";

    /**
     * 端口号
     */
    private String port = "";


    /**
     * 数据库用户名
     */
    private String username = "";

    /**
     * 数据库密码
     */
    private String password = "";


    /**
     * 数据库名称
     */
    private String database = "";


    /**
     * 额外 JDBC 参数
     */
    private String extraJdbc = "";


    /**
     * 数据库 schema 名称
     */
    private String dbSchema = "public";

    /**
     * 上传的文件名（可选）
     */
    private String filename = "";

    /**
     * Excel sheet 名称列表（可选）
     */
    private List<String> sheets = new ArrayList<>();

    /**
     * 模式（如 service_name, host, ip 等）
     */
    private String mode = "service_name";

    /**
     * 超时时间（秒）
     */
    private Integer timeout = 30;

    /**
     * 表名
     */
    private String tableName = "";

    /**
     * 表注释
     */
    private String tableComment = "";

}
