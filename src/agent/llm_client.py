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
            print(f"[LLMClient Warning] LLM API call failed ({ex}). Falling back to schema mock generator.")
            return self._generate_mock_output(prompt, schema_cls)

    def _call_gemini(self, prompt: str, schema_cls: Type[T]) -> T:
        """Queries Gemini API using google-genai SDK or native urllib REST API."""
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
        except Exception:
            # Native urllib REST API fallback for zero dependency execution
            return self._call_gemini_rest_api(prompt, schema_cls)

    def _call_gemini_rest_api(self, prompt: str, schema_cls: Type[T]) -> T:
        """Native urllib REST API client for Google Gemini with multi-model fallback."""
        import urllib.request
        import json

        models_to_try = [
            self.model_name,
            "gemini-2.5-flash",
            "gemini-1.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-pro",
        ]

        headers = {"Content-Type": "application/json"}
        schema_json = json.dumps(schema_cls.model_json_schema())
        full_prompt = (
            f"You are a Senior Engineer AI Agent. Return strictly a JSON object matching this schema: {schema_json}\n\n"
            f"USER PROMPT:\n{prompt}"
        )
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2
            }
        }

        last_error = None
        for m in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={self.api_key}"
            try:
                req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=45) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    raw_text = resp_data["candidates"][0]["content"]["parts"][0]["text"]
                    return self.extract_json_schema(raw_text, schema_cls)
            except Exception as ex:
                last_error = ex
                continue

        raise last_error or RuntimeError("Failed to query Gemini API across all model endpoints.")

    def _call_openai(self, prompt: str, schema_cls: Type[T]) -> T:
        """Uses OpenAI structured outputs parser or native urllib REST API."""
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
            return self._call_openai_rest_api(prompt, schema_cls)

    def _call_openai_rest_api(self, prompt: str, schema_cls: Type[T]) -> T:
        """Native urllib REST API client for OpenAI."""
        import urllib.request
        import json

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        schema_json = json.dumps(schema_cls.model_json_schema())
        system_msg = f"You are a Senior Engineer AI Agent. Return strictly a valid JSON object matching this schema: {schema_json}"
        
        payload = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }
        
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=45) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            raw_text = resp_data["choices"][0]["message"]["content"]
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

        prompt_lower = prompt.lower()
        is_todo = "todo" in prompt_lower or "task manager" in prompt_lower or "task list" in prompt_lower
        is_calc = "calc" in prompt_lower or "calculator" in prompt_lower or "math" in prompt_lower
        is_snake = "snake" in prompt_lower or "game" in prompt_lower

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
            if is_snake:
                return FeatureSpecification(
                    feature_title="Snake Game Application",
                    summary="Retro Snake Game platform with Java Spring Boot REST API for high scores and React UI Canvas.",
                    entities=["GameSession", "HighScore", "Player"],
                    api_endpoints=["GET /api/game/scores", "POST /api/game/score", "GET /api/game/leaderboard"],
                    ui_views=["GameBoardCanvas", "ScoreBoard", "GameOverModal"],
                )
            elif is_calc:
                return FeatureSpecification(
                    feature_title="Full-Stack Calculator Application",
                    summary="Scientific and basic calculator with Java Spring Boot REST API and React UI.",
                    entities=["Calculation", "Operation", "History"],
                    api_endpoints=["POST /api/calculator/add", "POST /api/calculator/subtract", "GET /api/calculator/history"],
                    ui_views=["CalculatorKeypad", "DisplayScreen", "HistorySidebar"],
                )
            elif is_todo:
                return FeatureSpecification(
                    feature_title="Todo Task Management System",
                    summary="Task management platform with Java Spring Boot 3 REST API and React UI Dashboard.",
                    entities=["Task", "Category", "User"],
                    api_endpoints=["GET /api/tasks", "POST /api/tasks", "PUT /api/tasks/{id}", "DELETE /api/tasks/{id}"],
                    ui_views=["TaskList", "TaskCreateForm", "CategoryFilter"],
                )
            else:
                return FeatureSpecification(
                    feature_title="Order Management System",
                    summary="Full-stack Food Delivery Order Management System with Java Spring Boot REST API and React Dashboard UI.",
                    entities=["Order", "OrderItem", "Customer"],
                    api_endpoints=["GET /api/orders", "POST /api/orders", "GET /api/orders/{id}"],
                    ui_views=["OrderDashboard", "CreateOrderForm", "OrderDetailModal"],
                )
        elif schema_cls == SpringBootArtifacts:
            if is_snake:
                pom_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.snakegame</groupId>
  <artifactId>game-service</artifactId>
  <version>1.0.0</version>
  <name>game-service</name>
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
      <artifactId>spring-boot-starter-test</artifactId>
      <scope>test</scope>
    </dependency>
  </dependencies>
