#!/usr/bin/env python3

import logging
import os
import sys
import time
import tweepy

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
    
    return logging.getLogger()

def get_api(consumer_key: str, consumer_secret: str, access_token: str, access_token_secret: str):
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    return tweepy.API(auth, wait_on_rate_limit=True)

def get_last_id(api) -> str:
    last_tweets = api.home_timeline(count=1)
    
    if not len(last_tweets):
        return '1119952223906217984'

    while len(last_tweets):
        last_tweet = last_tweets[0]
        in_reply_id = last_tweet.in_reply_to_status_id_str
        if in_reply_id:
            return in_reply_id

        last_tweets = api.home_timeline(count=1, max_id=last_tweet.id-1)

    return last_tweet.id_str

def check_phrase(phrase: str) -> bool:
    return True

def is_tweet_exists(api, tweet_id):
    try:
        tweet = api.get_status(tweet_id)
        return True
    except (Exception, tweepy.TweepError) as error:
        return False

def main():
    consumer_key, consumer_secret, access_token_key, access_token_secret, search_query, status_text = read_config()
    
    logger = get_logger()
    try:
        api = get_api(consumer_key, consumer_secret, access_token_key, access_token_secret)
    except (Exception, tweepy.TweepError) as error:
        logger.exception("received an error on getting API")
        sys.exit(1)

    while True:
        try:
            tweet_id = get_last_id(api)
            tweets = sorted(tweepy.Cursor(api.search, q=f'{search_query} -filter:retweets', tweet_mode='extended', since_id=tweet_id).items(), key=lambda x: x.id_str)
        except (Exception, tweepy.TweepError) as error:
            logger.exception("received an error on getting search results")
            sys.exit(1)

        for tweet in tweets:
            try:
                if is_tweet_exists(api, tweet.id):
                    api.update_status(f'@{tweet.author.screen_name} {status_text}', in_reply_to_status_id=tweet.id_str)
                    logger.info(f'replied to https://twitter.com/{tweet.author.screen_name}/status/{tweet.id_str}')
            except (Exception, tweepy.TweepError) as error:
                logger.exception("received an error on trying to reply")
                sys.exit(1)

        time.sleep(30)


if __name__ == "__main__":
    main()
