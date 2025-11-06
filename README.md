# Vehicle Inspection System

A FastAPI-based vehicle inspection system implementing hexagonal architecture with support for car and motorcycle inspections using an 8-point evaluation system.

## 🏗️ Architecture

This project follows **Hexagonal Architecture** (Ports and Adapters) with **Domain-Driven Design** principles:

```
src/vehicle_inspection/
├── domain/                 # Domain layer (business logic)
│   ├── entities/          # Domain entities (Vehicle, Car, Motorcycle)
│   ├── value_objects/     # Immutable value objects
│   └── services/          # Domain services
├── application/           # Application layer (use cases)
│   ├── services/         # Application services
│   └── ports/            # Port interfaces
├── infrastructure/       # Infrastructure layer (adapters)
│   ├── adapters/         # External service adapters
│   ├── repositories/     # Data persistence
│   └── database/         # Database configuration
└── presentation/         # Presentation layer (API)
    └── api/              # FastAPI routes and schemas
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 12+
- Docker & Docker Compose (optional)

### 1. Environment Setup

```bash
# Clone and navigate to project
cd vehicle-status-scan

# Copy environment variables
cp .env.example .env

# Edit .env file with your database credentials
```

### 2. Installation

```bash
# Install uv package manager (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment with uv
uv venv .venv
source .venv/bin/activate

# Install dependencies using uv
uv pip install -e .

# Install development dependencies
uv pip install -e ".[dev]"
```

### 3. Database Setup

```bash
# Start PostgreSQL with Docker
docker-compose up -d db

# Run database migrations (when implemented)
alembic upgrade head
```

### 4. Run the Application

#### Option A: Local Development
```bash
# Run FastAPI development server
uvicorn src.vehicle_inspection.presentation.api.main:app --reload --host 0.0.0.0 --port 8000
```

#### Option B: Docker Compose
```bash
# Run entire stack
docker-compose up
```

### 5. Access the API

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Root Endpoint**: http://localhost:8000/

## 🔧 Development

### Code Quality Tools

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/

# Run tests
pytest

# Test with coverage
pytest --cov=src/vehicle_inspection --cov-report=html

# Verify Hexagonal Architecture with import-linter
lint-imports --config .import-linter

# Verbose import-linter output
lint-imports --config .import-linter --verbose
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

## 🧪 Testing

The project includes comprehensive testing following the test pyramid:

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# All tests with coverage
pytest --cov=src/vehicle_inspection --cov-report=term-missing
```

## 🏛️ Design Patterns Implemented

### SOLID Principles
- **S**ingle Responsibility: Each class has one reason to change
- **O**pen/Closed: Vehicle hierarchy extensible without modification
- **L**iskov Substitution: Car/Motorcycle interchangeable through Vehicle interface
- **I**nterface Segregation: Specific interfaces for repositories and services
- **D**ependency Inversion: Dependencies on abstractions, not implementations

### Patterns
- **Factory Pattern**: Vehicle creation
- **Repository Pattern**: Data access abstraction
- **Strategy Pattern**: Vehicle-specific scoring algorithms
- **Dependency Injection**: Service composition
- **Value Object Pattern**: Immutable domain values

## 🔍 Key Features

### Domain Features
- Vehicle inheritance (Car/Motorcycle)
- 8-point inspection system
- Automatic safety evaluation
- Business rule validation

### Technical Features
- Async/await support
- Database connection pooling
- CORS middleware
- Health checks
- Environment-based configuration
- Docker containerization

## 📚 API Endpoints

### Health
- `GET /health` - System health check
- `GET /` - Root endpoint

### Vehicles
- `GET /api/v1/vehicles` - List vehicles
- `POST /api/v1/vehicles` - Create vehicle
- `GET /api/v1/vehicles/{license_plate}` - Get vehicle

### Bookings
- `GET /api/v1/bookings` - List bookings
- `POST /api/v1/bookings` - Create booking
- `GET /api/v1/bookings/{booking_id}` - Get booking

### Inspections
- `GET /api/v1/inspections` - List inspections
- `POST /api/v1/inspections` - Create inspection
- `GET /api/v1/inspections/{inspection_id}` - Get inspection

## 🤝 Contributing

1. Follow the established architecture patterns
2. Write tests for new features
3. Update documentation
4. Follow code style guidelines
5. Create meaningful commit messages

## 📄 License

This project is licensed under the MIT License.

---

**Next Steps**: Run the setup commands above and start implementing the business logic following the established architecture patterns.
