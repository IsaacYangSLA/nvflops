# nvflops
The **N**ew **V**ersion of the **F**ree-style machine-**L**earning **O**pen **P**latform **S**ystem

# Key concepts

- All results from participants are recorded with mandatory metadata, such as parents, creator, creator's role.
- Blobs of results (the large binary information) are stored in S3 or other dedicate blob storage space.  Their addresses (bucket and object in S3 use case) are stored in the mandatory metadata.
- Parents and children are many-to-many relationship.  That is, one result can have multiple parents (aggregation operation).  One parents can have multiple results (client's local training).
- Results can include additional metadata (custom_field) as flat dictionary.  Search can perform against those custom_field.

Aggregation style operation as shown in this graph.
![alt text](https://github.com/IsaacYangSLA/nvflops/blob/main/key_concepts.png?raw=true)
