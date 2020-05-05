# Import everything.
import praw
import configparser
import requests
from bs4 import BeautifulSoup
import re
import difflib
import furl
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
conn = sqlite3.connect('PostHistory.db')
c = conn.cursor()
# id = auto-incrementing value.
# epoch = timestamp.
# postid = the internal Reddit post ID.
# username = the username of the poster.
# posttitle = the title given to the post by the user.
# posturl = the URL posted by the user.
# strippedurl = the posturl minus any variables at the end, e.g. ?FBID=12345.
# urltitle = the website's title of the article. Please not that they sometimes get changed by the editor.
# redditurl = the link to the post on Reddit.
conn.execute('''CREATE TABLE IF NOT EXISTS alteredheadlinebot
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
        epoch INTEGER,
        postid TEXT,
        username TEXT,
        posttitle TEXT,
        posturl TEXT,
        strippedurl TEXT,
        urltitle TEXT,
        redditurl TEXT);''')

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
      # Get the ID.
      post_id = submission.id
      if type(post_id) == type(None):
        continue

      # Check to see if we've already checked this one.
      c.execute("SELECT id FROM alteredheadlinebot WHERE postid = ?", (post_id,))
      query_result = c.fetchall()
      if len(query_result) != 0:
        continue

      # Username section and error checking.
      username = submission.author
      if type(username) == type(None):
        continue

      # Title section and error checking.
      post_title = submission.title
      if type(post_title) == type(None):
        continue

      # Post URL and error checking.
      post_url = submission.url
      if type(post_url) == type(None):
        continue
      if not valid_url.match(post_url):
        continue

      # Create a stripped URL for report checking.
      stripped_url = furl.furl(post_url).remove(args=True, fragment=True).url

      # Get rid of certain domains that are known to fail.
      if drop_urls.match(post_url):
        continue

      # Find the real title from the actual HTML.
      headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'}
      real_url_request = requests.get(post_url, headers=headers, timeout=5)
      html_content = real_url_request.text
      soup = BeautifulSoup(html_content, 'html.parser')
      if type(soup.title) == type(None):
        continue
      else:
        url_title = soup.title.string.strip()
      if len(url_title) <= 16:
        continue

      # Convert to lowercase and identify similarity.
      similarity_object = difflib.SequenceMatcher(None, post_title.lower(), url_title.lower())
      similarity = round(similarity_object.ratio()*100)
      # DEBUG
      print(f'Username: {username} \nStripped URL: {stripped_url} \nPost Title: {post_title} \nActual Title: {url_title} \nSimilarity: {similarity} \n')
      if (similarity >= score_threshold):
        continue

      # Send an alert if the title differs significantly.
      if similarity <= score_threshold and leave_mod_notice == 'True':
        n_link = '[Link to post for review.]({})\n\n'.format(submission.permalink)
        n_posted = '**Posted Title:** {}\n\n'.format(post_title)
        n_actual = '**Actual Title:** {}\n\n'.format(url_title)
        n_similarity = '**Similarity:** {}%\n\n'.format(similarity)
        n_footer = '\n\n*Please contact u/{} if this bot is misbehaving.*\n\n'.format(bot_owner)
        notification = n_actual + n_posted + n_similarity + n_link + n_footer
        reddit.subreddit(reddit_target_subreddit).message('Potentially Altered Headline', notification)

      # Leave a comment in the thread.
      if similarity <= score_threshold and leave_post_comment == 'True':
        r_message = 'Hello u/{}!\n\n The title of your post differs from the actual article title and has been flagged for review. Please review {} in the r/{} subreddit rules. If this is an actual rule violation, you can always delete the submission and resubmit with the correct headline. Otherwise, this will likely be removed by the moderators. Please note that some websites change their article titles and this may be a false-positive. In that case, no further action is required. Further details: \n\n'.format(username, link_to_rule, reddit_target_subreddit)
        n_posted = '**Posted Title:** {}\n\n'.format(post_title)
        n_actual = '**Actual Title:** {}\n\n'.format(url_title)
        n_similarity = '**Similarity:** {}%\n\n'.format(similarity)
        n_footer = '\n\n*Please contact u/{} if this bot is misbehaving.*\n\n'.format(bot_owner)
        comment_text = r_message + n_posted + n_actual + n_similarity + n_footer
        post_submission = reddit.submission(id=post_id)
        this_comment = post_submission.reply(comment_text)
        this_comment.mod.distinguish(how='yes')

      # Insert into the database.
      epoch = time.time()
      c.execute("INSERT INTO alteredheadlinebot (epoch, postid, username, posttitle, posturl, strippedurl, urltitle, redditurl) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (int(epoch), str(post_id), str(username), str(post_title), str(post_url), str(stripped_url), str(url_title), str(submission.permalink)))
      conn.commit()
    except:
      continue

conn.close()
