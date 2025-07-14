# Athlete Service API

A modern, high-performance REST API for managing athlete information built with FastAPI, SQLAlchemy, and PostgreSQL.

## 🚀 Features

- **RESTful API**: Complete CRUD operations for athlete management
- **Async Database**: Built with SQLAlchemy async for high performance
- **Data Validation**: Pydantic models for request/response validation
- **Health Monitoring**: Built-in health check endpoint
- **Logging**: Structured logging with Logfire integration
- **Docker Support**: Containerized application with Docker Compose
- **Database**: PostgreSQL with async driver support

## 📋 Prerequisites

- Python 3.12+
- PostgreSQL 15+
- Docker & Docker Compose (for containerized deployment)

## 🛠️ Installation

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd athlete-service
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```env
   DB_USER=postgres
   DB_PASSWORD=postgres
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=athlete_db
   ```

5. **Start PostgreSQL database**
   ```bash
   # Using Docker
   docker run -d \
     --name postgres \
     -e POSTGRES_USER=postgres \
     -e POSTGRES_PASSWORD=postgres \
     -e POSTGRES_DB=athlete_db \
     -p 5432:5432 \
     postgres:15
   ```

6. **Run the application**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Docker Deployment

1. **Using Docker Compose (Recommended)**
   ```bash
   docker-compose up -d
   ```

2. **Using Docker directly**
   ```bash
   docker build -t athlete-service .
   docker run -p 8000:8000 athlete-service
   ```

## 📚 API Documentation

Once the application is running, you can access:

- **Interactive API Documentation**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## 🔌 API Endpoints

### Health Check
- `GET /health` - Service health status

### Athletes
- `GET /athletes` - List all athletes (with pagination)
- `POST /athletes` - Create a new athlete
- `GET /athletes/{athlete_id}` - Get athlete by ID
- `PATCH /athletes/{athlete_id}` - Update athlete
- `DELETE /athletes/{athlete_id}` - Delete athlete

### Query Parameters
- `offset` (int): Number of records to skip (default: 0)
- `limit` (int): Maximum number of records to return (default: 100, max: 100)

## 📊 Data Models

### Athlete Schema
```json
{
  "id": 1,
  "name": "string",
  "country": "string",
  "birth_date": "YYYY-MM-DD",
  "height": 180,
  "weight": 75,
  "sport": "string",
  "nick_name": "string",
  "bio": "string",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

## 🧪 Testing

### Example API Calls

**Create an athlete:**
```bash
curl -X POST "http://localhost:8000/athletes/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "country": "USA",
    "birth_date": "1995-05-15",
    "height": 185,
    "weight": 80,
    "sport": "Basketball",
    "nick_name": "JD",
    "bio": "Professional basketball player"
  }'
```

**Get all athletes:**
```bash
curl -X GET "http://localhost:8000/athletes/"
```

**Get athlete by ID:**
```bash
curl -X GET "http://localhost:8000/athletes/1"
```

**Update athlete:**
```bash
curl -X PATCH "http://localhost:8000/athletes/1" \
  -H "Content-Type: application/json" \
  -d '{
    "weight": 82,
    "bio": "Updated bio information"
  }'
```

**Delete athlete:**
```bash
curl -X DELETE "http://localhost:8000/athletes/1"
```

## 🏗️ Project Structure

```
athlete-service/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application entry point
│   ├── config.py        # Database configuration
│   ├── models.py        # SQLAlchemy models and Pydantic schemas
│   └── router.py        # API routes and endpoints
├── docker-compose.yml   # Docker Compose configuration
├── Dockerfile          # Docker image definition
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## 🔧 Configuration

### Environment Variables

| Variable      | Description       | Default     |
| ------------- | ----------------- | ----------- |
| `DB_USER`     | Database username | `postgres`  |
| `DB_PASSWORD` | Database password | `postgres`  |
| `DB_HOST`     | Database host     | `localhost` |
| `DB_PORT`     | Database port     | `5432`      |
| `DB_NAME`     | Database name     | `postgres`  |

## 🚀 Deployment

### Production Considerations

1. **Environment Variables**: Set proper production database credentials
2. **Security**: Use strong passwords and consider SSL connections
3. **Monitoring**: Enable Logfire or other monitoring solutions
4. **Scaling**: Use multiple workers with uvicorn or gunicorn
5. **Reverse Proxy**: Use nginx or similar for production deployments

### Docker Production Build

```bash
# Build production image
docker build -t athlete-service:latest .

# Run with production settings
docker run -d \
  --name athlete-service \
  -p 8000:8000 \
  -e DB_HOST=your-db-host \
  -e DB_PASSWORD=your-secure-password \
  athlete-service:latest
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the API documentation at `/docs`

## 🔄 Version History

- **v1.0.0**: Initial release with basic CRUD operations
- Features: Athlete management, health checks, async database operations 