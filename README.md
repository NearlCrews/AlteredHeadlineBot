# AlteredHeadlineBot
A PRAW Reddit bot to check for editorialized and altered headlines. 

# Summary
This simple Reddit PRAW bot is designed for a specific purpose:
1. Check the "real" headline of a Reddit post against the submitted headline.
2. Compare the two to check if the difference exceeds a configurable value between 0-100.
3. Alert the moderators of the subreddit so they can review the submission. 
4. Leave an optional comment on the post. 

Be gentle. I've never written anything in Python and I'm sure there are more efficient ways of doing everything. This was a "COVID-19 I'm bored" learning project. Either way, it seems to work as expected and we're receiving actionable information.

# Installation
Install the required modules:
```
pip3 install --upgrade configparser bs4 praw
```

You want to plug the correct values into `settings.ini`. They're fairly simple:
```
[alteredheadlinebot]
 # Bot username and password, or use your own.
 reddit_user =
 reddit_pass =
 # Create the secret OATH values. Instructions on Reddit.
 reddit_client_id =
 reddit_client_secret =
 # Subreddit to monitor, e.g. Michigan.
 reddit_target_subreddit =
 # Score for how "different" the topic and submissions are. High number = more identical. From 0-100.
 score_threshold = 50
 # Bot owner. This is typically your username. Don't add the u/ in front of the name.
 bot_owner =
 # Set to true if you'd like the bot to leave a comment on the post.
 # You'll need to edit the message in the Python script.
 leave_post_comment = True
 # Set to true if you'd like a mod notice sent to the subreddit.
 leave_mod_notice = True
```

You then simply run the bot:
`python3 AlteredHeadlineBot.py`

I run it in `screen` since I'm ususlly watching the ouput. It'll also write the processed events to a local database so it's not sending repeat alerts if it needs to reprocess. 

**Sample Output:**
```
Username: XXXXX
Stripped URL: https://www.mlive.com/public-interest/2020/04/michigan-greenhouses-garden-centers-submit-may-1-reopening-plan-to-governor.html
Post Title: Michigan greenhouses, garden centers submit May 1 reopening plan to governor
Actual Title: Michigan greenhouses, garden centers submit May 1 reopening plan to governor - mlive.com
Similarity: 93

Username: XXXXX
Stripped URL: https://www.spinalcolumnonline.com/articles/oakland-county-now-offering-drive-thru-covid-19-testing/
Post Title: Oakland country now offering drive-thru testing. Phone screening required.
Actual Title: Oakland County now offering drive-thru COVID-19 testing | The Spinal Column
Similarity: 74

Username: XXXXX
Stripped URL: https://www.independent.co.uk/news/world/americas/coronavirus-michigan-girl-dies-protest-lockdown-skylar-herbert-a9475216.html
Post Title: Five-year-old daughter of Michigan emergency workers dies of coronavirus as residents continue to protest lockdown
Actual Title: Five-year-old daughter of Michigan emergency workers dies of coronavirus as residents continue to protest lockdown | The Independent
Similarity: 93

Username: XXXXX
Stripped URL: https://www.thedailybeast.com/devos-has-deep-ties-to-michigan-protest-group-but-is-quiet-on-tactics
Post Title: DeVos Has Deep Ties to Michigan Protest Group, But Is Quiet On Tactics
Actual Title: DeVos Has Deep Ties to Michigan Protest Group, But Is Quiet On Tactics
Similarity: 100
```

**Sample Mod Notification:**
```
Actual Title: Finley: How to do business, and stay safe

Posted Title: Autocam Medical has instituted rigorous precautions to protect worker safety

Similarity: 36%

Link to post for review.

Please contact u/{bot_owner} if this bot is misbehaving.
```

**Sample Comment Notification:**
```
Hello u/{username}!

The title of your post differs from the actual article title and has been flagged for review. Please review Rule #6 
in the r/Michigan subreddit rules. If this is an actual rule violation, you can always delete the submission and 
resubmit with the correct headline. Otherwise, this will likely be removed by the moderators. Please note that 
some websites change their article titles and this may be a false-positive. In that case, no further action is 
required. Further details:

Posted Title: TESTING 123 TESTING 123 TESTING 123

Actual Title: Lions' fourth-round pick Logan Stenberg cites 'nastiness' as one of his best traits

Similarity: 24%

Please contact u/{botowner} if this bot is misbehaving.
```
