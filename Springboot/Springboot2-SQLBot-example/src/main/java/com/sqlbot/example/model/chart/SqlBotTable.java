package com.sqlbot.example.model.chart;

import com.sqlbot.example.model.chart.sub.Column;
import com.sqlbot.example.model.chart.sub.Data;

import java.util.List;

public class SqlBotTable {
    private String type;
    private String title;
    private List<Column> columns;
    private Data data;

    public String getType() {
        return type;
    }

    public void setType(String type) {
        this.type = type;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public List<Column> getColumns() {
        return columns;
    }

    public void setColumns(List<Column> columns) {
        this.columns = columns;
    }

    public Data getData() {
        return data;
    }

    public void setData(Data data) {
        this.data = data;
    }
}
