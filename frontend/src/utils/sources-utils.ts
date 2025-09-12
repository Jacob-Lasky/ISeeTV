
import { apiGet, apiPost } from "@/utils/apiUtils"

// Types for source operations
export interface SourceFileRow {
    fileId: string
    sourceName: string
    fileType: "epg" | "m3u"
    _isGroupHeader?: boolean
}

export interface DownloadTaskResponse {
    task_id: string
    message: string
    status: string
}

export interface DownloadAllTasksResponse {
    task_ids: string[]
    message: string
    status: string
}

export interface IngestTaskResponse {
    task_id: string
    message: string
    status: string
}

// Progress polling utilities
const activePollingIntervals = new Map<string, NodeJS.Timeout>()
const activeIngestPollingIntervals = new Map<string, NodeJS.Timeout>()

/**
 * Start progress polling for a download task
 * @param taskId - The download task ID
 * @param fileId - The file ID for UI updates
 * @param onProgress - Optional callback for progress updates
 */
export function startProgressPolling(
    taskId: string,
    fileId: string,
    onProgress?: (progress: any) => void
) {
    // Clear any existing polling for this task
    stopProgressPolling(taskId, fileId)

    const interval = setInterval(async () => {
        try {
            const progressData = await apiGet(
                `/api/downloads/progress/${taskId}`,
                false, // No loading toast
                { showSuccessToast: false, showErrorToast: false } // No toast messages for polling
            )

            if (onProgress) {
                onProgress(progressData)
            }

            // Stop polling if task is complete or failed
            if (
                progressData.status === "completed" ||
                progressData.status === "failed"
            ) {
                stopProgressPolling(taskId, fileId)
            }
        } catch (error) {
            console.error(
                `Download progress polling error for task ${taskId}:`,
                error
            )
            stopProgressPolling(taskId, fileId)
        }
    }, 1000) // Poll every second

    activePollingIntervals.set(`${taskId}_${fileId}`, interval)
}

/**
 * Stop progress polling for a download task
 * @param taskId - The download task ID
 * @param fileId - The file ID
 */
export function stopProgressPolling(taskId: string, fileId: string) {
    const key = `${taskId}_${fileId}`
    const interval = activePollingIntervals.get(key)
    if (interval) {
        clearInterval(interval)
        activePollingIntervals.delete(key)
    }
}

/**
 * Start ingest progress polling
 * @param taskId - The ingest task ID
 * @param fileId - The file ID for UI updates
 * @param onProgress - Optional callback for progress updates
 */
export function startIngestProgressPolling(
    taskId: string,
    fileId: string,
    onProgress?: (progress: any) => void
) {
    // Clear any existing polling for this task
    stopIngestProgressPolling(taskId, fileId)

    const interval = setInterval(async () => {
        try {
            const progressData = await apiGet(
                `/api/ingest/progress`,
                false, // No loading toast
                { showSuccessToast: false, showErrorToast: false } // No toast messages for polling
            )
            const taskProgress = progressData.find(
                (p: any) => p.task_id === taskId
            )

            if (onProgress && taskProgress) {
                onProgress(taskProgress)
            }

            // Stop polling if task is complete or failed
            if (
                taskProgress &&
                (taskProgress.status === "completed" ||
                    taskProgress.status === "failed")
            ) {
                stopIngestProgressPolling(taskId, fileId)
            }
        } catch (error) {
            console.error(
                `Ingest progress polling error for task ${taskId}:`,
                error
            )
            stopIngestProgressPolling(taskId, fileId)
        }
    }, 1000) // Poll every second

    activeIngestPollingIntervals.set(`${taskId}_${fileId}`, interval)
}

/**
 * Stop ingest progress polling
 * @param taskId - The ingest task ID
 * @param fileId - The file ID
 */
export function stopIngestProgressPolling(taskId: string, fileId: string) {
    const key = `${taskId}_${fileId}`
    const interval = activeIngestPollingIntervals.get(key)
    if (interval) {
        clearInterval(interval)
        activeIngestPollingIntervals.delete(key)
    }
}

/**
 * Start progress polling and wait for completion
 * @param taskId - Task ID to poll for
 * @returns Promise that resolves when task completes
 */
