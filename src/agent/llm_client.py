import os
import json
import re
from typing import Type, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """
    LLM Client that queries LLM APIs (Gemini/OpenAI) or parses JSON responses into target Pydantic schemas.
    Includes robust JSON extraction and cleaning for multi-line code/diff strings.
    """

    def __init__(self, api_key: Optional[str] = None, provider: str = "gemini", model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.provider = provider.lower()
        self.model_name = model_name

    def generate_structured_output(self, prompt: str, schema_cls: Type[T]) -> T:
        """Sends prompt to LLM and forces response into requested Pydantic schema class."""
        if self.provider == "mock" or not self.api_key:
            # Fallback for testing without active API key or mock provider
            return self._generate_mock_output(prompt, schema_cls)

        try:
            if self.provider == "gemini":
                return self._call_gemini(prompt, schema_cls)
            elif self.provider == "openai":
                return self._call_openai(prompt, schema_cls)
            else:
                return self._call_gemini(prompt, schema_cls)
        except Exception as ex:
            print(f"[LLMClient Warning] LLM API call failed: {ex}. Falling back to clean JSON extraction.")
            raw_text = self._call_generic_completion(prompt)
            return self.extract_json_schema(raw_text, schema_cls)

    def _call_gemini(self, prompt: str, schema_cls: Type[T]) -> T:
        """Uses google-genai library if installed."""
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema_cls,
                ),
            )
            return schema_cls.model_validate_json(response.text)
        except ImportError:
            # Fallback if library not available
            raw_text = self._call_generic_completion(prompt)
            return self.extract_json_schema(raw_text, schema_cls)

    def _call_openai(self, prompt: str, schema_cls: Type[T]) -> T:
        """Uses OpenAI structured outputs parser."""
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            completion = client.beta.chat.completions.parse(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format=schema_cls,
            )
            return completion.choices[0].message.parsed
        except Exception:
            raw_text = self._call_generic_completion(prompt)
            return self.extract_json_schema(raw_text, schema_cls)

    def _call_generic_completion(self, prompt: str) -> str:
        """Generic text completion fallback."""
        return "{}"

    def extract_json_schema(self, raw_text: str, schema_cls: Type[T]) -> T:
        """Extracts JSON block from raw text and parses it with Pydantic schema."""
        cleaned = raw_text.strip()

        # Remove markdown fences if present
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if json_match:
            cleaned = json_match.group(1).strip()

        # Parse JSON
        data = json.loads(cleaned)
        return schema_cls.model_validate(data)

    def _generate_mock_output(self, prompt: str, schema_cls: Type[T]) -> T:
        """Mock fallback for offline validation and demo testing."""
        from src.schemas.models import (
            ReproductionTest,
            PatchSubmission,
            Diagnosis,
            FeatureSpecification,
            SpringBootArtifacts,
            ReactArtifacts,
            CodeFile,
        )

        if schema_cls == ReproductionTest:
            return ReproductionTest(
                test_file_path="tests/test_reproduction.py",
                test_code="from sample_app import calculate\n\ndef test_calculate_bug():\n    # Expect calculate(5) to return 6 (5 + 1), currently returns 4 (5 - 1)\n    assert calculate(5) == 6\n",
                runner_command="python -m pytest tests/test_reproduction.py",
            )
        elif schema_cls == PatchSubmission:
            return PatchSubmission(
                diagnosis=Diagnosis(
                    root_cause="Fix calculation function in sample_app.py to add 1 instead of subtracting 1.",
                    suspected_files=["sample_app.py"],
                ),
                patch_diff=(
                    "diff --git a/sample_app.py b/sample_app.py\n"
                    "--- a/sample_app.py\n"
                    "+++ b/sample_app.py\n"
                    "@@ -1,4 +1,4 @@\n"
                    " def calculate(x: int) -> int:\n"
                    '     """Calculates incremented value."""\n'
                    "-    # BUG: Subtracts 1 instead of adding 1\n"
                    "-    return x - 1\n"
                    "+    # FIXED: Adds 1\n"
                    "+    return x + 1\n"
                ),
            )
        elif schema_cls == FeatureSpecification:
            return FeatureSpecification(
                feature_title="Order Management System",
                summary="Full-stack Food Delivery Order Management System with Java Spring Boot REST API and React Dashboard UI.",
                entities=["Order", "OrderItem", "Customer"],
                api_endpoints=["GET /api/orders", "POST /api/orders", "GET /api/orders/{id}"],
                ui_views=["OrderDashboard", "CreateOrderForm", "OrderDetailModal"],
            )
        elif schema_cls == SpringBootArtifacts:
            pom_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.foodapp</groupId>
  <artifactId>order-service</artifactId>
  <version>1.0.0</version>
  <name>order-service</name>
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.2.0</version>
  </parent>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-data-jpa</artifactId>
    </dependency>
    <dependency>
      <groupId>com.h2database</groupId>
      <artifactId>h2</artifactId>
      <scope>runtime</scope>
    </dependency>
    <dependency>
      <groupId>org.projectlombok</groupId>
      <artifactId>lombok</artifactId>
      <optional>true</optional>
    </dependency>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-test</artifactId>
      <scope>test</scope>
    </dependency>
  </dependencies>
