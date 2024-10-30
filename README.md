# Microservice-2

This is a Microservice-2, a component of the project designed to interact with an AWS RDS PostgreSQL database.

## SSH into the EC2 Instance: (VSCode)

```bash
ssh -i "<path_to_key>\coms4153_key_pair.pem" ec2-user@ec2-34-196-69-206.compute-1.amazonaws.com
```

## Setting Up SSH Authentication for GitHub Access on EC2

* SSH Authentication: Generate an SSH key, add it to GitHub, and use the SSH URL to clone.

### Generate an SSH Key (on an EC2 instance)

* Run the following command on the EC2 instance to generate an SSH key pair:
    ```bash
    ssh-keygen -t rsa -b 4096 -C "username@email.com"
    ```
    * A public key has been saved in /home/ec2-user/.ssh/id_rsa.pub

* [GitHub SSH and GPG keys settings](https://github.com/settings/keys). 
* Click on `New SSH key`
* Paste public key stored in `~/.ssh/id_rsa.pub` into the "Key" field and save it.

* Clone the Repository Using SSH
    ```bash
    git clone git@github.com:Clouc-Computing/microservice-2.git
    ```

## Database Connection

* [PostgreSQL Database Connection Guide](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_GettingStarted.CreatingConnecting.PostgreSQL.html#CHAP_GettingStarted.Connecting.PostgreSQL)

    ```bash
    sudo yum install postgresql15
    psql --version
    ````

* To connect to the PostgreSQL RDS instance, use the following command:

    ```bash
    psql --host=microservice-2-database.chaomk0okau3.us-east-1.rds.amazonaws.com --port=5432 --dbname=postgres --username=postgres
    ```

## Sprint 2

### Initial Setup
* Initial Setup
    ```bash
    sudo yum install python3 -y
    python3 -m venv .venv
    source .venv/bin/activate
    ```
    * Added `.venv/` to `.gitignore` 

    ```bash
    python3 -m pip install --upgrade pip
    pip3 install -r requirements.txt
    ```
    
* After installing any python packages:
    ```bash
    pip3 freeze > requirements.txt
    ```

### PostgreSQL
* [PostgreSQL Commands](https://www.postgresql.org/docs/current/sql-commands.html)
    ```bash
    CREATE DATABASE microservice_db;
    CREATE USER microservice_user WITH PASSWORD 'dbuserdbuser';
    GRANT ALL PRIVILEGES ON DATABASE microservice_db TO microservice_user;
    ```


### Run and Test the Microservice
* Start the microservice on a specific port, which can be accessed by:  
    ```bash
    http://127.0.0.1:5000
    ````

* Check if the microservice connects to the PostgreSQL database correctly by accessing the endpoint (e.g., /data) in a browser or using `curl` or `Postman`.


## OpenAPI Documentation
* Created a OpenAPI Documentation for CRUD Operations (e.g. GET, POST, PUT, DELETE) with descriptions on SwaggerHub  
    [OpenAPI Documentation](https://app.swaggerhub.com/apis/SL5036/COMS4153-Project-OpenAPI-Documentation/1.0)
    

## Part 1: REST Interface with Database Access
1. All Methods on All Paths:
    * The code provides the complete set of HTTP methods:
        * GET for retrieving items and individual item details.
        * POST for creating new items.
        * PUT for updating an item asynchronously.
        * DELETE for deleting items.

2. Pagination:
    * The `GET /items` endpoint includes pagination support with page and per_page parameters.

3. Query Parameters:
    * The `GET /items` endpoint allows filtering items by name using the name query parameter.

4. 201 Created with a Link Header for POST:
    * The `POST /items` endpoint creates a new item and returns 201 Created with a Location header pointing to the newly created resource.

5. 202 Accepted and Implementing an Asynchronous Update to a URL:
    * The `PUT /items/<item_id>` endpoint accepts an update request and starts an asynchronous thread to update the item’s description, returning 202 Accepted.

6. Good Response Codes and Error Responses:
    * The code includes appropriate response codes and error handling:
        * 201 for successful creation.
        * 202 for accepted asynchronous updates.
        * 404 for not found resources.
        * 400 for bad requests.
    * Custom error handlers provide JSON-formatted responses for 404 and 400 errors.

7. Link Sections:
    * The `GET /items` endpoint includes a Link header for pagination, providing a link to the next page of results if available.