export function startProgressPollingAndWait(taskId: string): Promise<void> {
    return new Promise((resolve, reject) => {
        const interval = setInterval(async () => {
            try {
                const progressData = await apiGet(
                    `/api/downloads/progress/${taskId}`,
                    false, // No loading toast
                    { showSuccessToast: false, showErrorToast: false } // No toast messages for polling
                )

                if (progressData.status === "completed") {
                    clearInterval(interval)
                    resolve()
                } else if (progressData.status === "failed") {
                    clearInterval(interval)
                    reject(
                        new Error(
                            `Download failed: ${progressData.error || "Unknown error"}`
                        )
                    )
                }
            } catch (error) {
                console.error(`Error polling download task ${taskId}:`, error)
                clearInterval(interval)
                reject(error)
            }
        }, 1000)
    })
}

/**
 * Start ingest progress polling and wait for completion
 * @param taskId - Task ID to poll for
 * @returns Promise that resolves when task completes
 */
export function startIngestProgressPollingAndWait(
    taskId: string
): Promise<void> {
    return new Promise((resolve, reject) => {
        const interval = setInterval(async () => {
            try {
                const progressData = await apiGet(
                    `/api/ingest/progress`,
                    false, // No loading toast
                    { showSuccessToast: false, showErrorToast: false } // No toast messages for polling
                )

                const taskProgress = progressData.find(
                    (p: any) => p.task_id === taskId
                )

                if (taskProgress) {
                    if (taskProgress.status === "completed") {
                        clearInterval(interval)
                        resolve()
                    } else if (taskProgress.status === "failed") {
                        clearInterval(interval)
                        reject(
                            new Error(
                                `Ingest failed: ${taskProgress.error || "Unknown error"}`
                            )
                        )
                    }
                }
            } catch (error) {
                console.error(`Error polling ingest task ${taskId}:`, error)
                clearInterval(interval)
                reject(error)
            }
        }, 1000)
    })
}

/**
 * Refresh a single file (download + ingest)
 * @param fileRow - The file row data
 * @param onProgress - Optional progress callback
 */
export async function refreshFile(
    fileRow: SourceFileRow,
    onProgress?: (progress: any) => void
): Promise<void> {
    console.log(
        `Refreshing ${fileRow.fileType.toUpperCase()} file for source: ${fileRow.sourceName}`
    )

    try {
        // Step 1: Start download
        const downloadEndpoint = `/api/${encodeURIComponent(fileRow.sourceName)}/downloads/${fileRow.fileType}`
        const downloadResponse = await apiPost<DownloadTaskResponse>(
            downloadEndpoint,
            {},
            true,
            {
                successMessage: `${fileRow.fileType.toUpperCase()} download started`,
                errorPrefix: `${fileRow.fileType.toUpperCase()} download failed`,
            }
        )

        // Start download progress polling and wait for completion
        await startProgressPollingAndWait(
            downloadResponse.task_id,
            fileRow.fileId
        )

        // Step 2: Only start ingest after download is complete
        console.log(
            `Download completed for ${fileRow.fileType}, starting ingest process...`
        )
        const ingestEndpoint = `/api/${encodeURIComponent(fileRow.sourceName)}/loads/${fileRow.fileType}`
        const ingestResponse = await apiPost<IngestTaskResponse>(
            ingestEndpoint,
            {},
            true,
            {
                successMessage: `${fileRow.fileType.toUpperCase()} processing started`,
                errorPrefix: `${fileRow.fileType.toUpperCase()} processing failed`,
            }
        )

        // Start ingest progress polling
        startIngestProgressPolling(
            ingestResponse.task_id,
            fileRow.fileId,
            onProgress
        )
    } catch (error) {
        console.error(
            `Failed to refresh ${fileRow.fileType} for ${fileRow.sourceName}:`,
            error
        )
        throw error
    }
}

/**
 * Refresh all files for a specific source
 * @param sourceName - The source name
 * @param sourceFiles - Array of source file rows for this source
 * @param onProgress - Optional progress callback
 */
export async function refreshAllFilesForSource(
    sourceName: string,
    sourceFiles: SourceFileRow[],
    onProgress?: (progress: any) => void
): Promise<void> {
    console.log(`Refreshing all files for source: ${sourceName}`)

    try {
        // Defensive check for sourceName
        if (!sourceName || typeof sourceName !== "string") {
            console.warn(
                "Invalid sourceName provided to refreshAllFilesForSource"
            )
            return
        }

        // Filter to get actual file rows (not group headers)
        const validFiles = sourceFiles.filter(
            (row) => row && row.sourceName === sourceName && !row._isGroupHeader
        )

        if (validFiles.length === 0) {
            console.warn(`No files found for source: ${sourceName}`)
            return
        }

        // Refresh each file for this source
        for (const fileRow of validFiles) {
            if (fileRow && fileRow.fileType && fileRow.sourceName) {
                try {
                    await refreshFile(fileRow, onProgress)
                } catch (fileError) {
                    console.error(
                        `Failed to refresh ${fileRow.fileType} for ${sourceName}:`,
                        fileError
                    )
                    // Continue with other files even if one fails
                }
            }
        }
    } catch (error) {
        console.error(
            `Failed to refresh all files for source ${sourceName}:`,
            error
        )
        throw error
    }
}