</project>
"""
                controller_code = """package com.snakegame.gameservice.controller;

import org.springframework.web.bind.annotation.*;
import java.util.*;

@RestController
@RequestMapping("/api/game")
@CrossOrigin(origins = "*")
public class SnakeGameController {

    private final List<Map<String, Object>> scores = new ArrayList<>();

    @GetMapping("/scores")
    public List<Map<String, Object>> getScores() {
        return scores;
    }

    @PostMapping("/score")
    public Map<String, Object> recordScore(@RequestParam String player, @RequestParam int score) {
        Map<String, Object> entry = Map.of("player", player, "score", score, "timestamp", new Date().toString());
        scores.add(entry);
        return entry;
    }
}
"""
                test_code = """package com.snakegame.gameservice.controller;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class SnakeGameControllerTest {
    @Test
    public void testScoreRecording() {
        SnakeGameController controller = new SnakeGameController();
        var res = controller.recordScore("Alex", 150);
        assertEquals("Alex", res.get("player"));
    }
}
"""
                return SpringBootArtifacts(
                    pom_xml=CodeFile(file_path="pom.xml", content=pom_content, description="Maven configuration"),
                    java_files=[
                        CodeFile(file_path="src/main/java/com/snakegame/gameservice/controller/SnakeGameController.java", content=controller_code, description="Snake Game Controller"),
                    ],
                    test_files=[
                        CodeFile(file_path="src/test/java/com/snakegame/gameservice/controller/SnakeGameControllerTest.java", content=test_code, description="Test Suite"),
                    ],
                )
            elif is_calc:
                pom_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.todoapp</groupId>
  <artifactId>task-service</artifactId>
  <version>1.0.0</version>
  <name>task-service</name>
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
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-test</artifactId>
      <scope>test</scope>
    </dependency>
  </dependencies>
</project>
"""
                controller_code = """package com.todoapp.taskservice.controller;

import org.springframework.web.bind.annotation.*;
import java.util.*;

@RestController
@RequestMapping("/api/tasks")
@CrossOrigin(origins = "*")
public class TaskController {

    private final List<Map<String, Object>> tasks = new ArrayList<>();

    @GetMapping
    public List<Map<String, Object>> getTasks() {
        return tasks;
    }

    @PostMapping
    public Map<String, Object> createTask(@RequestBody Map<String, Object> task) {
        task.put("id", UUID.randomUUID().toString());
        task.put("completed", false);
        tasks.add(task);
        return task;
    }

    @DeleteMapping("/{id}")
    public void deleteTask(@PathVariable String id) {
        tasks.removeIf(t -> id.equals(t.get("id")));
    }
}
"""
                test_code = """package com.todoapp.taskservice.controller;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class TaskControllerTest {
    @Test
    public void testTaskControllerCreation() {
        TaskController controller = new TaskController();
        assertNotNull(controller.getTasks());
    }
}
"""
                return SpringBootArtifacts(
                    pom_xml=CodeFile(file_path="pom.xml", content=pom_content, description="Maven configuration"),
                    java_files=[
                        CodeFile(file_path="src/main/java/com/todoapp/taskservice/controller/TaskController.java", content=controller_code, description="Task Controller"),
                    ],
                    test_files=[
                        CodeFile(file_path="src/test/java/com/todoapp/taskservice/controller/TaskControllerTest.java", content=test_code, description="Test Suite"),
                    ],
                )
            elif is_calc:
                pom_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.calcapp</groupId>
  <artifactId>calculator-service</artifactId>
  <version>1.0.0</version>
  <name>calculator-service</name>
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
      <artifactId>spring-boot-starter-test</artifactId>
      <scope>test</scope>
    </dependency>
  </dependencies>
