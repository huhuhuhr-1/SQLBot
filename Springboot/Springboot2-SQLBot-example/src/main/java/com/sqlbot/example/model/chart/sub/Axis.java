package com.sqlbot.example.model.chart.sub;

public class Axis {
    private AxisInfo x;
    private AxisInfo y;
    
    // 构造函数
    public Axis() {}
    
    // Getter和Setter方法
    public AxisInfo getX() { return x; }
    public void setX(AxisInfo x) { this.x = x; }
    
    public AxisInfo getY() { return y; }
    public void setY(AxisInfo y) { this.y = y; }
}
