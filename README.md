# Anime-Scraper

The project is designed for scraping anime from MAL with a simple UI.

## Installation Instructions

1. **Clone the Repository**
    ```sh
    git clone https://github.com/GitaraMariusz/Anime-Scraper-Kubernetes.git
    ```
    **Note:** After cloning, it is recommended to delete all GitHub-related files as they can disturb the workflow of the application.

2. **Log in to Docker**
    ```sh
    docker login
    ```

3. **Build the Docker Images**
    ```sh
    docker build -t <docker-username>/scraper:latest -f Dockerfile.scraper .
    docker build -t <docker-username>/flask-app:latest -f Dockerfile .
    ```

4. **Push the Docker Images**
    ```sh
    docker push <docker-username>/scraper:latest
    docker push <docker-username>/flask-app:latest
    ```

5. **Start Minikube**
    ```sh
    minikube start
    ```

6. **Create Catalog for Redis**
    ```sh
    minikube ssh
    sudo mkdir -p /mnt/data/redis
    sudo chmod 777 /mnt/data/redis
    exit
    ```

7. **Apply the YAML Files**
    Before applying the YAML files, make sure to change 'username' to your Docker Hub username in `flask-app-deployment.yaml` and `scraper-deployment.yaml`.
    ```sh
    minikube kubectl -- apply -f scraper-service.yaml
    minikube kubectl -- apply -f flask-app-deployment.yaml
    minikube kubectl -- apply -f redis-deployment.yaml
    minikube kubectl -- apply -f scraper-deployment.yaml
    minikube kubectl -- apply -f redis-service.yaml
    ```

8. **Check status of the Pods**
    ```sh
    minikube kubectl -- get pods
    ```

9. **Access the Flask App Service**
    ```sh
    minikube service flask-app-service
    ```

## Usage

Once all the services are up and running, you can access the Flask app through the URL provided by Minikube.

## 
