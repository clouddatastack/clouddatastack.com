# dataspaces  

## compile  
curl -sSL https://install.python-poetry.org | python3 -  
poetry shell  
poetry run sphinx-build -E -b html src docs


## TODO
- Storage - Iceberg, Delta or Parquet
- Add Kafka konfiguration with terraform for AWS MKS
- Add section about algorythms an relevant data structures and design patterns
- Maintanance of DataLake (Optimize queries, monitor usage and others)
- Write-Audit-Publish with Slim CI
- Write baout Prefect templitize of the projects
- fastai usercase

Add services:
- PII Tracer 

Youtube videos:  
- DLT for API integration (Salesforce, google analytics)
- Modern airflow (scrape videos + experience)
- DBT (scripts and metadata)
- duckdb pipelines