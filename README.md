# E-commerce Analytics Platform

A comprehensive analytics platform for e-commerce data using the Olist dataset. This platform provides deep insights into customer behavior, sales patterns, and operational efficiency through advanced analytics and machine learning.

![Platform Overview](docs/images/platform-overview.png)

## 🌟 Features

### Customer Analytics

- Customer Lifetime Value (CLV) calculation
- RFM-based customer segmentation
- Cohort analysis and retention tracking
- Churn prediction using machine learning

### Sales Analytics

- Real-time sales monitoring dashboard
- Sales forecasting with multiple models
- Product performance analysis
- Market basket analysis

### Operational Analytics

- Seller performance metrics
- Inventory optimization
- Delivery time analysis
- Order processing efficiency

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL 13+
- Redis 6+
- Docker & Docker Compose

### Installation

1. Clone the repository:

```bash
https://github.com/data-jeong/ecommerce-analytics.git
cd ecommerce-analytics
```

2. Download the Olist dataset and place it in `data/raw/`.

3. Set up environment variables:

```bash
cp .env.example .env
# Edit .env with your configurations
```

4. Start services using Docker Compose:

```bash
docker-compose up -d
```

5. Install dependencies:

```bash
pip install -r requirements.txt
```

6. Run database migrations:

```bash
python manage.py migrate
```

## 🧪 Testing

Run all tests:

```bash
make test
```

Run specific test categories:

```bash
make test-unit        # Unit tests
make test-integration # Integration tests
make test-e2e        # End-to-end tests
```

## 📊 Database Schema

### OLTP Database (PostgreSQL)

- `users`: User management and authentication
- `api_keys`: API key management
- `audit_logs`: System audit logging
- `rate_limits`: API rate limiting

### OLAP Database

- Materialized views for analytics
- Optimized for complex queries
- Automated refresh mechanisms

For detailed schema information, see [Database Documentation](docs/database.md).

## 🏗️ Project Structure

```
ecommerce_analytics/
├── api/                 # API endpoints
├── core/               # Core business logic
├── data/               # Data management
│   ├── raw/           # Raw data files
│   └── processed/     # Processed data
├── docs/               # Documentation
├── tests/              # Test suite
└── utils/              # Utility functions
```

## 🔄 CI/CD Pipeline

Our GitHub Actions pipeline includes:

- Automated testing
- Code quality checks
- Security scanning
- Docker image building
- Automated deployment

See [CI/CD Documentation](docs/ci.md) for details.

## 📚 Documentation

- [API Documentation](docs/api.md)
- [Analytics Methods](docs/analytics.md)
- [Deployment Guide](docs/deployment.md)
- [Security Guide](docs/security.md)
- [Performance Guide](docs/performance.md)
- [Contributing Guide](docs/contributing.md)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](docs/contributing.md) for details.

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Olist](https://olist.com/) for providing the dataset
- [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/olistbr/brazilian-ecommerce)

## ToDO 
- [ ] K8s
