package com.sqlbot.example;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.sqlbot.example.model.chart.MyChartConfig;
import com.sqlbot.example.model.chart.MyTable;
import com.sqlbot.example.model.chart.SqlBotChart;
import com.sqlbot.example.model.chart.SqlBotTable;
import com.sqlbot.example.model.chart.Utils;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;

public class UnifiedConverterDemo {

    private static final ObjectMapper objectMapper = new ObjectMapper();

    static {
        // 配置ObjectMapper以美化输出JSON
        objectMapper.enable(SerializationFeature.INDENT_OUTPUT);
    }

    public static void main(String[] args) {
        System.out.println("请提供JSON文件路径作为参数");
        System.out.println("使用示例:");
        System.out.println("  java UnifiedConverterDemo file1.json file2.json ...");
        System.out.println("如果没有提供参数，将使用默认的示例文件进行测试");

        // 使用默认的示例文件
        String[] defaultFiles = {
                "D:\\github\\SQLBot\\Springboot\\Springboot2-SQLBot-example\\src\\main\\resources\\table-sample.json",
                "D:\\github\\SQLBot\\Springboot\\Springboot2-SQLBot-example\\src\\main\\resources\\line-chart-sample.json",
                "D:\\github\\SQLBot\\Springboot\\Springboot2-SQLBot-example\\src\\main\\resources\\bar-chart-sample.json",
                "D:\\github\\SQLBot\\Springboot\\Springboot2-SQLBot-example\\src\\main\\resources\\pie-chart-sample.json"
        };

        for (String file : defaultFiles) {
            if (Files.exists(Paths.get(file))) {
                System.out.println("\n========================================");
                System.out.println("处理文件: " + file);
                System.out.println("========================================");
                processFile(file);
            } else {
                System.out.println("文件不存在: " + file);
            }
        }
    }

    private static void processFile(String filePath) {
        if (!filePath.endsWith(".json") || !Files.exists(Paths.get(filePath))) {
            System.err.println("文件不存在或不是JSON文件: " + filePath);
            return;
        }

        try {
            // 从文件读取
            String jsonContent = new String(Files.readAllBytes(Paths.get(filePath)));
            System.out.println("原始数据:");
            System.out.println(jsonContent);

            // 解析JSON并确定类型
            String type = getTypeFromJson(jsonContent);
            System.out.println("\n----------------------------------------\n");

            switch (type) {
                case "table":
                    handleTableConversion(jsonContent);
                    break;
                case "line":
                case "bar":
                case "pie":
                    handleChartConversion(jsonContent);
                    break;
                default:
                    System.out.println("不支持的类型: " + type);
            }
        } catch (Exception e) {
            System.err.println("处理JSON时出错: " + e.getMessage());
            e.printStackTrace();
        }
    }

    private static String getTypeFromJson(String jsonContent) throws IOException {
        return objectMapper.readTree(jsonContent).get("type").asText();
    }

    private static void handleTableConversion(String jsonContent) throws IOException {
        SqlBotTable sqlBotTable = objectMapper.readValue(jsonContent, SqlBotTable.class);
        MyTable myTable = Utils.convertToMyTable(sqlBotTable);

        System.out.println("转换后的MyTable对象 (JSON格式):");
        System.out.println(objectMapper.writeValueAsString(myTable));
    }

    private static void handleChartConversion(String jsonContent) throws IOException {
        SqlBotChart sqlBotChart = objectMapper.readValue(jsonContent, SqlBotChart.class);
        MyChartConfig myChartConfig = Utils.convertToMyChartConfig(sqlBotChart);

        System.out.println("转换后的MyChartConfig对象 (JSON格式):");
        System.out.println(objectMapper.writeValueAsString(myChartConfig));
    }
}