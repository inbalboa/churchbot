#!/usr/bin/env python3

import logging
import os
import sys
import tweepy

app_name = 'church_bot'

def read_config() -> tuple:
    consumer_key = os.environ.get('consumer_key', None)
    consumer_secret = os.environ.get('consumer_secret', None)
    access_token_key = os.environ.get('access_token_key', None)
    access_token_secret = os.environ.get('access_token_secret', None)
    search_query = os.environ.get('search_query', None)
    status_text = os.environ.get('status_text', None)
    
    return consumer_key, consumer_secret, access_token_key, access_token_secret, search_query, status_text

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

def get_last_id() -> str:
    return os.environ.get('last_id', '1117855342552133637')

def set_last_id(tweet_id: str):
    return os.environ.set(tweet_id)

def check_phrase(phrase: str) -> bool:
    return True

def main():
    consumer_key, consumer_secret, access_token_key, access_token_secret, search_query, status_text = read_config()
    
    logger = get_logger()
    api = get_api(consumer_key, consumer_secret, access_token_key, access_token_secret)

    tweet_id = get_last_id()
    try:
        tweets = sorted(tweepy.Cursor(api.search, q=search_query, tweet_mode='extended', since_id=tweet_id).items(), key=lambda x: x.id_str)
    except (Exception, tweepy.TweepError) as error:
        logger.error(error)
        sys.exit(1)

    for tweet in tweets:
        try:
            api.update_status(f'@{tweet.author.screen_name} {status_text}', in_reply_to_status_id=tweet.id_str)
            set_last_id(tweet.id_str)
            logger.info(f'replied to https://twitter.com/{tweet.author.screen_name}/status/{tweet.id_str}')
        except (Exception, tweepy.TweepError) as error:
            logger.error(error)
            sys.exit(1)


if __name__ == "__main__":
    main()
