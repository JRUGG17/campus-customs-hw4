# Database Writes

Snapshot of `data/campus_customs.db` taken 2026-09-27 22:36. Hashes are truncated; plain-text passwords and session tokens are never stored. Emails other than the two demo logins are masked for the public repo.

## `users`

```sql
SELECT id, first_name, last_name, email, substr(password_hash, 1, 30) || '…' AS password_hash, created_at FROM users ORDER BY id
```

| id | first_name | last_name | email | password_hash | created_at |
|---|---|---|---|---|---|
| 1 | Test | User | test@campuscustoms.yale.edu | pbkdf2_sha256$600000$ef6130b49… | 2026-09-19 11:34:09 |
| 2 | Ada | Lovelace | a***@yale.edu | pbkdf2_sha256$36135cb0807f05a2… | 2026-09-19 11:56:30 |
| 3 | Tauhid | Zaman | t***@yale.edu | pbkdf2_sha256$df9c64a8bb6af8d5… | 2026-09-19 11:57:56 |
| 5 | Handsome | Dan | handsome.dan@yale.edu | pbkdf2_sha256$600000$88e714418… | 2026-09-27 23:39:52 |
| 6 | Mantis | Toboggan | d***@yale.edu | pbkdf2_sha256$600000$2fbffa292… | 2026-09-27 23:45:48 |

## `sessions`

```sql
SELECT id, user_id, substr(token_hash, 1, 16) || '…' AS token_hash, created_at, expires_at FROM sessions ORDER BY id
```

| id | user_id | token_hash | created_at | expires_at |
|---|---|---|---|---|
| 8 | 5 | dd3e9bf923d591f0… | 2026-09-27 23:39:54 | 2026-10-04 23:39:54 |
| 14 | 5 | 85b8f520aa063148… | 2026-09-27 23:59:44 | 2026-10-04 23:59:44 |
| 15 | 5 | b92983642ca887bb… | 2026-09-28 00:00:19 | 2026-10-05 00:00:19 |
| 16 | 5 | e0d13ad66c2f11bf… | 2026-09-28 00:15:51 | 2026-10-05 00:15:51 |
| 17 | 5 | 42b29aec33cfb36d… | 2026-09-28 00:16:55 | 2026-10-05 00:16:55 |
| 18 | 5 | f2d7bc17c830f45d… | 2026-09-28 00:30:23 | 2026-10-05 00:30:23 |
| 19 | 5 | 70572f45ef734737… | 2026-09-28 00:38:50 | 2026-10-05 00:38:50 |

## `chat_messages`

```sql
SELECT m.id, u.first_name || ' ' || u.last_name AS shopper, m.role, replace(substr(m.content, 1, 70), char(10), ' ') AS content, json_array_length(m.products_json) AS cards, m.results_heading, m.created_at FROM chat_messages m JOIN users u ON u.id = m.user_id WHERE m.id > 22 ORDER BY m.id
```

| id | shopper | role | content | cards | results_heading | created_at |
|---|---|---|---|---|---|---|
| 23 | Handsome Dan | user | Show me Saybrook gear | 0 | None | 2026-09-28 00:38:54 |
| 24 | Handsome Dan | assistant | I found 3 Saybrook items: a crewneck ($58.00), T-shirt ($32.00), and f | 3 | Saybrook items | 2026-09-28 00:38:54 |
| 25 | Handsome Dan | user | What did I ask you about a minute ago? And what is my email? | 0 | None | 2026-09-28 00:38:57 |
| 26 | Handsome Dan | assistant | A minute ago, you asked me to show you Saybrook gear. Your account ema | 0 | None | 2026-09-28 00:38:57 |
| 27 | Handsome Dan | user | Do you have this in pink? | 0 | None | 2026-09-28 00:40:17 |
| 28 | Handsome Dan | assistant | Sorry, this Baseball Left Chest Crewneck comes in navy with white lett | 2 | None | 2026-09-28 00:40:17 |
| 29 | Handsome Dan | user | OK, do you have it in medium then? | 0 | None | 2026-09-28 00:40:21 |
| 30 | Handsome Dan | assistant | Yes—there are 5 Baseball Left Chest Crewnecks left in medium. Sizes S, | 1 | None | 2026-09-28 00:40:21 |
| 31 | Handsome Dan | user | Do you have this in pink? | 0 | None | 2026-09-28 00:41:13 |
| 32 | Handsome Dan | assistant | No—this Baseball Left Chest Crewneck is navy with white lettering, not | 2 | None | 2026-09-28 00:41:13 |
| 33 | Handsome Dan | user | OK, do you have it in medium then? | 0 | None | 2026-09-28 00:41:17 |
| 34 | Handsome Dan | assistant | Yes—there are 5 Baseball Left Chest Crewnecks left in medium. Sizes S, | 1 | None | 2026-09-28 00:41:17 |
| 35 | Handsome Dan | user | What's the email on my account, and what was I looking at last time? | 0 | None | 2026-09-28 00:41:25 |
| 36 | Handsome Dan | assistant | Y***@yale.edu. Most recently, you were l | 1 | None | 2026-09-28 00:41:25 |
