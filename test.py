import requests
import json

requests.get('http://127.0.0.1:8080/info/google', json={'id': 'google', 'key': 'google', 'url': 'https://bing.com'})