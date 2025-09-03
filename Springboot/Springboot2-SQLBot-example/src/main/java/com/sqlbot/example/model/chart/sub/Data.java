package com.sqlbot.example.model.chart.sub;

import java.util.List;
import java.util.Map;

public class Data {
    private List<String> fields;
    private List<Map<String, Object>> data;
    
    // 构造函数
    public Data() {}
    
    // Getter和Setter方法
    public List<String> getFields() { return fields; }
    public void setFields(List<String> fields) { this.fields = fields; }
    
    public List<Map<String, Object>> getData() { return data; }
    public void setData(List<Map<String, Object>> data) { this.data = data; }
}
