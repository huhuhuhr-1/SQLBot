package com.sqlbot.example;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

/**
 * Spring Boot 3.x SQLBot示例应用
 * 
 * @author SQLBot Team
 * @since 1.0.0
 */
@SpringBootApplication
@EnableAsync
public class Springboot3SqlbotExampleApplication {
    
    public static void main(String[] args) {
        SpringApplication.run(Springboot3SqlbotExampleApplication.class, args);
    }
}