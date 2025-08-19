import requests

url = "http://127.0.0.1:8080/api/ask"
data = {"question": "Что такое Вечный Крестовый поход?"}

response = requests.post(url, json=data)
print(response.json())
