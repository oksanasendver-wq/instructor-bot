# Architecture Documentation

## Общая архитектура

```
Frontend (React)
    ↓
Backend API (FastAPI)
    ↓
Services Layer
    ↓
Models Layer (SQLAlchemy)
    ↓
PostgreSQL
```

## Backend слои

### 1. API Layer
- REST endpoints
- Request/Response models
- Validation

### 2. Services Layer
- ScoreEngine
- AIProvider
- AccessControl
- AttentionFlagManager
- Audit

### 3. Models Layer
- SQLAlchemy models
- Database schema
- Relationships

### 4. Core Layer
- Configuration
- Database connection
- Security

## Frontend архитектура

### Mini App
- Pages (Today, Report, ClientProfile)
- Services (API client)
- Store (Zustand)

### Admin
- Pages (Login, Dashboard, CRUD)
- Components (Modal, Forms, Layout)
- Services (API client)
