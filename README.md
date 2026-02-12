# Multilingual Mandi Challenge Platform

A revolutionary web-based trading platform that empowers local Indian vendors through AI-driven price discovery and cross-language negotiation tools. The platform bridges language barriers and facilitates transparent, efficient trade across India's diverse linguistic landscape.

## Features

- **Multilingual Support**: Native support for 10 Indian languages (Hindi, English, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi)
- **AI-Powered Price Discovery**: Real-time market price analysis with location, seasonality, and quality considerations
- **Cross-Language Negotiations**: Intelligent negotiation assistance with cultural context awareness
- **Voice Interface**: Speech-to-text and text-to-speech capabilities for accessibility
- **Mobile-First Design**: Optimized for smartphones with intuitive, large-button interfaces
- **Cultural Adaptation**: Regional customs and communication style adaptation
- **Real-Time Market Data**: Live pricing, availability, and market trend information
- **Secure Transactions**: End-to-end encryption and comprehensive audit trails

## Technology Stack

- **Backend**: FastAPI with Python 3.11+
- **Database**: PostgreSQL with Redis caching
- **Search**: Elasticsearch for multilingual product search
- **NLP**: iNLTK and Indic NLP Library for Indian language processing
- **Real-time**: WebSocket connections for live negotiations
- **Testing**: Pytest with Hypothesis for property-based testing

## Quick Start

### Prerequisites

- Python 3.11 or higher
- PostgreSQL 14+
- Redis 6+
- Elasticsearch 8+

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd multilingual-mandi-platform
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e ".[dev]"
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Initialize the database:
```bash
alembic upgrade head
```

6. Start the development server:
```bash
mandi-server dev
```

The API will be available at `http://localhost:8000` with interactive documentation at `http://localhost:8000/docs`.

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=mandi_platform

# Run only unit tests
pytest -m unit

# Run only property-based tests
pytest -m property

# Run integration tests
pytest -m integration
```

### Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint code
flake8 src/ tests/
mypy src/

# Run pre-commit hooks
pre-commit run --all-files
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Architecture

The platform follows a microservices architecture with the following core components:

- **API Gateway**: FastAPI application handling routing and authentication
- **Translation Service**: Real-time multilingual translation with cultural context
- **Price Discovery Engine**: ML-powered market price analysis and recommendations
- **Negotiation Assistant**: AI-driven negotiation facilitation and mediation
- **Cultural Context Engine**: Regional adaptation and communication style management
- **Product Catalog**: Elasticsearch-powered multilingual product search
- **User Management**: Authentication, authorization, and profile management

## API Documentation

Interactive API documentation is available at `/docs` when running the development server. The API follows RESTful conventions with additional WebSocket endpoints for real-time features.

### Key Endpoints

- `POST /auth/login` - User authentication
- `GET /products/search` - Multilingual product search
- `POST /translations/translate` - Real-time text translation
- `GET /prices/current/{product_id}` - Current market price
- `WS /negotiations/{session_id}` - Real-time negotiation chat

## Configuration

The application uses environment variables for configuration. Key settings include:

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `ELASTICSEARCH_URL`: Elasticsearch cluster URL
- `SECRET_KEY`: JWT signing secret
- `GOOGLE_TRANSLATE_API_KEY`: Google Translate API key
- `SUPPORTED_LANGUAGES`: Comma-separated list of language codes

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support and questions, please contact the development team or open an issue on the repository.

## Acknowledgments

- iNLTK team for Indian language NLP capabilities
- Indic NLP Library contributors
- FastAPI and Pydantic communities
- Local Indian vendors who inspired this platform