/**
 * Message response from API endpoints
 */
export interface ApiMessage {
    message: string
}

/**
 * Download task response with task ID for progress tracking
 */
export interface DownloadTaskResponse {
    message: string
    task_id: string
}

/**
 * Download all tasks response with multiple task IDs
 */
export interface DownloadAllTasksResponse {
    message: string
    task_ids: string[]
}

/**
 * Download progress tracking
 */
export interface DownloadProgress {
    task_id: string
    status: "pending" | "downloading" | "completed" | "failed" | "cancelled"
    file_type: "m3u" | "epg"
    current_item?: string | null
    total_items: number
    completed_items: number
    bytes_downloaded: number
    total_bytes: number
    error_message?: string | null
    started_at: string
    completed_at?: string | null
}

/**
 * Ingest progress tracking
 */
export interface IngestProgress {
    task_id: string
    status: "pending" | "ingesting" | "completed" | "failed" | "cancelled"
    file_type: "m3u" | "epg"
    current_item?: string | null
    total_items: number
    completed_items: number
    error_message?: string | null
    started_at: string
    completed_at?: string | null
}

export interface TotalRecords {
    channels: number
    programs: number
}

/**
 * File metadata for downloadable resources, matches source.json
 */
export interface FileMetadata {
    url: string
    last_refresh_started_timestamp?: string
    last_size_bytes?: number
    last_refresh_status?: "success" | "failed" | "cancelled"
    last_refresh_finished_timestamp?: string
    total_records: TotalRecords
}

/**
 * Source interface, matches source.json
 */
export interface Source {
    name: string
    number_of_connections?: number | null
    refresh_every_hours?: number | null
    refresh_time?: string | null
    subscription_expires?: string | null
    source_timezone?: string | null
    enabled: boolean
    rule_mode?: "whitelist" | "blacklist" // Default to blacklist (start with all channels)
    file_metadata: Record<string, FileMetadata>
}

/**
 *  file representation - single responsibility for file-specific data
 */
export interface SourceFile {
    id: string // unique identifier: sourceId + fileType
    sourceId: string // reference to parent source
    type: "m3u" | "epg" // file type
    url: string
    last_refresh_started_timestamp?: string | null
    last_size_bytes?: number
    status?: "active" | "inactive" | "error"
    last_error?: string | null
}

/**
 *  source representation - single responsibility for source-specific metadata
 */
export interface SourceProvider {
    id: string // unique identifier
    name: string
    number_of_connections?: number | null
    refresh_every_hours?: number | null
    refresh_time?: string | null
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
    sourceRefreshTime?: string | null
    sourceSubscriptionExpires?: string | null

    fileId: string
    fileType: "m3u" | "epg"
    fileUrl: string
    fileLastRefreshStartedTimestamp?: string | null
    fileLastRefreshFinishedTimestamp?: string | null
    fileSizeBytes?: number
    fileStatus?: "active" | "inactive" | "error"
    fileMetadata: FileMetadata // complete file metadata for status tracking

    isFirstFileForSource?: boolean // for rowspan logic
    rowSpanCount?: number // number of files for this source
}

/**
 * Global application settings
 */
export interface GlobalSettings {
    user_timezone: string
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
 * Stream channel with joined M3U and EPG data
 */
export interface StreamChannel {
    // M3U Channel Data (primary)
    m3u_id: number
    source: string
    tvg_id: string // This is the canonical channel_id
    name: string
    stream_url: string
    logo_url?: string | null
    group?: string | null
    stream_mode: string
    // EPG Channel Data (joined)
    epg_id?: number | null
    display_name?: string | null
    icon_url?: string | null

    // Metadata
    created_at: string
    updated_at: string

    // Program counts (aggregated)
    program_count: number
    next_program_title?: string | null
    next_program_start?: string | null
}

/**
 * Stream program with channel context
 */
export interface StreamProgram {
    // Program Data
    program_id: number
    source: string
    program_uid: string
    channel_id: string
    start_time: string
    end_time: string
    title?: string | null
    description?: string | null

    // Channel Context (joined)
    channel_name?: string | null
    channel_display_name?: string | null
    channel_group?: string | null
    stream_url?: string | null
    logo_url?: string | null
    icon_url?: string | null

    // Metadata
    created_at: string
    updated_at: string
}

/**
 * Filter value for dropdown options
 */
export interface FilterValue {
    value: string
    count: number
}

/**
 * Filter view counts for normal/inverse/all views
 */
export interface FilterViewCounts {
    normal: number
    inverse: number
    all: number
}

/**
 * Streams API response with pagination
 */
export interface StreamsResponse {
    success: boolean
    data: StreamChannel[]
    total: number
    page: number
    page_size: number
    total_pages: number
    has_next: boolean
    has_prev: boolean
    filters: Record<string, FilterValue[]>
    filter_view_counts?: FilterViewCounts
}

/**
 * Stream programs API response with pagination
 */
export interface StreamProgramsResponse {
    success: boolean
    data: StreamProgram[]
    total: number
    page: number
    page_size: number
    total_pages: number
    has_next: boolean
    has_prev: boolean
    filters: Record<string, FilterValue[]>
}

/**
 * API request types for POST endpoints
 */
export interface ApiRequests {
    "/api/settings": GlobalSettings
    "/api/sources": Source[]
}
