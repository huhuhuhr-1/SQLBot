package com.sqlbot.example.controller;

import com.sqlbot.example.model.response.TestResult;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 演示控制器
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
@RestController
@RequestMapping("/api/demo")
@Tag(name = "演示接口", description = "基本的演示接口")
public class DemoController {
    
    @GetMapping("/hello")
    @Operation(summary = "Hello World接口", description = "返回问候信息")
    public TestResult<String> hello() {
        return TestResult.success("Hello SQLBot! Spring Boot 2.x 示例项目运行正常");
    }
    
    @GetMapping("/status")
    @Operation(summary = "获取系统状态", description = "返回系统运行状态")
    public TestResult<String> getStatus() {
        return TestResult.success("系统运行正常，SQLBot Starter已就绪");
    }
}
