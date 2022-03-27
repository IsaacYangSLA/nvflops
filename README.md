# nvflops
The **N**ew **V**ersion of the **F**ree-style machine-**L**earning **O**pen **P**latform **S**ystem

# Key concepts

- All results from participants are recorded with mandatory metadata, such as parents, creator, creator's role.
- Blobs of results (the large binary information) are stored in S3 or other dedicate blob storage space.  Their addresses (bucket and object in S3 use case) are stored in the mandatory metadata.
- Parents and children are many-to-many relationship.  That is, one result can have multiple parents (aggregation operation).  One parents can have multiple results (client's local training).
- Results can include additional metadata (custom_field) as flat dictionary.  Search can perform against those custom_field.

Aggregation style operation as shown in this graph.
![alt text](https://github.com/IsaacYangSLA/nvflops/blob/main/docs/resources/key_concepts.png?raw=true)

# Package requirements
In current implementation, vflops requires a blob storage space and only S3 is supported.  Full S3 authentication with AWS IAM credential will be implemented in the future.  For local development and test, you can install [minio][https://min.io/download#/linux).  Minio Python package is required, but it should be easy to replace it with boto3.

The backend database can be any SQL database supported by SQLAlchemy.  However, you will need to setup your own database management system.

# Installation
We plan to have nvflops wheel package available on [PyPi](https://pypi.org/project/nvflops/).  You can choose to install via source codes.

  ```
  pip install -e .
  ```
  in nvflops folder (same level as setup.py)
