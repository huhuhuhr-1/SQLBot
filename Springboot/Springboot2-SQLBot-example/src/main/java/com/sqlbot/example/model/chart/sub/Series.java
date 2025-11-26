package com.sqlbot.example.model.chart.sub;

import java.util.List;

// 系列数据类
public class Series {
    private String type;
    private List<Integer> data;
    
    public Series() {}
    
    public String getType() { return type; }
    public void setType(String type) { this.type = type; }
    
    public List<Integer> getData() { return data; }
    public void setData(List<Integer> data) { this.data = data; }
}
