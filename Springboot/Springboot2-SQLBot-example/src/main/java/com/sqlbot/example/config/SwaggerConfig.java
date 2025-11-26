package com.sqlbot.example.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Swagger配置类
 *
 * @author SQLBot Team
 * @since 1.0.0
 */
@Configuration
public class SwaggerConfig {

    @Bean
    public OpenAPI customOpenAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("SQLBot API测试接口")
                        .description("SQLBot Spring Boot Starter 测试接口文档")
                        .version("1.0.0")
                        .contact(new Contact()
                                .name("SQLBot Team")
                                .url("https://github.com/sqlbot")
                                .email("sqlbot@example.com")));
    }
}
