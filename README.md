# Anime-Scraper
The project is designed for scraping anime from MAL with simple UI
![Index.html](https://github.com/GitaraMariusz/Anime-Scraper/blob/main/index.png?raw=true)  

1. Copy the repository
```txt
git clone https://github.com/GitaraMariusz/Anime-Scraper.git
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
6. Apply the yaml's
```txt
minikube kubectl -- apply -f scraper-service.yaml    
minikube kubectl -- apply -f flask-app-deployment.yaml    
minikube kubectl -- apply -f redis-deployment.yaml  
minikube kubectl -- apply -f scraper-deployment.yaml       
```
7. Get url
```txt
minikube service flask-app-service  
```



