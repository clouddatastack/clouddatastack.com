# dataspaces  

## compile  
curl -sSL https://install.python-poetry.org | python3 -  
poetry shell  
poetry run sphinx-build -E -b html src docs


## TODO
- Storage - Iceberg, Delta or Parquet
- Add Kafka konfiguration with terraform for AWS MKS