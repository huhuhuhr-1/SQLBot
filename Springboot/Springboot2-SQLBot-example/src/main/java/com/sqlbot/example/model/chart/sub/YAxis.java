package com.sqlbot.example.model.chart.sub;

import java.util.List;

// Y轴配置类
public class YAxis {
    private String type;
    private String name;
    private List<String> data;

    public YAxis() {
    }

    public List<String> getData() {
        return data;
    }

    public void setData(List<String> data) {
        this.data = data;
    }

    public String getType() {
        return type;
    }

    public void setType(String type) {
        this.type = type;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }
}
