# Database Schema Documentation

## Overview
This document describes the database schema for the IPTV application. The schema consists of three main tables: channels, epg_channels, and programs.

## Tables

### channels
Primary table for storing channel information from M3U playlists.

| Column        | Type      | Constraints       | Description                                    |
|--------------|-----------|------------------|------------------------------------------------|
| channel_id   | String    | PRIMARY KEY      | Unique identifier for the channel              |
| name         | String    | INDEX            | Display name of the channel                    |
| url          | String    | NOT NULL         | Stream URL for the channel                     |
| group        | String    | INDEX            | Channel group/category                         |
| logo         | String    | NULLABLE         | URL to channel logo image                      |
| is_favorite  | Boolean   | DEFAULT FALSE    | Whether user has marked channel as favorite    |
| last_watched | DateTime  | NULLABLE         | Timestamp of last time channel was watched     |
| created_at   | DateTime  | DEFAULT UTC NOW  | When the channel was added to the database    |
| is_missing   | Boolean   | DEFAULT FALSE    | Whether channel was missing in last M3U update |

### epg_channels
Links EPG data to channels and stores EPG-specific channel information.

| Column        | Type      | Constraints                | Description                                    |
|--------------|-----------|---------------------------|------------------------------------------------|
| id           | Integer   | PRIMARY KEY               | Auto-incrementing identifier                    |
| channel_id   | String    | FOREIGN KEY (channels)    | References channels.channel_id                  |
| display_name | String    | NOT NULL                  | Channel name from EPG                          |
| icon         | String    | NULLABLE                  | Channel icon URL from EPG                      |
| is_primary   | Boolean   | DEFAULT FALSE            | Whether this is primary EPG mapping for channel |

### programs
Stores program/show information from EPG data.

| Column      | Type      | Constraints                | Description                                    |
|------------|-----------|---------------------------|------------------------------------------------|
| id         | Integer   | PRIMARY KEY               | Auto-incrementing identifier                    |
| channel_id | String    | FOREIGN KEY (channels)    | References channels.channel_id                  |
| start_time | DateTime  | NOT NULL, TIMEZONE        | Program start time (with timezone)             |
| end_time   | DateTime  | NOT NULL, TIMEZONE        | Program end time (with timezone)               |
| title      | String    | NOT NULL                  | Program title                                  |
| description| String    | NULLABLE                  | Program description                            |
| category   | String    | NULLABLE                  | Program category/genre                         |
| created_at | DateTime  | DEFAULT NOW               | When program was added to database             |

## Relationships

1. channels ← epg_channels
   - One-to-Many: A channel can have multiple EPG channel mappings
   - Foreign Key: epg_channels.channel_id → channels.channel_id

2. channels ← programs
   - One-to-Many: A channel can have multiple programs
   - Foreign Key: programs.channel_id → channels.channel_id

## Indexes
- channels.name: For quick channel search
- channels.group: For filtering by channel groups
- Implicit indexes on all primary and foreign keys

## Notes
- All DateTime fields use UTC timezone
- EPG data (programs) is periodically updated from XMLTV source
- Channel data is updated from M3U playlist source
- Missing channels are marked rather than deleted to preserve user preferences 