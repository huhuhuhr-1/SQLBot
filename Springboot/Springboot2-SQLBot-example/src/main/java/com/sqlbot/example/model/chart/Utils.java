package com.sqlbot.example.model.chart;

import com.sqlbot.example.model.chart.sub.Data;
import com.sqlbot.example.model.chart.sub.Series;
import com.sqlbot.example.model.chart.sub.Title;
import com.sqlbot.example.model.chart.sub.XAxis;
import com.sqlbot.example.model.chart.sub.YAxis;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class Utils {

    public static MyTable convertToMyTable(SqlBotTable sqlBotTable) {
        if (sqlBotTable == null) {
            return null;
        }

        MyTable myTable = new MyTable();
        myTable.setType(sqlBotTable.getType());
        myTable.setTitle(sqlBotTable.getTitle());

        // 转换列头
        List<String> headers = new ArrayList<>();
        if (sqlBotTable.getColumns() != null) {
            for (com.sqlbot.example.model.chart.sub.Column column : sqlBotTable.getColumns()) {
                headers.add(column.getName());
            }
        }
        myTable.setHeaders(headers);

        // 转换数据
        List<List<String>> tableData = new ArrayList<>();
        Data data = sqlBotTable.getData();
        if (data != null && data.getData() != null) {
            for (Map<String, Object> row : data.getData()) {
                List<String> rowData = new ArrayList<>();
                if (data.getFields() != null) {
                    for (String field : data.getFields()) {
                        Object value = row.get(field);
                        rowData.add(value != null ? value.toString() : "");
                    }
                }
                tableData.add(rowData);
            }
        }
        myTable.setData(tableData);

        return myTable;
    }

    public static MyChartConfig convertToMyChartConfig(SqlBotChart sqlBotChart) {
        if (sqlBotChart == null) {
            return null;
        }

        MyChartConfig myChartConfig = new MyChartConfig();

        // 设置标题
        Title title = new Title();
        title.setText(sqlBotChart.getTitle());
        myChartConfig.setTitle(title);

        // 检查是否为条形图

        // 设置X轴
        XAxis xAxis = new XAxis();
        // 其他图表的X轴为类目轴
        xAxis.setType("category");
        if (sqlBotChart.getAxis() != null && sqlBotChart.getAxis().getX() != null) {
            xAxis.setName(sqlBotChart.getAxis().getX().getName());
        }

        // 从数据中提取X轴的值（条形图需要特殊处理）
        List<String> xAxisData = new ArrayList<>();
        if (sqlBotChart.getData() != null && sqlBotChart.getData().getData() != null) {
            String xValueKey = null;
            // 其他图表使用X轴的值
            if (sqlBotChart.getAxis() != null && sqlBotChart.getAxis().getX() != null) {
                xValueKey = sqlBotChart.getAxis().getX().getValue();
            }

            for (Map<String, Object> dataRow : sqlBotChart.getData().getData()) {
                if (xValueKey != null && dataRow.containsKey(xValueKey)) {
                    // 截取日期部分（去掉时间部分）
                    String dateTime = dataRow.get(xValueKey).toString();
                    if (dateTime.contains("T")) {
                        String datePart = dateTime.split("T")[0];
                        xAxisData.add(datePart);
                    } else {
                        xAxisData.add(dateTime);
                    }
                }
            }
        }

        // 条形图将数据放在Y轴上，其他图表放在X轴上
        xAxis.setData(xAxisData);
        myChartConfig.setxAxis(xAxis);

        // 设置Y轴
        // 其他图表的Y轴为数值轴
        YAxis yAxis = new YAxis();
        yAxis.setType("value");
        if (sqlBotChart.getAxis() != null && sqlBotChart.getAxis().getY() != null) {
            yAxis.setName(sqlBotChart.getAxis().getY().getName());
        }
        myChartConfig.setyAxis(yAxis);

        // 设置系列数据
        List<Series> seriesList = new ArrayList<>();
        Series series = new Series();
        series.setType(sqlBotChart.getType());

        List<Integer> seriesData = new ArrayList<>();
        if (sqlBotChart.getData() != null && sqlBotChart.getData().getData() != null) {
            String yValueKey = null;
            // 其他图表使用Y轴的值作为数据
            if (sqlBotChart.getAxis() != null && sqlBotChart.getAxis().getY() != null) {
                yValueKey = sqlBotChart.getAxis().getY().getValue();
            }

            for (Map<String, Object> dataRow : sqlBotChart.getData().getData()) {
                if (yValueKey != null && dataRow.containsKey(yValueKey)) {
                    Object value = dataRow.get(yValueKey);
                    if (value instanceof Number) {
                        seriesData.add(((Number) value).intValue());
                    } else {
                        try {
                            seriesData.add(Integer.parseInt(value.toString()));
                        } catch (NumberFormatException e) {
                            seriesData.add(0);
                        }
                    }
                }
            }
        }
        series.setData(seriesData);
        seriesList.add(series);
        myChartConfig.setSeries(seriesList);

        return myChartConfig;
    }
}