export interface Source {
    name: string
    m3u_url: string
    epg_url?: string
    number_of_connections?: number
    refresh_every_hours?: number
    subscription_expires?: string
    source_timezone?: string
    enabled: boolean
}