</project>
"""
                controller_code = """package com.calcapp.calculatorservice.controller;

import org.springframework.web.bind.annotation.*;
import java.util.*;

@RestController
@RequestMapping("/api/calculator")
@CrossOrigin(origins = "*")
public class CalculatorController {

    private final List<String> history = new ArrayList<>();

    @PostMapping("/calculate")
    public Map<String, Object> calculate(@RequestParam double a, @RequestParam double b, @RequestParam String op) {
        double result = 0;
        switch (op) {
            case "+": result = a + b; break;
            case "-": result = a - b; break;
            case "*": result = a * b; break;
            case "/": result = b != 0 ? a / b : 0; break;
        }
        String logEntry = a + " " + op + " " + b + " = " + result;
        history.add(logEntry);
        Map<String, Object> res = new HashMap<>();
        res.put("result", result);
        res.put("expression", logEntry);
        return res;
    }

    @GetMapping("/history")
    public List<String> getHistory() {
        return history;
    }
}
"""
                test_code = """package com.calcapp.calculatorservice.controller;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class CalculatorControllerTest {
    @Test
    public void testAddition() {
        CalculatorController controller = new CalculatorController();
        var res = controller.calculate(5, 3, "+");
        assertEquals(8.0, res.get("result"));
    }
}
"""
                return SpringBootArtifacts(
                    pom_xml=CodeFile(file_path="pom.xml", content=pom_content, description="Maven configuration"),
                    java_files=[
                        CodeFile(file_path="src/main/java/com/calcapp/calculatorservice/controller/CalculatorController.java", content=controller_code, description="Calculator Controller"),
                    ],
                    test_files=[
                        CodeFile(file_path="src/test/java/com/calcapp/calculatorservice/controller/CalculatorControllerTest.java", content=test_code, description="Test Suite"),
                    ],
                )
            else:
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
    public List<Map<String, Object>> getAllOrders() {
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
            if is_todo:
                pkg_content = """{
  "name": "react-todo-dashboard",
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
                app_code = """import React, { useState } from 'react';
import './App.css';

export default function App() {
  const [tasks, setTasks] = useState([
    { id: 1, title: 'Learn Spring Boot 3 & React', completed: true },
    { id: 2, title: 'Deploy AI Engineer Agent Pipeline', completed: false }
  ]);
  const [text, setText] = useState('');

  const addTask = (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    setTasks([...tasks, { id: Date.now(), title: text, completed: false }]);
    setText('');
  };

  const toggleTask = (id) => {
    setTasks(tasks.map(t => t.id === id ? { ...t, completed: !t.completed } : t));
  };

  const deleteTask = (id) => {
    setTasks(tasks.filter(t => t.id !== id));
  };

  return (
    <div className="todo-container">
      <header className="header">
        <h1>📝 Todo Task Manager</h1>
      </header>
      <form onSubmit={addTask} className="task-form">
        <input 
          type="text" 
          value={text} 
          onChange={(e) => setText(e.target.value)} 
          placeholder="Add a new task..." 
          className="task-input"
        />
        <button type="submit" className="btn-add">Add Task</button>
      </form>
      <ul className="task-list">
        {tasks.map(t => (
          <li key={t.id} className={`task-item ${t.completed ? 'completed' : ''}`}>
            <span onClick={() => toggleTask(t.id)} className="task-title">{t.title}</span>
            <button onClick={() => deleteTask(t.id)} className="btn-delete">Delete</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
"""
                css_code = """.todo-container {
  font-family: 'Inter', sans-serif;
  background-color: #0f172a;
  color: #f8fafc;
  min-height: 100vh;
  padding: 2rem;
  max-width: 600px;
  margin: 0 auto;
}
.header { border-bottom: 2px solid #1e293b; margin-bottom: 1.5rem; }
.task-form { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; }
.task-input { flex: 1; padding: 0.75rem; border-radius: 6px; border: 1px solid #334155; background: #1e293b; color: #fff; }
.btn-add { background: #0284c7; color: white; border: none; padding: 0.75rem 1.25rem; border-radius: 6px; cursor: pointer; }
.task-list { list-style: none; padding: 0; }
.task-item { background: #1e293b; border: 1px solid #334155; padding: 1rem; border-radius: 8px; margin-bottom: 0.75rem; display: flex; justify-content: space-between; align-items: center; }
.task-item.completed .task-title { text-decoration: line-through; opacity: 0.6; }
.btn-delete { background: #ef4444; color: white; border: none; padding: 0.4rem 0.8rem; border-radius: 4px; cursor: pointer; }
"""
                test_code = """import { render, screen } from '@testing-library/react';
import App from './App';

test('renders todo manager header', () => {
  render(<App />);
  const headerElement = screen.getByText(/Todo Task Manager/i);
  expect(headerElement).toBeInTheDocument();
});
"""
                return ReactArtifacts(
                    package_json=CodeFile(file_path="package.json", content=pkg_content, description="NPM Package Config"),
                    component_files=[
                        CodeFile(file_path="src/App.jsx", content=app_code, description="React App Component"),
                        CodeFile(file_path="src/App.css", content=css_code, description="React App CSS"),
                    ],
                    test_files=[
                        CodeFile(file_path="src/App.test.jsx", content=test_code, description="React App Test"),
                    ],
                )
            elif is_calc:
                pkg_content = """{
  "name": "react-calculator-app",
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
                app_code = """import React, { useState } from 'react';
import './App.css';

export default function App() {
  const [display, setDisplay] = useState('0');
  const [expression, setExpression] = useState('');

  const handlePress = (val) => {
    if (display === '0' && val !== '.') {
      setDisplay(val);
    } else {
      setDisplay(display + val);
    }
  };

  const handleClear = () => {
    setDisplay('0');
    setExpression('');
  };

  const handleDelete = () => {
    if (display.length > 1) {
      setDisplay(display.slice(0, -1));
    } else {
      setDisplay('0');
    }
  };

  const handleEqual = () => {
    try {
      setExpression(display + ' =');
      const calculated = Function('"use strict";return (' + display + ')')();
      setDisplay(String(calculated));
    } catch {
      setDisplay('Error');
    }
  };

  return (
    <div className="calc-wrapper">
      <div className="calc-container">
        <header className="calc-header">
          <h2>🧮 Professional Calculator</h2>
          <span className="calc-badge">Spring Boot REST Connected</span>
        </header>

        <div className="calc-screen-box">
          <div className="calc-expression">{expression || '\u00A0'}</div>
          <div className="calc-screen">{display}</div>
        </div>

        <div className="calc-grid">
          <button onClick={handleClear} className="btn btn-clear">C</button>
          <button onClick={() => handlePress('(')} className="btn btn-util">(</button>
          <button onClick={() => handlePress(')')} className="btn btn-util">)</button>
          <button onClick={() => handlePress('/')} className="btn btn-op">÷</button>

          <button onClick={() => handlePress('7')} className="btn btn-num">7</button>
          <button onClick={() => handlePress('8')} className="btn btn-num">8</button>
          <button onClick={() => handlePress('9')} className="btn btn-num">9</button>
          <button onClick={() => handlePress('*')} className="btn btn-op">×</button>

          <button onClick={() => handlePress('4')} className="btn btn-num">4</button>
          <button onClick={() => handlePress('5')} className="btn btn-num">5</button>
          <button onClick={() => handlePress('6')} className="btn btn-num">6</button>
          <button onClick={() => handlePress('-')} className="btn btn-op">-</button>

          <button onClick={() => handlePress('1')} className="btn btn-num">1</button>
          <button onClick={() => handlePress('2')} className="btn btn-num">2</button>
          <button onClick={() => handlePress('3')} className="btn btn-num">3</button>
          <button onClick={() => handlePress('+')} className="btn btn-op">+</button>

          <button onClick={() => handlePress('0')} className="btn btn-num">0</button>
          <button onClick={() => handlePress('.')} className="btn btn-num">.</button>
          <button onClick={handleDelete} className="btn btn-util">⌫</button>
          <button onClick={handleEqual} className="btn btn-eq">=</button>
        </div>
      </div>
    </div>
  );
}
"""
                css_code = """.calc-wrapper {
  min-height: 100vh;
  background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
}

.calc-container {
  background: rgba(30, 41, 59, 0.7);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
  border-radius: 20px;
  padding: 2rem;
  width: 100%;
  max-width: 380px;
}

.calc-header {
  margin-bottom: 1.25rem;
  text-align: center;
}

.calc-header h2 {
  color: #f8fafc;
  font-size: 1.25rem;
  margin: 0 0 0.25rem 0;
  font-weight: 600;
}

.calc-badge {
  font-size: 0.75rem;
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.1);
  padding: 0.2rem 0.6rem;
  border-radius: 12px;
  border: 1px solid rgba(56, 189, 248, 0.2);
}

