#!/usr/bin/env python3

from ast import literal_eval
import logging
import logging.handlers
import operator
import os
import sys
import time
import tweepy


class TlsSMTPHandler(logging.handlers.SMTPHandler):
    def __init__(self, *args, app_name: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_name = app_name

    def emit(self, record):
        try:
            import smtplib
            from email.utils import formatdate

            port = self.mailport
            if not port:
                port = smtplib.SMTP_PORT
            smtp = smtplib.SMTP(self.mailhost, port)
            msg = f'Content-Type: text/plain;charset=utf-8\nFrom: {self.fromaddr}\nTo: {",".join(self.toaddrs)}\nSubject: {self.app_name}: {self.getSubject(record)}\nDate: {formatdate()}\n\n{self.format(record)}'

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
    app_name = os.environ.get('app_name', '.'.join(sys.argv[0].split('.')[:-1]))
    config = {
        'app_name': app_name,
        'app_fullname': os.environ.get('app_fullname', app_name),

        'consumer_key': os.environ.get('consumer_key'),
        'consumer_secret': os.environ.get('consumer_secret'),
        'access_token_key': os.environ.get('access_token_key'),
        'access_token_secret': os.environ.get('access_token_secret'),

        'search_query': os.environ.get('search_query'),
        'status_text': literal_eval(os.environ.get('status_text')),

        'mail_address': os.environ.get('mail_address'),
        'mail_password': os.environ.get('mail_password')
    }

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
    last_tweets = api.user_timeline(screen_name=api.me().screen_name, count=1)

    if not last_tweets:
        return '1119999999999999999'

    while last_tweets:
        last_tweet = last_tweets[0]
        in_reply_id = last_tweet.in_reply_to_status_id_str
        if in_reply_id:
            return in_reply_id

        last_tweets = api.home_timeline(count=1, max_id=last_tweet.id-1)

    return last_tweet.id_str

def check_phrase(phrase: str) -> bool:
    # TODO: smart checking
    return True

def tweet_exists(api: tweepy.API, tweet_id: int) -> bool:
    try:
        api.get_status(tweet_id)
        return True
    except:
        return False

def main():
    config = read_config()
    logger = get_logger(mail_address=config['mail_address'], mail_password=config['mail_password'], app_name=config['app_fullname'])

    api = get_api(config['consumer_key'], config['consumer_secret'], config['access_token_key'], config['access_token_secret'])
    last_tweet_id = get_last_id(api)
    tweets = tweepy.Cursor(api.search, q=f'{config["search_query"]} -filter:retweets', tweet_mode='extended', since_id=last_tweet_id)
    for tweet in sorted(tweets.items(), key=operator.attrgetter('id_str')):
        status_text = config['status_text'].get(tweet.lang)
        if status_text and tweet_exists(api, tweet.id):
            reply = api.update_status(f'@{tweet.author.screen_name} {status_text}', in_reply_to_status_id=tweet.id_str)
            logger.info(f'new reply https://twitter.com/{reply.author.screen_name}/status/{reply.id_str}\n{reply.text}\n\nto https://twitter.com/{tweet.author.screen_name}/status/{tweet.id_str}\n{tweet.full_text}')


if __name__ == '__main__':
    main()

