# Telegram

<!-- toc -->

- [General](#general)
- [Secret vs Regular chats](#secret-vs-regular-chats)
  * [Secret](#secret)
  * [Regular](#regular)
- [Username](#username)
- [Google meet room](#google-meet-room)

<!-- tocstop -->

# General

- We use [Telegram](https://telegram.org/) for
  - Discussions that need
    - tight interaction (like a debug session)
    - immediacy (e.g., "are you ready for the sync up?")
  - Github Actions notifications from Telegram bots
    - E.g., regressions fail in one of our repos

# Secret vs Regular chats

## Secret

- We use secret chats for private one-on-one communication
  - We prefer to send all the sensitive information using encrypted chats
  - A Secret chat uses end-to-end encryption which means that even Telegram does
    not have access to a conversion
- How to start secret chat - see
  [here](https://telegram.org/faq#q-how-do-i-start-a-secret-chat)
- Limitations:
  - Telegram desktop version does not support secret chats so one uses secret
    chats only using his/her phone
  - You cannot add multiple people to a secret chat, only one-on-one
    communication is allowed
  - All secret chats in Telegram are device-specific and are not part of the
    Telegram cloud. This means you can only access messages in a secret chat
    from their device of origin.

## Regular

- We use regular chats for
  - General discussions within a team
  - Group chats
- We do not share sensitive information via regular chats

# Username

- We ask everyone to set a username so that is easier to find a person
- See the instructions
  [here](https://telegram.org/faq#q-what-are-usernames-how-do-i-get-one)

# Google meet room

- It is always nice to pin a google meeting room in a chat
- We usually use `->` as an invitation to join a google meet room pinned in a
  chat
