import tweepy
import logging
import time
import requests
import psycopg2
import uuid
from config import config
import psycopg2.extras
import json
import time
import math

psycopg2.extras.register_uuid()

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
    logger.info("Retrieving mentions")
    new_since_id = since_id
    for tweet in tweepy.Cursor(api.mentions_timeline,
                               since_id=since_id, tweet_mode='extended').items():
        new_since_id = max(tweet.id, new_since_id)
        if tweet.in_reply_to_status_id is not None:
           
            tweet_json = tweet._json
           
            
            if any(keyword in tweet.full_text.lower() for keyword in keywords):
                logger.info(f"Answering to {tweet.user.name}")
                splitted_tweet_text = tweet.full_text.lower().split()
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

                    list_of_tweets_to_categorize = []
                    text_to_categorize = []
                    text_to_categorize_dict = {}
                    test_list = []
                    #tweet to categorize
                    tweet_to_categorize = api.get_status(tweet._json['in_reply_to_status_id'], tweet_mode='extended')
                    list_of_tweets_to_categorize.append(tweet_to_categorize)
                    text_to_categorize.append(tweet_to_categorize._json.get('full_text'))
                    text_to_categorize_dict['text'] = tweet_to_categorize._json.get('full_text')
                    text_to_categorize_dict['id'] = tweet_to_categorize._json.get('id')
                    test_list.append(text_to_categorize_dict)

                    #Get user object
                    user_object = api.get_user(tweet_to_categorize._json.get('in_reply_to_user_id_str'))
                    user_object_name_to_categorize = user_object._json.get('name')
                    user_object_screen_name_to_categorize = user_object._json.get('screen_name')
                    user_object_image_url_to_categorize = user_object._json.get('profile_image_url_https')
                    user_to_categorize = tweet_to_categorize._json.get('user').get('name')
                    user_screen_name_to_categorize = tweet_to_categorize._json.get('user').get('screen_name')
                    date_to_categorize = tweet_to_categorize._json.get('created_at')
                    
                    if(tweet_to_categorize.in_reply_to_status_id is not None):
                        new_tweet = api.get_status(tweet_to_categorize._json['in_reply_to_status_id'], tweet_mode='extended')
                        while True:
                            text_to_categorize_dict_loop = {}
                            list_of_tweets_to_categorize.append(new_tweet)
                            text_to_categorize.append(new_tweet._json.get('full_text') + "\n")
                            text_to_categorize_dict_loop['text'] = new_tweet._json.get('full_text') + "\n"
                            text_to_categorize_dict_loop['id'] = new_tweet._json.get('id')
                            test_list.append(text_to_categorize_dict_loop)
                
                            if new_tweet.in_reply_to_status_id is None:
                                text_to_categorize_dict_loop_1 = {}
                                list_of_tweets_to_categorize.append(new_tweet)
                                text_to_categorize.append(new_tweet._json.get('full_text'))
                                text_to_categorize_dict_loop_1['text'] = new_tweet._json.get('full_text') + "\n"
                                text_to_categorize_dict_loop_1['id'] = new_tweet._json.get('id')
                                test_list.append(text_to_categorize_dict_loop_1)
                                break
                            new_tweet = api.get_status(new_tweet._json['in_reply_to_status_id'], tweet_mode='extended')


                    # cursor
                    cursor = conn.cursor()

                    reversedcontent = list(reversed(text_to_categorize))
                    del reversedcontent[0]

                    reversed_list_dict = list(reversed(test_list))
                    del reversed_list_dict[0]


                    final_text = []
                    for text in reversedcontent:
                        text += "\n"
                        final_text.append(text)

                    final_text_dict = []
                    for dict_item in reversed_list_dict:
                        dict_item['text'] += "\n"
                        final_text_dict.append(dict_item)
                    
                    json_final_dict = json.dumps(final_text_dict)

                    data_send = {'user': user_object_name_to_categorize,'user_screen_name': user_object_screen_name_to_categorize, 'user_image_url': user_object_image_url_to_categorize,'category': last_word,
                             'content': json_final_dict, 'date': date_to_categorize}
                    new_tweet_uuid = uuid.uuid4()
                    cursor.execute("INSERT INTO tweet_organized (tweet_organized_id, tweet_organized_content, tweet_organized_category, tweet_organized_date, user_name, user_screen_name, user_image_url) VALUES (%s, ARRAY[%s]::json[],%s,%s,%s,%s,%s) RETURNING tweet_organized_content;",
                     (new_tweet_uuid, data_send.get('content'), data_send.get('category'), data_send.get('date'), data_send.get('user'), data_send.get('user_screen_name'), data_send.get('user_image_url')))
                    #Create new twitter user if not exists, otherwise append to existing array
                    cursor.execute(
                        """
                        INSERT INTO twitter_user (id, tweets_organized) 
                        VALUES (%s, ARRAY[%s])
                        ON CONFLICT (id) DO UPDATE 
                        SET tweets_organized = array_append(twitter_user.tweets_organized, %s) WHERE ((twitter_user.id)::text = %s::text)
                        RETURNING *;
                        """,
                    (data_send.get('user_screen_name'),new_tweet_uuid, new_tweet_uuid , data_send.get('user_screen_name')))

                    #Create new category user if not exists, otherwise do nothing
                    cursor.execute(
                        """
                        INSERT INTO categories (id, is_default, created_at, name)
                        VALUES (%s, false ,%s, %s)
                        ON CONFLICT (id) DO NOTHING
                        RETURNING *;
                        """, (
                            data_send.get("category").lower(), int(time.time()), data_send.get("category").capitalize())
                    )

                    # print(cursor.fetchone())
                    

                    # inserted_data = cursor.fetchone()[0]

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
