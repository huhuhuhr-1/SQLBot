package com.sqlbot.example.controller;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

/**
 * 测试页面控制器
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
@Controller
public class TestPageController {
    
    @GetMapping("/")
    public String index() {
        return "index";
    }
    
    @GetMapping("/test")
    public String test() {
        return "test";
    }
    
    @GetMapping("/workflow-test")
    public String workflowTest() {
        return "workflow-test";
    }
    
    @GetMapping("/stream-test")
    public String streamTest() {
        return "stream-test";
    }
    
    @GetMapping("/chat-test")
    public String chatTest() {
        return "chat-test";
    }
}

