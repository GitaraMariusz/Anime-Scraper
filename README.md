# Anime-Scraper
The project is designed for scraping anime from MAL with simple UI 

1. Copy the repository
```txt
git clone https://github.com/GitaraMariusz/Anime-Scraper-Kubernetes.git
```
2. Log in to docker
```txt
docker login
```
3. Build the images
```txt
docker build -t docker-username/scraper:latest -f Dockerfile.scraper .
docker build -t docker-username/flask-app:latest -f Dockerfile .      
```
4. Push to docker
```txt
docker push docker-username/scraper:latest         
docker push docker-username/flask-app:latest
```
5. Start minikube
```txt
minikube start
```
6. Creating catalog for Redis
```txt
minikube ssh
sudo mkdir -p /mnt/data/redis
sudo chmod 777 /mnt/data/redis
exit
```
7. Apply the yaml's
```txt
minikube kubectl -- apply -f scraper-service.yaml    
minikube kubectl -- apply -f flask-app-deployment.yaml    
minikube kubectl -- apply -f redis-deployment.yaml  
minikube kubectl -- apply -f scraper-deployment.yaml 
minikube kubectl -- apply -f redis-service.yaml      
```
8. Get url
```txt
minikube kubectl -- get pods
```
9. Get url
```txt
minikube service flask-app-service  
```



