# Daily digest

Our task tracker is a web app in which small teams assign each other tasks and discuss them in comments. Users miss what changes whilst they're away, so we want to email each of them once a day about what concerns them: the tasks assigned to them since their last digest, their tasks that are due in the next two days, and the comments that mention them.

## Requirements

- Each digest arrives at around 8:00 in the user's time zone, as set in their profile, give or take 15 minutes.
- Nobody gets more than one digest a day, even if something fails halfway through.
- Nobody gets a digest on a day when there's nothing to tell them.
- Users can turn the digest off in their settings, or with one click from any digest.
- The email links to each task and comment, rather than copying what they say, so that a forwarded digest reveals as little as possible.

## Scale

- 180,000 users today, spread over 140 time zones. We expect 500,000 within two years.
- About 60% of users will keep the digest on.

## What we already run

Everything runs in one AWS account, in the `eu-west-1` region:

- The web app and its API, on Amazon ECS.
- Amazon RDS for PostgreSQL, which holds the users, tasks, and comments.
- Amazon SQS, for the web app's background jobs.
- Amazon SES, which sends our sign-up and password reset emails.
- Amazon CloudWatch, for logs, metrics, and alarms.
