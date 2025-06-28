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
 * Source configuration for IPTV streams
 */
export interface Source {
    name: string
    m3u_url: string
    epg_url?: string | null
    number_of_connections?: number | null
    refresh_every_hours?: number | null
    subscription_expires?: string | null
    source_timezone?: string | null
    enabled: boolean
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
