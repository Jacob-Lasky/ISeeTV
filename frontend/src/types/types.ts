/**
 * TypeScript interfaces matching the backend Pydantic models
 * These should be kept in sync with backend/main.py
 */

/**
 * Message response from API endpoints
 */
export interface ApiMessage {
    message: string
}

/**
 * File metadata for downloadable resources
 */
export interface FileMetadata {
    url: string
    last_refresh?: string
    last_size_bytes?: number
}

/**
 * Source configuration for IPTV streams
 */
export interface Source {
    name: string
    number_of_connections?: number | null
    refresh_every_hours?: number | null
    subscription_expires?: string | null
    last_refresh?: string | null
    source_timezone?: string | null
    enabled: boolean
    file_metadata?: Record<string, FileMetadata>
}

/**
 * Global application settings
 */
export interface GlobalSettings {
    user_timezone: string
    program_cache_days: number
    theme: string
}

/**
 * API response types for different endpoints
 */
export interface ApiResponses {
    "/api/health": ApiMessage
    "/api/settings": GlobalSettings
    "/api/sources": Source[]
}

/**
 * API request types for POST endpoints
 */
export interface ApiRequests {
    "/api/settings": GlobalSettings
    "/api/sources": Source[]
}
