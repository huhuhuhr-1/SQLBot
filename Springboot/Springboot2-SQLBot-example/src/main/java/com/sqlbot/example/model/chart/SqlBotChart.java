package com.sqlbot.example.model.chart;


import com.sqlbot.example.model.chart.sub.Axis;
import com.sqlbot.example.model.chart.sub.Data;

public class SqlBotChart {
    private String type;
    private String title;
    private Axis axis;
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

    public Axis getAxis() {
        return axis;
    }

    public void setAxis(Axis axis) {
        this.axis = axis;
    }

    public Data getData() {
        return data;
    }

    public void setData(Data data) {
        this.data = data;
    }
}