.calc-screen-box {
  background: #090d16;
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 1rem;
  margin-bottom: 1.25rem;
  text-align: right;
}

.calc-expression {
  font-size: 0.85rem;
  color: #94a3b8;
  min-height: 1.2rem;
}

.calc-screen {
  font-size: 2.25rem;
  font-weight: 700;
  color: #f8fafc;
  overflow-x: auto;
  white-space: nowrap;
}

.calc-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.75rem;
}

.btn {
  height: 54px;
  font-size: 1.2rem;
  font-weight: 600;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s ease-in-out;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn:active {
  transform: scale(0.95);
}

.btn-num {
  background: #1e293b;
  color: #f8fafc;
  border: 1px solid #334155;
}

.btn-num:hover {
  background: #334155;
}

.btn-op {
  background: #0284c7;
  color: #ffffff;
}

.btn-op:hover {
  background: #0369a1;
}

.btn-util {
  background: #475569;
  color: #f8fafc;
}

.btn-util:hover {
  background: #64748b;
}

.btn-clear {
  background: #ef4444;
  color: #ffffff;
}

.btn-clear:hover {
  background: #dc2626;
}

.btn-eq {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: #ffffff;
}

.btn-eq:hover {
  box-shadow: 0 0 15px rgba(16, 185, 129, 0.4);
}
"""
                test_code = """import { render, screen } from '@testing-library/react';
import App from './App';

test('renders calculator title', () => {
  render(<App />);
  const titleElement = screen.getByText(/Scientific Calculator/i);
  expect(titleElement).toBeInTheDocument();
});
"""
                return ReactArtifacts(
                    package_json=CodeFile(file_path="package.json", content=pkg_content, description="NPM Package Config"),
                    component_files=[
                        CodeFile(file_path="src/App.jsx", content=app_code, description="React App Component"),
                        CodeFile(file_path="src/App.css", content=css_code, description="React App CSS"),
                    ],
                    test_files=[
                        CodeFile(file_path="src/App.test.jsx", content=test_code, description="React App Test"),
                    ],
                )
            else:
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
                app_code = """import React, { useState } from 'react';
import './App.css';

export default function App() {
  const [orders] = useState([
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
.header { border-bottom: 2px solid #1e293b; padding-bottom: 1rem; margin-bottom: 2rem; }
.order-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.5rem; }
.order-card { background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 1.5rem; }
.badge { display: inline-block; padding: 0.25rem 0.5rem; border-radius: 4px; font-weight: bold; margin-top: 0.5rem; }
.badge.delivered { background-color: #065f46; color: #34d399; }
.badge.preparing { background-color: #92400e; color: #fbbf24; }
"""
                test_code = """import { render, screen } from '@testing-library/react';
import App from './App';

test('renders order dashboard title', () => {
  render(<App />);
  const titleElement = screen.getByText(/Food Order Dashboard/i);
  expect(titleElement).toBeInTheDocument();
});
"""
                return ReactArtifacts(
                    package_json=CodeFile(file_path="package.json", content=pkg_content, description="NPM Package Config"),
                    component_files=[
                        CodeFile(file_path="src/App.jsx", content=app_code, description="React App Component"),
                        CodeFile(file_path="src/App.css", content=css_code, description="React App CSS"),
                    ],
                    test_files=[
                        CodeFile(file_path="src/App.test.jsx", content=test_code, description="React App Test"),
                    ],
                )
        else:
            return schema_cls()
