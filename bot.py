import tweepy
import logging
import time
import requests
import psycopg2
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Authenticate to Twitter
auth = tweepy.OAuthHandler("d3B6f3n4RWGSyLIAJTkKh4clg",
                           "WTsGQHKz5eYa98ICf2FzNuYOz2zc2QD18nabyUOlOsMFtS2t5w")
auth.set_access_token("1301947389096407040-tiDUae2T2EBakKZHrmGEpfNQB4ItvU",
                      "exMKdrFKcFZLBA9gqOUXlQsOOeJXMGoCOmYp2i0fMDVAL")

# Create API object
api = tweepy.API(auth)

try:
    api.verify_credentials()
    print("Authentication OK")
except:
    print("Error during authentication")


def check_mentions(api, keywords, since_id):
    statuses = api.mentions_timeline()
    print(str(len(statuses)) + " number of statuses have been mentioned")
    logger.info("Retrieving mentions")
    new_since_id = since_id
    for tweet in tweepy.Cursor(api.mentions_timeline,
                               since_id=since_id).items():
        new_since_id = max(tweet.id, new_since_id)
        if tweet.in_reply_to_status_id is not None:
            print(tweet.text.lower())

            if any(keyword in tweet.text.lower() for keyword in keywords):
                logger.info(f"Answering to {tweet.user.name}")
                splitted_tweet_text = tweet.text.lower().split()
                last_word = splitted_tweet_text[-1]

                if not tweet.user.following:
                    tweet.user.follow()

                api.update_status(
                    status="Categorized tweet by: @" + tweet.user.screen_name,
                    in_reply_to_status_id=tweet.id,
                )

                try:
                    print("Connecting to database...")
                    conn = psycopg2.connect(
                    user="postgres",
                    password="bdsjhbsdj",
                    host="localhost",
                    port=5432,
                    database="twitter_organizer"
                )
                    #tweet to categorize
                    tweet_to_categorize = api.get_status(tweet.in_reply_to_status_id)
                    text_to_categorize = tweet_to_categorize._json.get('text')
                    user_to_categorize = tweet_to_categorize._json.get('user').get('name')
                    user_screen_name_to_categorize = tweet_to_categorize._json.get('user').get('screen_name')
                    date_to_categorize = tweet_to_categorize._json.get('created_at')

                    # cursor
                    cursor = conn.cursor()

                    data_send = {'user': user_to_categorize,'user_screen_name': user_screen_name_to_categorize,'category': last_word,
                             'content': text_to_categorize, 'date': date_to_categorize}

                    cursor.execute("INSERT INTO tweet_organized (tweet_organized_content, tweet_organized_category, tweet_organized_date, user_name, user_screen_name) VALUES (%s,%s,%s,%s,%s) RETURNING tweet_organized_content",
                     (data_send.get('content'), data_send.get('category'), data_send.get('date'), data_send.get('user'), data_send.get('user_screen_name')))

                    inserted_data = cursor.fetchone()[0]

                    conn.commit()

                    cursor.close()

                except (Exception, psycopg2.DatabaseError) as error:
                    print(error)

    return new_since_id


def main():
    since_id = 1
    while True:
        since_id = check_mentions(api, ["categorize"], since_id)
        logger.info("Waiting...")
        time.sleep(60)


if __name__ == "__main__":
    main()
