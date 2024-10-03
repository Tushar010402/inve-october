
# Multi-Tenant Inventory & Surveillance SaaS Platform

## Overview

This project is a Multi-Tenant Inventory & Surveillance SaaS Platform designed for retail businesses. It integrates CCTV cameras with AI-based YOLOv8 models for real-time product tracking, anomaly detection, and automated inventory management.

## File Structure

- `app.py`: Main FastAPI application file. Contains route definitions, database connection logic, and integrates core services. It handles tenant registration, product tracking, anomaly detection, and licensing.
- `services.py`: Contains core service functions for product tracking, anomaly detection, and licensing. It includes functions for validating licenses, tracking products, and detecting anomalies.
- `db_utils.py`: Utility functions for database operations, including sharded database connections. It manages connection pools for each shard and provides functions to get database connections based on tenant IDs.
- `architecture_diagram.puml`: PlantUML file for generating the architecture diagram. It visually represents the system architecture, including components and their interactions.
- `README.md`: This documentation file. Provides an overview of the project, setup instructions, and deployment guidelines.

## Running Locally

### Prerequisites

- Python 3.8+
- PostgreSQL 14.13
- FastAPI
- psycopg
- psycopg_pool

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd multi_tenant_inventory
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up PostgreSQL: Create a database and configure connection strings in `app.py`.

4. Run the FastAPI server:
   ```bash
   uvicorn multi_tenant_inventory.app:app --reload
   ```

5. Access the API at `http://localhost:8000`.

## Third-Party Keys or Accounts

- AWS S3: Required for video storage. Configure your AWS credentials and bucket details in the application.

## Database Setup

### Local

1. Start PostgreSQL server.
2. Create the necessary tables using the SQL commands in `app.py`.

### Server

1. Deploy PostgreSQL on your server. Ensure it's accessible by the application.
2. Run the same SQL commands to create tables.

## Deployment

### Google Cloud

1. Containerize the application using Docker.
2. Deploy the container to Google Cloud Run or Google Kubernetes Engine.
3. Set up a managed PostgreSQL instance on Google Cloud SQL.
4. Configure environment variables and secrets for database connections and AWS credentials.

## Production Readiness

- Ensure all environment variables are set for production.
- Use a production-ready database with proper scaling and backup configurations.
- Implement logging and monitoring for the application.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
