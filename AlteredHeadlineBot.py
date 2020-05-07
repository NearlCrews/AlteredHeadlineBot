# Import everything.
import praw
import configparser
import requests
from bs4 import BeautifulSoup
import re
import difflib
import sqlite3
import os.path
import time

# Read the configuration.
config = configparser.ConfigParser()
config.read('settings.ini')
reddit_user = config['alteredheadlinebot']['reddit_user']
reddit_pass = config['alteredheadlinebot']['reddit_pass']
reddit_client_id = config['alteredheadlinebot']['reddit_client_id']
reddit_client_secret = config['alteredheadlinebot']['reddit_client_secret']
reddit_target_subreddit = config['alteredheadlinebot']['reddit_target_subreddit']
score_threshold = int(config['alteredheadlinebot']['score_threshold'])
bot_owner = config['alteredheadlinebot']['bot_owner']
leave_post_comment = config['alteredheadlinebot']['leave_post_comment']
leave_mod_notice = config['alteredheadlinebot']['leave_mod_notice']
link_to_rule = config['alteredheadlinebot']['link_to_rule']

# Regex list of domains to ignore.
drop_urls = re.compile('(?:.*bloomberg\.com.*|.*reddit\.com.*|.*redd\.it.*|.*imgur\.com.*|.*youtube\.com.*|.*wikipedia\.org.*|.*twitter\.com.*|.*youtu\.be.*|.*facebook\.com.*|.*michigan\.gov.*)', re.IGNORECASE)

# Regex for URL validity.
valid_url = re.compile('(?:^http.*)', re.IGNORECASE)

# Create the tracking database.
conn = sqlite3.connect('BotCache.db')
c = conn.cursor()
# id = auto-incrementing value.
# epoch = timestamp.
# postid = the internal Reddit post ID.
# username = the username of the poster.
# submitted_title = the title given to the post by the user.
# submitted_url = the URL posted by the user.
# real_title = the website's title of the article. Please not that they sometimes get changed by the editor.
# reddit_permalink = the link to the post on Reddit.
conn.execute('''CREATE TABLE IF NOT EXISTS alteredheadlinebot
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
        epoch INTEGER,
        postid TEXT,
        username TEXT,
        submitted_title TEXT,
        submitted_url TEXT,
        real_title TEXT,
        reddit_permalink TEXT);''')

# Create the Reddit object.
reddit = praw.Reddit(
    username=reddit_user,
    password=reddit_pass,
    client_id=reddit_client_id,
    client_secret=reddit_client_secret,
    user_agent='AlteredHeadlineBot managed by u/{}'.format(bot_owner)
)

# Start the streaming loop for new submissions.
while True:
  for submission in reddit.subreddit(reddit_target_subreddit).stream.submissions():
    try:
      # Ignore self-posts and cross-posts:
      if submission.is_self or submission.num_crossposts > 0:
        continue
     
      # Check to see if we've already checked this one.
      c.execute("SELECT id FROM alteredheadlinebot WHERE postid = ?", (submission.id,))
      query_result = c.fetchall()
      if len(query_result) != 0:
        continue

      # Ensure it starts with http*
      if not valid_url.match(submission.url):
        continue

      # Get rid of certain domains that are known to fail.
      if drop_urls.match(submission.url):
        continue

      # Find the real title from the actual HTML.
      headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'}
      real_url_request = requests.get(submission.url, headers=headers, timeout=5)
      html_content = real_url_request.text
      soup = BeautifulSoup(html_content, 'html.parser')
      # Check to make sure we get a real value and remove any extra characters.
      if type(soup.title) == type(None):
        continue
      else:
        real_title = soup.title.string.strip()
      # Ignore short URL titles since the website isn't returning a title.
      if len(real_title) <= 16:
        continue

      # Convert to lowercase and identify similarity.
      similarity_object = difflib.SequenceMatcher(None, submission.title.lower(), real_title.lower())
      similarity = round(similarity_object.ratio()*100)
      # DEBUG
      print(f'Username: {submission.author} \nSubmitted URL: {submission.url} \nPost Title: {submission.title} \nActual Title: {real_title} \nSimilarity: {similarity} \n')
      if (similarity >= score_threshold):
        continue

      # Send an alert if the title differs significantly.
      if similarity <= score_threshold and leave_mod_notice == 'True':
        # DEGUG
        n_link = '[Link to post for review.]({})\n\n'.format(submission.permalink)
        n_posted = '**Posted Title:** {}\n\n'.format(submission.title)
        n_actual = '**Actual Title:** {}\n\n'.format(real_title)
        n_similarity = '**Similarity:** {}%\n\n'.format(similarity)
        n_footer = '\n\n*Please contact u/{} if this bot is misbehaving.*\n\n'.format(bot_owner)
        notification = n_actual + n_posted + n_similarity + n_link + n_footer
        reddit.subreddit(reddit_target_subreddit).message('Potentially Altered Headline', notification)

      # Leave a comment in the thread.
      if similarity <= score_threshold and leave_post_comment == 'True':
        # DEGUG
        r_message = 'Hello u/{}!\n\n The title of your post differs from the actual article title and has been flagged for review. Please review {} in the r/{} subreddit rules. If this is an actual rule violation, you can always delete the submission and resubmit with the correct headline. Otherwise, this will likely be removed by the moderators. Please note that some websites change their article titles and this may be a false-positive. In that case, no further action is required. Further details: \n\n'.format(submission.author, link_to_rule, reddit_target_subreddit)
        n_posted = '**Posted Title:** {}\n\n'.format(submission.title)
        n_actual = '**Actual Title:** {}\n\n'.format(real_title)
        n_similarity = '**Similarity:** {}%\n\n'.format(similarity)
        n_footer = '\n\n*Please contact u/{} if this bot is misbehaving.*\n\n'.format(bot_owner)
        comment_text = r_message + n_posted + n_actual + n_similarity + n_footer
        post_submission = reddit.submission(id=submission.id)
        this_comment = post_submission.reply(comment_text)
        this_comment.mod.distinguish(how='yes')

      # Insert into the database.
      epoch = time.time()
      c.execute("INSERT INTO alteredheadlinebot (epoch, postid, username, submitted_title, submitted_url, real_title, reddit_permalink) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (int(epoch), str(submission.id), str(submission.author), str(submission.title), str(submission.url), str(real_title), str(submission.permalink)))
      conn.commit()
    except:
      continue

# Close the DB connection.
conn.close()
