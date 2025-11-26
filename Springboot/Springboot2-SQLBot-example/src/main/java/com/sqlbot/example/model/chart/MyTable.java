package com.sqlbot.example.model.chart;

import java.util.List;

public class MyTable {
    private String type;
    private String title;
    private List<String> headers;
    private List<List<String>> data;

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

    public List<String> getHeaders() {
        return headers;
    }

    public void setHeaders(List<String> headers) {
        this.headers = headers;
    }

    public List<List<String>> getData() {
        return data;
    }

    public void setData(List<List<String>> data) {
        this.data = data;
    }

    @Override
    public String toString() {
        return "MyTable{" +
                "type='" + type + '\'' +
                ", title='" + title + '\'' +
                ", headers=" + headers +
                ", data=" + data +
                '}';
    }
}