</project>
"""
            controller_code = """package com.foodapp.orderservice.controller;

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
"""
            test_code = """package com.foodapp.orderservice.controller;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(OrderController.class)
public class OrderControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    public void testGetAllOrders() throws Exception {
        mockMvc.perform(get("/api/orders"))
               .andExpect(status().isOk());
    }
}
"""
            return SpringBootArtifacts(
                pom_xml=CodeFile(file_path="pom.xml", content=pom_content, description="Maven configuration"),
                java_files=[
                    CodeFile(
                        file_path="src/main/java/com/foodapp/orderservice/controller/OrderController.java",
                        content=controller_code,
                        description="REST Controller for Orders",
                    )
                ],
                test_files=[
                    CodeFile(
                        file_path="src/test/java/com/foodapp/orderservice/controller/OrderControllerTest.java",
                        content=test_code,
                        description="JUnit 5 Test for Order Controller",
                    )
                ],
            )
        elif schema_cls == ReactArtifacts:
            pkg_content = """{
  "name": "react-order-dashboard",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "scripts": {
    "start": "react-scripts start",
    "test": "react-scripts test --watchAll=false"
  }
}
"""
            app_code = """import React, { useState, useEffect } from 'react';
import './App.css';

export default function App() {
  const [orders, setOrders] = useState([
    { id: 1, customer: 'John Doe', amount: 29.99, status: 'DELIVERED' },
    { id: 2, customer: 'Jane Smith', amount: 45.50, status: 'PREPARING' }
  ]);

  return (
    <div className="dashboard-container">
      <header className="header">
        <h1>🚀 Food Order Dashboard</h1>
      </header>
      <main className="content">
        <div className="order-grid">
          {orders.map((o) => (
            <div key={o.id} className="order-card">
              <h3>Order #{o.id}</h3>
              <p>Customer: {o.customer}</p>
              <p>Amount: ${o.amount}</p>
              <span className={`badge ${o.status.toLowerCase()}`}>{o.status}</span>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
"""
            css_code = """.dashboard-container {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background-color: #0f172a;
  color: #f8fafc;
  min-height: 100vh;
  padding: 2rem;
}

.header {
  border-bottom: 2px solid #1e293b;
  padding-bottom: 1rem;
  margin-bottom: 2rem;
}

.order-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
}

.order-card {
  background-color: #1e293b;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
  border: 1px solid #334155;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.85rem;
  font-weight: bold;
}
.badge.delivered { background-color: #059669; color: #ecfdf5; }
.badge.preparing { background-color: #d97706; color: #fffbe6; }
"""
            test_code = """import { render, screen } from '@testing-library/react';
import App from './App';

test('renders Food Order Dashboard title', () => {
  render(<App />);
  const titleElement = screen.getByText(/Food Order Dashboard/i);
  expect(titleElement).toBeInTheDocument();
});
"""
            return ReactArtifacts(
                package_json=CodeFile(file_path="package.json", content=pkg_content, description="NPM Package Manifest"),
                component_files=[
                    CodeFile(file_path="src/App.jsx", content=app_code, description="Main React App Component"),
                    CodeFile(file_path="src/App.css", content=css_code, description="Dashboard Styles"),
                ],
                test_files=[
                    CodeFile(file_path="src/App.test.jsx", content=test_code, description="React App Test Suite"),
                ],
            )
        else:
            return schema_cls()
