import time
import requests
from bs4 import BeautifulSoup
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import pandas as pd
import seaborn as sns
import os
import html5lib
import lxml
import numpy as np

URL_PREFIX = 'https://www.psp.cz/sqw/'


class CProposal:
    def __init__(self, meeting_n=None, voting_n=None, url=None):
        if meeting_n is not None:
            self.meeting_n = meeting_n
            self.voting_n = voting_n
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            results_tag = soup.find_all('ul', class_='results')
            self.df = pd.DataFrame(columns=['Name', 'Party', 'Vote', 'Mtg n.', 'Proposal n.'])
            for party in results_tag:
                party_name = str(party.previous_sibling.contents[0].next)[:-2]
                for member in party:
                    row = pd.Series(data={'Name': member.contents[2].string, "Party": party_name,
                                          "Vote": member.contents[0].string, 'Mtg n.': meeting_n,
                                          'Proposal n.': voting_n})
                    self.df = self.df.append(row, ignore_index=True)

    def load(self, filename):
        dash_pos = str(filename).find('_')
        dot_pos = str(filename).find('.')
        self.meeting_n = int(str(filename)[:dash_pos])
        self.voting_n = int(str(filename)[dash_pos + 1:dot_pos])
        self.df = pd.read_csv('../data/' + filename)

    def save(self):
        members_file = '../data/' + str(self.meeting_n) + '_' + str(self.voting_n) + '.csv'
        self.df.to_csv(members_file, index=False)


def main():
    save_data()
    # meetings = load_data()
    # df = merge(meetings)
    # attendance(df)
    # transfers(df)
    # party_match(df)
    # party_unity(df)


def merge(meetings):
    df = pd.DataFrame(columns={'Name', 'Party', 'Vote', 'Mtg n.', 'Proposal n.'})
    for meeting in meetings:
        for proposal in meeting:
            df = df.append(proposal.df)
    return df


def transfers(df):
    pass


def attendance(df):
    ax = sns.countplot(x='Name', data=df)
    pass


def party_match(meetings):
    pass


def party_unity(meetings):
    pass


def load_data():
    meetings = [[]] * 61
    directory = '../data'
    ban = []
    for file in os.scandir(directory):
        proposal = CProposal()
        ban.append(proposal.load(file.name))
        meetings[proposal.meeting_n].append(proposal)

    return meetings


def save_data():
    meetings = fetch_meetings()
    results_meetings, vote_links = split_meetings(meetings)
    meeting_n = 0
    results_meetings.to_csv('results', index=False)
    for meeting in vote_links:
        meeting_n += 1
        for voting_number in meeting:
            url = URL_PREFIX + meeting[voting_number]
            print(url)
            proposal = CProposal(meeting_n, voting_number, url)
            proposal.save()


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
            page_url = table_url[:len(table_url) - 1] + str(i)
            print(page_url)
            response = requests.get(page_url)
            try:
                all_votings_results = all_votings_results.append(pd.read_html(response.text)[0])
            except:
                break
            vote_links = links_from_vote(vote_links, response)
        meetings_vote_links.append(vote_links)
    all_votings_results['Výsledek'] = all_votings_results['Výsledek'].map({'Přijato': 1, "Zamítnuto": 0})
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
