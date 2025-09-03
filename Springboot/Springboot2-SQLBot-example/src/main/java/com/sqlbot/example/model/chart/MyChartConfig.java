package com.sqlbot.example.model.chart;

import com.sqlbot.example.model.chart.sub.Series;
import com.sqlbot.example.model.chart.sub.Title;
import com.sqlbot.example.model.chart.sub.XAxis;
import com.sqlbot.example.model.chart.sub.YAxis;

import java.util.List;

public class MyChartConfig {
    private Title title;
    private XAxis xAxis;
    private YAxis yAxis;
    private List<Series> series;

    public Title getTitle() {
        return title;
    }

    public void setTitle(Title title) {
        this.title = title;
    }

    public XAxis getxAxis() {
        return xAxis;
    }

    public void setxAxis(XAxis xAxis) {
        this.xAxis = xAxis;
    }

    public YAxis getyAxis() {
        return yAxis;
    }

    public void setyAxis(YAxis yAxis) {
        this.yAxis = yAxis;
    }

    public List<Series> getSeries() {
        return series;
    }

    public void setSeries(List<Series> series) {
        this.series = series;
    }
}
