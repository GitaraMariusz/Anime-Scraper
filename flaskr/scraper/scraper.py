import asyncio
import aiohttp
import logging
from bs4 import BeautifulSoup
import random
import redis
import json
import os
from flask import Flask, request

logging.basicConfig(level=logging.DEBUG)

redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_client = redis.StrictRedis(host=redis_host, port=6379, db=0, decode_responses=True)

app = Flask(__name__)

async def fetch(url, session):
    try:
        async with session.get(url, timeout=10) as response:
            if response.status != 200:
                logging.error(f"Failed to retrieve {url}")
                return None
            return await response.text()
    except Exception as e:
        logging.error(f"Exception occurred while fetching {url}: {e}")
        return None

async def fetch_all(urls, session):
    tasks = [fetch(url, session) for url in urls]
    return await asyncio.gather(*tasks)

async def fetch_anime_details(anime_page_url, session):
    try:
        html = await fetch(anime_page_url, session)
        if html is None:
            return {'synopsis': 'N/A', 'image_url': 'N/A', 'genres': []}

        soup = BeautifulSoup(html, 'html.parser')
        synopsis_tag = soup.select_one('p[itemprop="description"]')
        synopsis = synopsis_tag.text.strip() if synopsis_tag else 'N/A'
        image_tag = soup.select_one('img[itemprop="image"]')
        image_url = image_tag['data-src'] if image_tag else 'N/A'
        genre_tags = soup.select('div.spaceit_pad span[itemprop="genre"] ~ a')
        genres = [genre_tag.text.strip() for genre_tag in genre_tags]

        return {'synopsis': synopsis, 'image_url': image_url, 'genres': genres}
    except Exception as e:
        logging.error(f"Exception occurred while fetching details from {anime_page_url}: {e}")
        return {'synopsis': 'N/A', 'image_url': 'N/A', 'genres': []}

async def parse_anime_page(html_content, session):
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    anime_entries = soup.find_all('tr', class_='ranking-list')
    anime_list = []

    detail_tasks = []

    for anime in anime_entries:
        title_tag = anime.find('h3', class_='anime_ranking_h3')
        title = title_tag.text.strip() if title_tag else 'N/A'

        score_tag = anime.find('span', class_='score-label')
        user_score = score_tag.text.strip() if score_tag else 'N/A'

        rank_tag = anime.find('span', class_='top-anime-rank-text')
        rank = rank_tag.text.strip() if rank_tag else 'N/A'

        aired_tag = anime.find('div', class_='information di-ib mt4')
        episodes = 'N/A'
        aired_date = 'N/A'
        members = 'N/A'
        anime_type = 'N/A'

        if aired_tag:
            aired_info = aired_tag.text.strip()
            if 'TV (' in aired_info:
                anime_type = 'TV'
            elif 'Movie (' in aired_info:
                anime_type = 'Movie'
            elif 'OVA (' in aired_info:
                anime_type = 'OVA'
            elif 'Special (' in aired_info:
                anime_type = 'Special'
            elif 'ONA (' in aired_info:
                anime_type = 'ONA'

            if '(' in aired_info and 'eps)' in aired_info:
                start = aired_info.find('(') + 1
                end = aired_info.find('eps)')
                episodes_str = aired_info[start:end].strip()
                try:
                    episodes = int(episodes_str)
                except ValueError:
                    logging.error(f"Invalid episode count: {episodes_str}")
                    episodes = 0

            if 'members' in aired_info:
                parts = aired_info.split(' ')
                members_str = parts[-2].replace(',', '')
                try:
                    members = int(members_str)
                except ValueError:
                    logging.error(f"Invalid members count: {members_str}")
                    members = 0
                aired_date = ' '.join(parts[:-2]).strip()
            else:
                aired_date = aired_info

            if 'TV (' in aired_date or 'Movie (' in aired_date or 'OVA (' in aired_date or 'Special (' in aired_date or 'ONA (' in aired_date:
                aired_date = aired_date.split(')', 1)[1].strip()

        anime_page_url_tag = anime.find('a', class_='hoverinfo_trigger fl-l ml12 mr8')
        anime_page_url = anime_page_url_tag['href'] if anime_page_url_tag else None

        if anime_page_url:
            detail_tasks.append(fetch_anime_details(anime_page_url, session))
        else:
            detail_tasks.append(asyncio.Future())
            detail_tasks[-1].set_result({'synopsis': 'N/A', 'image_url': 'N/A', 'genres': []})

        anime_details = {
            'title': title,
            'user_score': float(user_score) if user_score != 'N/A' else 0,
            'rank': int(rank) if rank != 'N/A' else 0,
            'episodes': episodes,
            'aired_date': aired_date,
            'members': members,
            'type': anime_type,
            'genres': [],
            'anime_page_url': anime_page_url,
            'synopsis': 'N/A',
            'image_url': 'N/A'
        }

        anime_list.append(anime_details)

    details_list = await asyncio.gather(*detail_tasks)

    for anime, details in zip(anime_list, details_list):
        if details is None:
            logging.error(f"No details fetched for {anime['title']}")
            details = {'synopsis': 'N/A', 'image_url': 'N/A', 'genres': []}
        anime.update(details)

    return anime_list

async def scrape_anime_list(num_pages, start_page=0):
    base_url = "https://myanimelist.net/topanime.php?limit="
    urls = [base_url + str(page * 50) for page in range(start_page, start_page + num_pages)]

    async with aiohttp.ClientSession() as session:
        anime_list = []
        for i in range(0, len(urls), 5):  # Fetch in batches of 5
            current_urls = urls[i:i + 5]
            html_pages = await fetch_all(current_urls, session)
            tasks = [parse_anime_page(html, session) for html in html_pages if html]
            results = await asyncio.gather(*tasks)
            for result in results:
                anime_list.extend(result)
            
            if i + 5 < len(urls):
                await asyncio.sleep(random.uniform(5, 10))  

    return anime_list

def get_start_page():
    total_titles = redis_client.hlen("anime")
    if total_titles == 0:
        return 0
    return (total_titles // 50)  

def get_anime_list(num_pages):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    start_page = get_start_page()
    scraped_anime = loop.run_until_complete(scrape_anime_list(num_pages, start_page))
    
    for anime in scraped_anime:
        title = anime['title']
        if not redis_client.hexists("anime", title):
            redis_client.hset("anime", title, json.dumps(anime))
    
    return scraped_anime

@app.route('/trigger_scrape', methods=['POST'])
def trigger_scrape():
    num_pages = int(request.form.get('num_pages', 1))
    start_page = get_start_page()
    anime_list = asyncio.run(scrape_anime_list(num_pages, start_page))

    for anime in anime_list:
        title = anime['title']
        if not redis_client.hexists("anime", title):
            redis_client.hset("anime", title, json.dumps(anime))

    return {"status": "success", "message": "Scraping completed"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
