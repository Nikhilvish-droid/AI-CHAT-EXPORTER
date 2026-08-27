import requests


def html_fetcher(url:str):
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})

    return{
        "status_code":response.status_code,
        "data":response.text[:100]
    }