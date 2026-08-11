# 🚀 Order Management System

Full-stack Food Delivery Order Management System with Java Spring Boot REST API and React Dashboard UI.

This is a **standalone, fully decoupled Full-Stack Application** generated independently of the AI Agent.

---

## 🏗️ Project Architecture

* **Backend (`/backend`)**: Java Spring Boot 3 REST API (Maven, JPA, H2/PostgreSQL)
* **Frontend (`/frontend`)**: Modern React UI (NPM, JSX/TSX, CSS, API Client)

---

## ⚡ Quick Start & How to Run

### 1. Run Java Spring Boot Backend
```bash
cd backend
mvn spring-boot:run
```
Backend runs at `http://localhost:8080` (H2 Console: `http://localhost:8080/h2-console`)

### 2. Run React UI Frontend
```bash
cd frontend
npm install
npm start
```
Frontend runs at `http://localhost:3000`

### 3. Run Backend & Frontend Tests
```bash
# Backend JUnit 5 tests
cd backend && mvn test

# Frontend React tests
cd frontend && npm test
```

---

## 🐳 Docker Deployment
Run backend and frontend containers together:
```bash
docker-compose up --build
```
