package com.sqlbot.example.model.chart.sub;

public class Column {
    private String name;    // 显示名称
    private String value;   // 字段值
    
    // 构造函数
    public Column() {}
    
    // Getter和Setter方法
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    
    public String getValue() { return value; }
    public void setValue(String value) { this.value = value; }
}