/**
 * Download a file without ingesting
 * @param fileRow - The file row data
 * @param onProgress - Optional progress callback
 */
export async function downloadFile(
    fileRow: SourceFileRow,
    onProgress?: (progress: any) => void
): Promise<void> {
    console.log(
        `Downloading ${fileRow.fileType.toUpperCase()} file for source: ${fileRow.sourceName}`
    )

    try {
        const downloadEndpoint = `/api/${encodeURIComponent(fileRow.sourceName)}/downloads/${fileRow.fileType}`
        const downloadResponse = await apiPost<DownloadTaskResponse>(
            downloadEndpoint,
            {},
            true,
            {
                successMessage: `${fileRow.fileType.toUpperCase()} download started`,
                errorPrefix: `${fileRow.fileType.toUpperCase()} download failed`,
            }
        )

        // Start progress polling with progress callback
        if (onProgress) {
            startProgressPolling(
                downloadResponse.task_id,
                fileRow.fileId,
                onProgress
            )
        }

        // Wait for download to complete before returning
        await startProgressPollingAndWait(downloadResponse.task_id)
    } catch (error) {
        console.error(
            `Failed to download ${fileRow.fileType} for ${fileRow.sourceName}:`,
            error
        )
        throw error
    }
}

/**
 * Reingest a file (ingest only, no download)
 * @param fileRow - The file row data
 * @param onProgress - Optional progress callback
 */
export async function reingestFile(
    fileRow: SourceFileRow,
    onProgress?: (progress: any) => void
): Promise<void> {
    console.log(
        `Reingesting ${fileRow.fileType.toUpperCase()} file for source: ${fileRow.sourceName}`
    )

    try {
        const ingestEndpoint = `/api/${encodeURIComponent(fileRow.sourceName)}/loads/${fileRow.fileType}`
        const ingestResponse = await apiPost<IngestTaskResponse>(
            ingestEndpoint,
            {},
            true,
            {
                successMessage: `${fileRow.fileType.toUpperCase()} processing started`,
                errorPrefix: `${fileRow.fileType.toUpperCase()} processing failed`,
            }
        )

        // Start ingest progress polling with progress callback
        if (onProgress) {
            startIngestProgressPolling(
                ingestResponse.task_id,
                fileRow.fileId,
                onProgress
            )
        }

        // Wait for ingest to complete before returning
        await startIngestProgressPollingAndWait(ingestResponse.task_id)
    } catch (error) {
        console.error(
            `Failed to reingest ${fileRow.fileType} for ${fileRow.sourceName}:`,
            error
        )
        throw error
    }
}

/**
 * Cancel a download task
 * @param taskId - The download task ID
 * @param fileRow - The file row data
 */
export async function cancelDownload(
    taskId: string,
    fileRow: SourceFileRow
): Promise<void> {
    try {
        const endpoint = `/api/downloads/cancel/${taskId}`

        await fetch(endpoint, {
            method: "DELETE",
            headers: {
                "Content-Type": "application/json",
            },
        }).then((response) => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`)
            }
            console.log(
                `${fileRow.fileType.toUpperCase()} download cancelled successfully`
            )
        })

        // Stop local progress polling immediately
        stopProgressPolling(taskId, fileRow.fileId)
    } catch (error) {
        console.error(
            `Failed to cancel ${fileRow.fileType} download for ${fileRow.sourceName}:`,
            error
        )
        throw error
    }
}

/**
 * Clean up all active polling intervals
 */
export function cleanupAllPolling(): void {
    // Clear download progress polling
    for (const [key, interval] of activePollingIntervals.entries()) {
        clearInterval(interval)
    }
    activePollingIntervals.clear()

    // Clear ingest progress polling
    for (const [key, interval] of activeIngestPollingIntervals.entries()) {
        clearInterval(interval)
    }
    activeIngestPollingIntervals.clear()
}
