package com.foodapp.orderservice.controller;

import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/orders")
@CrossOrigin(origins = "*")
public class OrderController {

    @GetMapping
    public List<Map<str, Object>> getAllOrders() {
        return List.of(
            Map.of("id", 1, "customer", "John Doe", "amount", 29.99, "status", "DELIVERED"),
            Map.of("id", 2, "customer", "Jane Smith", "amount", 45.50, "status", "PREPARING")
        );
    }

    @PostMapping
    public Map<str, Object> createOrder(@RequestBody Map<str, Object> order) {
        return Map.of("id", 3, "customer", order.getOrDefault("customer", "Guest"), "status", "CREATED");
    }
}
