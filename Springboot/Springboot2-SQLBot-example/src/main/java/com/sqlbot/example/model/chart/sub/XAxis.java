package com.sqlbot.example.model.chart.sub;

import java.util.List;

// X轴配置类
public class XAxis {
    private String type;
    private String name;
    private List<String> data;
    
    public XAxis() {}
    
    public String getType() { return type; }
    public void setType(String type) { this.type = type; }
    
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    
    public List<String> getData() { return data; }
    public void setData(List<String> data) { this.data = data; }
}
