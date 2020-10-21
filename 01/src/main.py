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
    def __init__(self, meeting_n=None, voting_n=None, url=None, response=None):
        if meeting_n is not None:
            self.meeting_n = meeting_n
            self.voting_n = voting_n
            soup = BeautifulSoup(response.text, 'html.parser')
            results_tag = soup.find_all('ul', class_='results')
            try:
                self.overall_df = pd.read_html(response.text)[1]
            except:
                self.overall_df = pd.DataFrame(columns=["Party", 'N. repr.', 'A', 'N', '0', 'Z', 'M'])
            self.overall_df.columns = ["Party", 'N. repr.', 'A', 'N', '0', 'Z', 'M']
            self.overall_df = self.overall_df.assign(Meeting=self.meeting_n)
            self.overall_df = self.overall_df.assign(Proposal=self.voting_n)
            self.df = pd.DataFrame(columns=['Name', 'Party', 'Vote', 'Meeting', 'Proposal'])
            for party in results_tag:
                party_name = str(party.previous_sibling.contents[0].next)[:-2]
                for member in party:
                    row = pd.Series(data={'Name': member.contents[2].string, "Party": party_name,
                                          "Vote": member.contents[0].string, 'Meeting': meeting_n,
                                          'Proposal': voting_n})
                    self.df = self.df.append(row, ignore_index=True)

    def load(self, filename):
        uscore_pos = str(filename).find('_')
        dash_pos = str(filename).find('-')
        dot_pos = str(filename).find('.')
        pos = 0
        if dash_pos < 0:
            pos = uscore_pos
        else:
            pos = dash_pos
        self.meeting_n = int(str(filename)[:pos])
        self.voting_n = int(str(filename)[pos + 1:dot_pos])
        uscorefile = str(self.meeting_n) + '_' + str(self.voting_n) + '.csv'
        dashfile = str(self.meeting_n) + '-' + str(self.voting_n) + '.csv'
        ban = ''
        if dash_pos < 0:
            ban = dashfile
        else:
            ban = uscorefile
        self.df = pd.read_csv('../data/' + uscorefile)
        self.overall_df = pd.read_csv('../data/' + dashfile)
        return ban

    def save(self):
        print('Saving: m: ' + str(self.meeting_n) + ' p: ' + str(self.voting_n))
        members_file = '../data2/' + str(self.meeting_n) + '_' + str(self.voting_n) + '.csv'
        party_file = '../data2/' + str(self.meeting_n) + '-' + str(self.voting_n) + '.csv'
        self.df.to_csv(members_file, index=False)
        self.overall_df.to_csv(party_file, index=False)


def main():
    meetings = fetch_meetings()
    results_meetings, vote_links = split_meetings(meetings)
    meeting_n = 0
    results_meetings.to_csv('results.csv', index=False)
    unsuccessful_urls = open('../url.txt', 'a')
    for meeting in vote_links:
        meeting_n += 1
        if meeting_n == 21:
            meeting_n += 1
        for voting_number in meeting:
            url = URL_PREFIX + meeting[voting_number]
            print(url)
            try:
                response = requests.get(url)
            except:
                unsuccessful_urls.write("\n")
                unsuccessful_urls.write(url)
                continue
            proposal = CProposal(meeting_n, voting_number, url, response)
            proposal.save()


def fetch_meetings():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0'
    })
    retries = Retry(total=10,
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
