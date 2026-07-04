-- PostgreSQL/Supabase Database Schema for SponsorFlow.io MVP

-- Enable UUID extension if supported, otherwise fall back to standard serial/identity
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Channels Table (podcasts, newsletters, youtube channels)
CREATE TABLE IF NOT EXISTS channels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL CHECK (platform IN ('newsletter', 'podcast', 'youtube')),
    raw_url TEXT NOT NULL,
    media_kit_claimed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Unique constraint on channel URL to prevent duplicate profiles
ALTER TABLE channels ADD CONSTRAINT unique_channel_url UNIQUE (raw_url);

-- Sponsors Table (brands buying sponsorships)
CREATE TABLE IF NOT EXISTS sponsors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_name VARCHAR(255) NOT NULL,
    industry_tag VARCHAR(100),
    global_website TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Unique constraint on brand name to prevent duplicate sponsor profiles
ALTER TABLE sponsors ADD CONSTRAINT unique_brand_name UNIQUE (brand_name);

-- Sponsorship Signals Table (individual occurrences of sponsorships detected by our engines)
CREATE TABLE IF NOT EXISTS sponsorship_signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_id UUID NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    sponsor_id UUID NOT NULL REFERENCES sponsors(id) ON DELETE CASCADE,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ad_copy TEXT,
    source_url TEXT,
    estimated_value_tier VARCHAR(50), -- e.g. 'Low ($0-$500)', 'Medium ($500-$2000)', 'High ($2000+)'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indices for optimized querying (dashboard leaderboards & competitor lookup)
CREATE INDEX IF NOT EXISTS idx_signals_channel_id ON sponsorship_signals(channel_id);
CREATE INDEX IF NOT EXISTS idx_signals_sponsor_id ON sponsorship_signals(sponsor_id);
CREATE INDEX IF NOT EXISTS idx_signals_detected_at ON sponsorship_signals(detected_at);
