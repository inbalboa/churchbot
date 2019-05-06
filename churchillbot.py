#!/usr/bin/env python3

import logging
import logging.handlers
import os
import sys
import time
import tweepy


class TlsSMTPHandler(logging.handlers.SMTPHandler):
    def __init__(self, *args, app_name: str = None, **kwargs):
        super(TlsSMTPHandler, self).__init__(*args, **kwargs)
        self.app_name = app_name

    def emit(self, record):
        try:
            import smtplib
            from email.utils import formatdate
            
            port = self.mailport
            if not port:
                port = smtplib.SMTP_PORT
            smtp = smtplib.SMTP(self.mailhost, port)
            msg = self.format(record)
            msg = f'Content-Type: text/html;charset=utf-8\nFrom: {self.fromaddr}\nTo: {",".join(self.toaddrs)}\nSubject: {self.app_name}: {self.getSubject(record)}\nDate: {formatdate()}\n\n{msg}'

            if self.username:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(self.username, self.password)
            smtp.sendmail(self.fromaddr, self.toaddrs, msg.encode('utf8'))
            smtp.quit()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

def read_config() -> dict:
    config = dict()
    
    config['app_name'] = os.environ.get('app_name', sys.argv[0])
    config['app_fullname'] = os.environ.get('app_fullname', config['app_name'])
    
    config['consumer_key'] = os.environ.get('consumer_key', None)
    config['consumer_secret'] = os.environ.get('consumer_secret', None)
    config['access_token_key'] = os.environ.get('access_token_key', None)
    config['access_token_secret'] = os.environ.get('access_token_secret', None)
    
    config['search_query'] = os.environ.get('search_query', None)
    config['status_text'] = os.environ.get('status_text', None)
    
    config['mail_address'] = os.environ.get('mail_address', None)
    config['mail_password'] = os.environ.get('mail_password', None)
    
    return config

def get_logger(log_path: str = None, mail_address: str = None, mail_password: str = None, app_name: str = None) -> logging.Logger:
    logger = logging.getLogger(app_name)
    logger.setLevel(logging.DEBUG)
    
    base_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.DEBUG)
    sh.setFormatter(base_formatter)
    logger.addHandler(sh)
    
    if log_path:
        fh = logging.FileHandler(log_path)
        fh.setLevel(logging.INFO)
        fh.setFormatter(base_formatter)
        logger.addHandler(fh)

    if mail_address and mail_password:
        mh1 = TlsSMTPHandler(('smtp.gmail.com', 587), mail_address, (mail_address), '✔️ new reply', (mail_address, mail_password), app_name=app_name)
        mh1.setLevel(logging.INFO)
        mh1.setFormatter(logging.Formatter('%(message)s'))
        mh1.addFilter(type('', (logging.Filter,), {'filter': staticmethod(lambda r: r.levelno == logging.INFO)}))
        logger.addHandler(mh1)

        mh2 = TlsSMTPHandler(('smtp.gmail.com', 587), mail_address, (mail_address), '⚠️ error found', (mail_address, mail_password), app_name=app_name)
        mh2.setLevel(logging.ERROR)
        mh2.setFormatter(base_formatter)
        logger.addHandler(mh2)

    return logger

def get_api(consumer_key: str, consumer_secret: str, access_token: str, access_token_secret: str) -> tweepy.API:
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
    # TODO: smart checking
    return True

def is_tweet_exists(api: tweepy.API, tweet_id: int) -> bool:
    try:
        tweet = api.get_status(tweet_id)
        return True
    except (Exception, tweepy.TweepError) as error:
        return False

def main():
    config = read_config()    
    logger = get_logger(mail_address=config['mail_address'], mail_password=config['mail_password'], app_name=config['app_fullname'])

    try:
        api = get_api(config['consumer_key'], config['consumer_secret'], config['access_token_key'], config['access_token_secret'])
    except (Exception, tweepy.TweepError) as error:
        logger.exception('received an error on getting API')
        sys.exit(1)

    new_last_id = True
    while True:
        try:
            if new_last_id:
                tweet_id = get_last_id(api)
                new_last_id = False
            tweets = sorted(tweepy.Cursor(api.search, q=f'{config["search_query"]} -filter:retweets', tweet_mode='extended', since_id=tweet_id).items(), key=lambda x: x.id_str)
        except (Exception, tweepy.TweepError) as error:
            logger.exception('received an error on getting search results')
            sys.exit(1)

        for tweet in tweets:
            try:
                if is_tweet_exists(api, tweet.id):
                    api.update_status(f'@{tweet.author.screen_name} {config["status_text"]}', in_reply_to_status_id=tweet.id_str)
                    logger.info(f'replied to https://twitter.com/{tweet.author.screen_name}/status/{tweet.id_str}')
                    new_last_id = True
            except (Exception, tweepy.TweepError) as error:
                logger.exception('received an error on trying to reply')
                sys.exit(1)

        time.sleep(600)


if __name__ == '__main__':
    main()
