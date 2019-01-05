#!/usr/bin/env python3
import argparse

import requests
import re
from bs4 import BeautifulSoup


def get_soup(req):
    return BeautifulSoup(req.content, 'html.parser')


def find_translation(content):
    pattern = re.compile(r'.*(\/du\/verbe\/[a-z]+\.php).*')
    for line in content.split():
        match = pattern.match(line)
        if match:
            return 'http://la-conjugaison.nouvelobs.com/' + match.group(1)

    return None


def get_tense_divs(soup):
    tenses = {}
    for div in soup.find_all('div', attrs={'class': 'tempstab'}):
        tense = div.find('h3').text.strip().lower()
        if tense not in tenses: # To avoid gerondif
            tenses[tense] = div

    return tenses


def fetch_verb(verb):
    es_url = "http://la-conjugaison.nouvelobs.com/espagnol/verbe/" + verb + ".php"
    es_req = requests.get(es_url)

    fr_url = find_translation(str(es_req.content))
    if fr_url is None:
        return None, None
    fr_req = requests.get(fr_url)

    es_soup = get_soup(es_req)
    fr_soup = get_soup(fr_req)

    es_verbs = get_tense_divs(es_soup)
    fr_verbs = get_tense_divs(fr_soup)

    return es_verbs, fr_verbs


def tie_languages(es_lang, fr_lang, tenses=['présent']):
    tie = {}
    for tense in tenses:
        if tense in es_lang and tense in fr_lang:
            tie[tense] = (es_lang[tense], fr_lang[tense])
        elif tense not in es_lang:
            print('es: Missing ' + tense)
            print(es_lang.keys())
        elif tense not in fr_lang:
            print('fr: Missing ' + tense)
            print(fr_lang.keys())

    return tie


def format_body(body):
    body = body.replace('<div class="tempscorps">', '').replace('</div>', '')
    body = body.replace('<b>', '').split('</b><br/>')

    return list(filter(lambda s: len(s), body))


def get_conjugaison(tied_languages):
    for tense, (es_lang, fr_lang) in tied_languages.items():
        print('### ' + tense)

        es_body = str(es_lang.find('div', attrs={'class': 'tempscorps'}))
        fr_body = str(fr_lang.find('div', attrs={'class': 'tempscorps'}))

        for es, fr in zip(format_body(es_body), format_body(fr_body)):
            yield es, fr, tense


def write_languages(file_obj, tenses, verbs):
    tags = ['nouvelobs', 'conjugaison']

    for verb in verbs:
        print('# ' + verb)

        es_lang, fr_lang = fetch_verb(verb)
        if fr_lang is None:
            print('Translation not found!')
            continue

        tie = tie_languages(es_lang, fr_lang, tenses=tenses)
        for es, fr, tense in get_conjugaison(tie):
            if verb in ('ser', 'estar'):
                fr = '{} ({})'.format(fr, verb)


            print('{} -> {}'.format(es, fr))
            file_obj.write('"{}","{}","{}"\n'.format(
                es,
                fr,
                ' '.join(tags + [verb, tense])
            ))



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-tenses', nargs='+',
                        default=[
                            'présent',
                            'futur simple',
                            'imparfait'
                        ])
    parser.add_argument('-verbs', nargs='+', required=True)
    parser.add_argument('-csv', default='deck.csv')

    args = parser.parse_args()
    with open(args.csv, "w+") as file_obj:
        write_languages(file_obj, args.tenses, args.verbs)
