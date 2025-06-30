//  utility functions for file type operations
export const getFileTypeIcon = (fileType: string): string => {
    switch (fileType.toLowerCase()) {
        case "m3u":
            return "pi pi-video"
        case "epg-programs":
            return "pi pi-calendar"
        case "epg-channels":
            return "pi pi-table"
        default:
            return "pi pi-file"
    }
}
