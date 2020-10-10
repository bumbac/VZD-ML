import time
import requests
from bs4 import BeautifulSoup
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import pandas as pd
import html5lib
import lxml
import numpy as np

URL_PREFIX = 'https://www.psp.cz/sqw/'


def main():
    meetings = fetch_meetings()
    # results_meetings, vote_links = split_meetings(meetings)
    file = open('OUT.txt', "w")
    file.write(str(split_meetings(meetings)))
    file.close()


def fetch_meetings():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0'
    })
    retries = Retry(total=5,
                    backoff_factor=1,
                    status_forcelist=[429, 500, 502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))

    url = URL_PREFIX + 'hlasovani.sqw?o=8'
    response = session.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')
    meetings = []
    for tr in table.findAllNext('tr'):
        try:
            meetings.append(URL_PREFIX + tr.find('td').find('a')['href'])
        except:
            pass
    return meetings


def split_meetings(meetings):
    all_votings_results = pd.DataFrame
    init_dfs_flag = True
    meetings_vote_links = []
    for mtg_url in meetings:
        response = requests.get(mtg_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        vote_log = soup.find(id='main-content')
        table_url = URL_PREFIX + vote_log.find_next('a')['href']
        response = requests.get(table_url)
        # initiate table
        vote_links = {}
        if init_dfs_flag:
            all_votings_results = pd.read_html(response.text)[0]
            vote_links = links_from_vote(vote_links, response)

        for i in range(1, 100):
            if init_dfs_flag:
                init_dfs_flag = False
                continue
            page_url = table_url[:len(table_url)-1] + str(i)
            print(page_url)
            response = requests.get(page_url)
            try:
                all_votings_results = all_votings_results.append(pd.read_html(response.text)[0])
            except Exception:
                break
            vote_links = links_from_vote(vote_links, response)
        meetings_vote_links.append(vote_links)

    return all_votings_results, meetings_vote_links


def links_from_vote(vote_links, response):
    soup = BeautifulSoup(response.text, 'html.parser')
    starting_point = soup.find('table')
    for link in starting_point.findAllNext('a'):
        if not str(link['href']).startswith('hlasy'):
            continue
        else:
            vote_links[link.text] = link['href']
    return vote_links


if __name__ == '__main__':
    main()
