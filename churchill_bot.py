#!/usr/bin/env python3

import argparse
import configparser
import logging
import pathlib
import sys
import tweepy

app_name = 'church_bot'

def parse_args() -> tuple:
    parser = argparse.ArgumentParser(description='Churchill twitter bot')
    parser.add_argument('--config_file', type=str, help='Config file', default=f'{pathlib.Path.home()}/.config/{app_name}.cfg')
    args = parser.parse_args()
    return args

def read_config(config_file: str) -> tuple:
    config = configparser.ConfigParser()
    config.read(config_file)
    
    secret_section = config['SECRETS']
    consumer_key = secret_section.get('consumer_key', None)
    consumer_secret = secret_section.get('consumer_secret', None)
    access_token_key = secret_section.get('access_token_key', None)
    access_token_secret = secret_section.get('access_token_secret', None)
    
    files_section = config['FILES']
    log_path = files_section.get('log_path', None)
    state_file = files_section.get('state_file', f'{pathlib.Path.home()}/.local/share/{app_name}/{app_name}.state')
    
    text_section = config['TEXT']
    search_query = text_section.get('search_query', None)
    status_text = text_section.get('status_text', None)
    
    return consumer_key, consumer_secret, access_token_key, access_token_secret, log_path, state_file, search_query, status_text

def get_logger(log_path: str=None, verbose: bool=True):
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_path:
        handlers.append(logging.FileHandler(log_path))
    
    logging.basicConfig(level=logging.INFO if verbose else logging.WARNING, format='%(asctime)s [%(levelname)-5.5s]  %(message)s', handlers=handlers)
    
    return logging.getLogger(app_name)

def get_api(consumer_key: str, consumer_secret: str, access_token: str, access_token_secret: str):
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    return tweepy.API(auth)

def get_last_id(state_file: str) -> str:
    result = None
    try:
        with open(state_file) as file:
            array_state = [row.strip() for row in file]
            if len(array_state):
                result = array_state[0]
    except FileNotFoundError:
        pass

    return result if result else '1114964897769623553'

def set_last_id(state_file: str, tweet_id: str):
    with open(state_file, 'w') as file:
        file.write(tweet_id)
        
def check_phrase(phrase: str) -> bool:
    return True

def main():
    parsed_args = parse_args()

    consumer_key, consumer_secret, access_token_key, access_token_secret, log_path, state_file, search_query, status_text = read_config(parsed_args.config_file)
    
    logger = get_logger(log_path)
    api = get_api(consumer_key, consumer_secret, access_token_key, access_token_secret)

    tweet_id = get_last_id(state_file)
    try:
        tweets = sorted(tweepy.Cursor(api.search, q=search_query, tweet_mode='extended', since_id=tweet_id).items(), key=lambda x: x.id_str)
    except (Exception, tweepy.TweepError) as error:
        logger.error(error)
        sys.exit(1)

    for tweet in tweets:
        try:
            api.update_status(f'@{tweet.author.screen_name} {status_text}', in_reply_to_status_id=tweet.id_str)
            set_last_id(state_file, tweet.id_str)
            logger.info(f'replied to https://twitter.com/{tweet.author.screen_name}/status/{tweet.id_str}')
        except (Exception, tweepy.TweepError) as error:
            logger.error(error)
            sys.exit(1)


if __name__ == "__main__":
    main()
