-- models.sql
-- One row per (series URL, Discord channel) combination
CREATE TABLE IF NOT EXISTS subscriptions (
    url         TEXT NOT NULL,      -- full series page URL
    channel_id  INTEGER NOT NULL,   -- Discord text/news-channel to post in
    last_id     TEXT NOT NULL,      -- latest-chapter ID we’ve already announced
    ping_ids    TEXT NOT NULL,      -- comma-separated Discord IDs to @mention
    owner_id    INTEGER NOT NULL,   -- user who created the entry
    PRIMARY KEY (url, channel_id)
);
