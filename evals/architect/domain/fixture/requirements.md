# Offline notes

Jotter's mobile app only works whilst it's online: it loads the user's notes from the server when it opens, and saves each edit straight back. Users on the Underground or on a flight can't read or edit their notes, and edits to the same note on two devices overwrite each other without warning.

## Requirements

- Users can read, create, edit, and delete notes on their phone without a connection, and their changes reach the server once they're back online.
- When the same note is edited on two devices whilst they're offline, neither edit is lost without the user knowing.
- A note deleted on one device disappears from the user's other devices.
- A phone that's been offline for a month still catches up when it reconnects.

## Constraints

- Users are on iOS 16 or later, or Android 10 or later, and often on slow or metered mobile data.
- Notes are plain text, up to 100 KB each. The heaviest users have about 5,000 notes.
- We have 40,000 monthly active users.
- The server is the FastAPI app in `server/`, which runs on Amazon ECS with Amazon RDS for PostgreSQL. The mobile app is the React Native app in `app/`.
