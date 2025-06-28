/**
 * Message response from API endpoints
 */
export interface ApiMessage {
    message: string
}

/**
 * File metadata for downloadable resources, matches source.json
 */
export interface FileMetadata {
    url: string
    last_refresh?: string
    last_size_bytes?: number
}

/**
 * Source interface, matches source.json
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
 * Atomic file representation - single responsibility for file-specific data
 */
export interface SourceFile {
    id: string // unique identifier: sourceId + fileType
    sourceId: string // reference to parent source
    type: "m3u" | "epg" // file type
    url: string
    last_refresh?: string | null
    last_size_bytes?: number
    status?: "active" | "inactive" | "error"
    last_error?: string | null
}

/**
 * Atomic source representation - single responsibility for source-specific metadata
 */
export interface SourceProvider {
    id: string // unique identifier
    name: string
    number_of_connections?: number | null
    refresh_every_hours?: number | null
    subscription_expires?: string | null
    source_timezone?: string | null
    enabled: boolean
    // Source-level metadata only, no file-specific data
}

/**
 * Normalized data structure for the table display
 * Combines source and file data for row-grouped display
 */
export interface SourceFileRow {
    sourceId: string
    sourceName: string
    sourceEnabled: boolean
    sourceTimezone?: string | null
    sourceConnections?: number | null
    sourceRefreshHours?: number | null
    sourceSubscriptionExpires?: string | null

    fileId: string
    fileType: "m3u" | "epg"
    fileUrl: string
    fileLastRefresh?: string | null
    fileSizeBytes?: number
    fileStatus?: "active" | "inactive" | "error"
    fileLastError?: string | null

    isFirstFileForSource?: boolean // for rowspan logic
    rowSpanCount?: number // number of files for this source
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
