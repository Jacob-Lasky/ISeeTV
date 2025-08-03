<template>
    <div class="source-node-wrapper">
        <!-- Node Toolbar -->
        <NodeToolbar
            :is-visible="data.toolbarVisible"
            :position="data.toolbarPosition || 'top'"
        >
            <div class="toolbar-buttons">
                <Button
                    icon="pi pi-download"
                    size="small"
                    severity="primary"
                    v-tooltip.top="'Redownload source files'"
                    @click="handleRedownload"
                    :loading="isRedownloading"
                />
                <Button
                    icon="pi pi-refresh"
                    size="small"
                    severity="secondary"
                    v-tooltip.top="'Reingest data into database'"
                    @click="handleReingest"
                    :loading="isReingesting"
                />
                <Button
                    icon="pi pi-sync"
                    size="small"
                    severity="info"
                    v-tooltip.top="'Refresh (redownload + reingest)'"
                    @click="handleRefresh"
                    :loading="isRefreshing"
                />
                <Button
                    icon="pi pi-cog"
                    size="small"
                    severity="secondary"
                    v-tooltip.top="'Go to source settings'"
                    @click="handleSettings"
                />
            </div>
        </NodeToolbar>

        <div class="source-node">
            <div class="node-header">
                <i class="pi pi-database"></i>
                <span class="node-title">{{ data.label }}</span>
            </div>

            <div class="node-body">
                <!-- Progress Tracking - Only show during active download/ingestion -->
                <div v-if="hasActiveProgress" class="progress-section">
                    <!-- M3U Ingestion Progress -->
                    <div
                        v-if="m3uIngestProgress"
                        class="ingest-progress-container m3u-progress"
                    >
                        <div class="progress-header">
                            <i class="pi pi-list"></i>
                            <span class="progress-type">M3U Ingestion</span>
                        </div>
                        <div class="step-info">
                            <span class="step-indicator">
                                Step
                                {{ m3uIngestProgress.current_step || 1 }}/{{
                                    m3uIngestProgress.total_steps || 3
                                }}:
                            </span>
                            <span class="step-name">
                                {{
                                    formatStepName(m3uIngestProgress.step_name)
                                }}
                            </span>
                        </div>
                        <div class="progress-details">
                            <span
                                v-if="m3uIngestProgress.total_items > 0"
                                class="progress-items"
                            >
                                {{ m3uIngestProgress.completed_items || 0 }}
                                /
                                {{ m3uIngestProgress.total_items }}
                                items
                            </span>
                            <span
                                v-else-if="
                                    m3uIngestProgress.completed_items > 0
                                "
                                class="progress-items"
                            >
                                {{
                                    formatNumber(
                                        m3uIngestProgress.completed_items || 0
                                    )
                                }}
                                records processed
                            </span>
                            <span
                                v-else-if="m3uIngestProgress.current_item"
                                class="progress-current-item"
                            >
                                {{ m3uIngestProgress.current_item }}
                            </span>
                        </div>
                        <!-- Progress bar: step-specific progress or indeterminate -->
                        <ProgressBar
                            v-if="
                                getStepProgressValue(m3uIngestProgress) !== null
                            "
                            :value="getStepProgressValue(m3uIngestProgress)"
                            style="height: 12px; margin-top: 4px"
                        />
                        <ProgressBar
                            v-else
                            mode="indeterminate"
                            style="height: 12px; margin-top: 4px"
                        />
                    </div>

                    <!-- EPG Ingestion Progress -->
                    <div
                        v-if="epgIngestProgress"
                        class="ingest-progress-container epg-progress"
                    >
                        <div class="progress-header">
                            <i class="pi pi-calendar"></i>
                            <span class="progress-type">EPG Ingestion</span>
                        </div>
                        <div class="step-info">
                            <span class="step-indicator">
                                Step
                                {{ epgIngestProgress.current_step || 1 }}/{{
                                    epgIngestProgress.total_steps || 3
                                }}:
                            </span>
                            <span class="step-name">
                                {{
                                    formatStepName(epgIngestProgress.step_name)
                                }}
                            </span>
                        </div>
                        <div class="progress-details">
                            <span
                                v-if="epgIngestProgress.total_items > 0"
                                class="progress-items"
                            >
                                {{ epgIngestProgress.completed_items || 0 }}
                                /
                                {{ epgIngestProgress.total_items }}
                                items
                            </span>
                            <span
                                v-else-if="
                                    epgIngestProgress.completed_items > 0
                                "
                                class="progress-items"
                            >
                                {{
                                    formatNumber(
                                        epgIngestProgress.completed_items || 0
                                    )
                                }}
                                records processed
                            </span>
                            <span
                                v-else-if="epgIngestProgress.current_item"
                                class="progress-current-item"
                            >
                                {{ epgIngestProgress.current_item }}
                            </span>
                        </div>
                        <!-- Progress bar: step-specific progress or indeterminate -->
                        <ProgressBar
                            v-if="
                                getStepProgressValue(epgIngestProgress) !== null
                            "
                            :value="getStepProgressValue(epgIngestProgress)"
                            style="height: 12px; margin-top: 4px"
                        />
                        <ProgressBar
                            v-else
                            mode="indeterminate"
                            style="height: 12px; margin-top: 4px"
                        />
                    </div>
                    <!-- Show download progress if file is downloading -->
                    <div
                        v-else-if="activeDownloadProgress"
                        class="download-progress-container"
                    >
                        <div class="progress-info">
                            <span class="progress-status">
                                Downloading
                                {{
                                    activeDownloadProgress.file_type?.toUpperCase() ||
                                    "file"
                                }}:
                            </span>
                            <span
                                v-if="activeDownloadProgress.total_bytes > 0"
                                class="progress-bytes"
                            >
                                {{
                                    formatBytes(
                                        activeDownloadProgress.bytes_downloaded ||
                                            0
                                    )
                                }}
                                /
                                {{
                                    formatBytes(
                                        activeDownloadProgress.total_bytes || 0
                                    )
                                }}
                            </span>
                            <span v-else class="progress-bytes">
                                {{
                                    formatBytes(
                                        activeDownloadProgress.bytes_downloaded ||
                                            0
                                    )
                                }}
                                downloaded
                            </span>
                        </div>
                        <ProgressBar
                            v-if="activeDownloadProgress.total_bytes > 0"
                            :value="
                                Math.round(
                                    ((activeDownloadProgress.bytes_downloaded ||
                                        0) /
                                        (activeDownloadProgress.total_bytes ||
                                            1)) *
                                        100
                                )
                            "
                            style="height: 12px; margin-top: 4px"
                        />
                        <ProgressBar
                            v-else
                            mode="indeterminate"
                            style="height: 12px; margin-top: 4px"
                        />
                    </div>
                </div>

                <!-- Table Statistics Display -->
                <div class="stats-section">
                    <!-- Individual table counts -->
                    <template v-for="table in data.tables" :key="table.name">
                        <div
                            class="stat-item table-stat"
                            :style="{
                                borderLeftColor: getTableColor(table.name),
                            }"
                        >
                            <span class="stat-label">{{ table.name }}:</span>
                            <span class="stat-value">{{
                                formatNumber(table.recordCount)
                            }}</span>
                        </div>
                    </template>
                </div>

                <!-- Execution Status -->
                <div v-if="data.isExecuting" class="execution-status">
                    <i class="pi pi-spin pi-spinner"></i>
                    <span>Processing...</span>
                </div>
            </div>

            <!-- Output handles for each table -->
            <template v-for="(table, index) in data.tables" :key="table.name">
                <Handle
                    :id="`table-${table.name}`"
                    type="source"
                    :position="Position.Right"
                    :style="{
                        top: `${25 + index * 25}%`,
                        backgroundColor: getTableColor(table.name),
                        borderColor: getTableColor(table.name),
                    }"
                    class="output-handle table-handle"
                />
                <div
                    v-if="isSelected"
                    class="handle-label table-label"
                    :style="{
                        top: `${25 + index * 25}%`,
                        backgroundColor: getTableColor(table.name),
                    }"
                >
                    {{ table.name }}
                </div>
            </template>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, inject, onMounted, ref } from "vue"
import { Handle, Position, useNode } from "@vue-flow/core"
import { NodeToolbar } from "@vue-flow/node-toolbar"
import Button from "primevue/button"
import ProgressBar from "primevue/progressbar"
import { useRouter } from "vue-router"
import { useToast } from "primevue/usetoast"
import type { SourceNodeData } from "@/types/flow-types"
import {
    refreshAllFilesForSource,
    downloadFile,
    reingestFile,
    startProgressPolling,
    startIngestProgressPolling,
    stopProgressPolling,
    stopIngestProgressPolling,
    type SourceFileRow,
} from "@/utils/sources-utils"
import { apiPost, apiGet } from "@/utils/apiUtils"

// Progress tracking types
interface DownloadProgress {
    task_id: string
    status: string
    bytes_downloaded: number
    total_bytes: number
    progress_percentage: number
    download_speed: number
    eta_seconds: number
    updated_at: string
}

interface IngestProgress {
    task_id: string
    status: string
    current_step: number
    total_steps: number
    step_name: string
    completed_items: number
    total_items: number
    current_item: string
    source_name: string
    current_phase: string
    updated_at: string
}

// Props - Define all Vue Flow props to prevent warnings
interface Props {
    id: string
    data: SourceNodeData
    // Vue Flow internal props
    type?: string
    events?: any
    selected?: boolean
    resizing?: boolean
    dragging?: boolean
    connectable?: boolean
    position?: { x: number; y: number }
    dimensions?: { width: number; height: number }
    isValidTargetPos?: boolean
    isValidSourcePos?: boolean
    parent?: string
    parentNodeId?: string
    zIndex?: number
    targetPosition?: string
    sourcePosition?: string
    label?: string
    dragHandle?: string
}

const props = defineProps<Props>()

// Define emits for Vue Flow event listeners
const emit = defineEmits<{
    updateNodeInternals: [nodeId: string]
}>()

// Selection state for conditional label display
const selectedNodeId = inject<any>("selectedNodeId")
const { node } = useNode()

// Check if this node is selected
const isSelected = computed(() => {
    return selectedNodeId?.value === node.id
})

// Utility functions
const formatNumber = (num: number): string => {
    return new Intl.NumberFormat().format(num)
}

// Color coding for different table types
const getTableColor = (tableName: string): string => {
    switch (tableName) {
        case "m3u_channels":
            return "#3b82f6" // Blue
        case "epg_channels":
            return "#10b981" // Green
        case "programs":
            return "#f59e0b" // Amber
        default:
            return "#6b7280" // Gray
    }
}

// Progress tracking utility functions
const formatBytes = (bytes: number): string => {
    if (bytes === 0) return "0 B"
    const k = 1024
    const sizes = ["B", "KB", "MB", "GB"]
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i]
}

const formatStepName = (stepName: string | undefined): string => {
    if (!stepName) return "Processing"
    return stepName
        .split("_")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ")
}

const getStepProgressValue = (
    progress?: IngestProgress | null
): number | null => {
    if (!progress) return null

    if (
        progress.step_progress !== undefined &&
        progress.step_progress !== null
    ) {
        return Math.round(progress.step_progress)
    }
    if (
        progress.overall_progress !== undefined &&
        progress.overall_progress !== null
    ) {
        return Math.round(progress.overall_progress)
    }
    return null
}

// Router and toast for navigation and notifications
const router = useRouter()
const toast = useToast()

// Resume active ingestion progress polling on mount
const resumeActiveIngestPolling = async () => {
    try {
        // Check for any active ingest tasks from the backend
        const progress = await apiGet<{
            ingest: Record<string, IngestProgress>
        }>(`/api/ingest/progress`, false, {
            showSuccessToast: false,
            showErrorToast: false,
        })

        // Resume polling for any active ingest tasks for this source
        if (progress.ingest) {
            for (const [taskId, taskProgress] of Object.entries(
                progress.ingest
            )) {
                // Only resume tasks for this specific source
                if (taskProgress.source_name === props.data.sourceName) {
                    if (
                        taskProgress.status === "ingesting" ||
                        taskProgress.status === "pending"
                    ) {
                        console.log(
                            `Resuming ingest progress polling for task ${taskId} (${taskProgress.source_name} ${taskProgress.file_type})`
                        )
                        // Store the progress in our tracking state
                        ingestProgressByType.value[taskProgress.file_type] =
                            taskProgress

                        // Start polling for this task
                        startPollingForTask(taskId, taskProgress.file_type)
                    }
                }
            }
        }
    } catch (error) {
        console.error("Failed to resume active ingest polling:", error)
    }
}

// Helper function to start polling for a specific task
const startPollingForTask = (taskId: string, fileType: string) => {
    const maxPolls = 300 // 5 minutes max
    let pollCount = 0

    const interval = setInterval(async () => {
        pollCount++
        try {
            const progress = await apiGet<{
                ingest: Record<string, IngestProgress>
            }>(`/api/ingest/progress`, false, {
                showSuccessToast: false,
                showErrorToast: false,
            })

            const taskProgress = progress.ingest?.[taskId]
            if (taskProgress) {
                console.log(
                    `[DEBUG] Resumed ingest progress for task ${taskId}:`,
                    taskProgress
                )
                // Update progress tracking state by file type
                ingestProgressByType.value[fileType] = taskProgress

                // Check if ingest is complete
                if (
                    taskProgress.status === "completed" ||
                    taskProgress.status === "failed" ||
                    taskProgress.status === "cancelled"
                ) {
                    console.log(
                        `Resumed ingest task ${taskId} completed with status: ${taskProgress.status}`
                    )
                    clearInterval(interval)
                    // Remove completed task from progress tracking
                    delete ingestProgressByType.value[fileType]
                    return
                }
            } else if (pollCount > 10) {
                // If task disappears from progress after 10 polls, assume it completed
                console.log(
                    `Resumed task ${taskId} no longer in progress response, assuming completed ${pollCount}`
                )
                clearInterval(interval)
                // Remove completed task from progress tracking
                delete ingestProgressByType.value[fileType]
                return
            }

            // Stop polling if we've exceeded max polls
            if (pollCount >= maxPolls) {
                console.log(
                    `Max polls reached for resumed task ${taskId}, stopping polling`
                )
                clearInterval(interval)
                // Remove timed-out task from progress tracking
                delete ingestProgressByType.value[fileType]
                return
            }
        } catch (error) {
            console.error(
                `Resume ingest progress polling error for task ${taskId}:`,
                error instanceof Error ? error.message : String(error),
                error
            )
            clearInterval(interval)
            // Remove errored task from progress tracking
            delete ingestProgressByType.value[fileType]
            return
        }
    }, 1000) // Poll every second
}

// Loading states for toolbar buttons
const isRedownloading = ref(false)
const isReingesting = ref(false)
const isRefreshing = ref(false)

// Progress tracking state
const activeDownloadProgress = ref<DownloadProgress | null>(null)

// Separate ingestion progress tracking by file type
const ingestProgressByType = ref<Record<string, IngestProgress>>({})

// Computed properties for individual file type progress
const m3uIngestProgress = computed(
    () => ingestProgressByType.value["m3u"] || null
)
const epgIngestProgress = computed(
    () => ingestProgressByType.value["epg"] || null
)

// Computed property to check if there's any active progress
const hasActiveProgress = computed(() => {
    return (
        activeDownloadProgress.value !== null ||
        m3uIngestProgress.value !== null ||
        epgIngestProgress.value !== null
    )
})

// Helper function to create SourceFileRow objects for this source
const createSourceFileRows = (): SourceFileRow[] => {
    const fileRows: SourceFileRow[] = []

    // Get table names from the tables array
    const tableNames = props.data.tables.map((table) => table.name)

    console.log(
        "Available tables for source:",
        props.data.sourceName,
        tableNames
    )

    // Add M3U file if source has M3U data
    if (tableNames.includes("m3u_channels")) {
        console.log("Adding M3U file for download")
        fileRows.push({
            fileId: `${props.data.sourceName}_m3u`,
            sourceName: props.data.sourceName,
            fileType: "m3u",
        })
    }

    // Add EPG file if source has EPG data
    if (
        tableNames.includes("epg_channels") ||
        tableNames.includes("programs")
    ) {
        console.log("Adding EPG file for download")
        fileRows.push({
            fileId: `${props.data.sourceName}_epg`,
            sourceName: props.data.sourceName,
            fileType: "epg",
        })
    }

    return fileRows
}

// Toolbar action handlers
const handleRedownload = async () => {
    console.log("Redownload source:", props.data.sourceName)

    try {
        isRedownloading.value = true
        const sourceFiles = createSourceFileRows()

        // Download all files for this source
        for (const fileRow of sourceFiles) {
            await downloadFile(fileRow, (progress) => {
                // Update progress tracking state
                activeDownloadProgress.value = progress
            })
        }

        toast.add({
            severity: "success",
            summary: "Download Started",
            detail: `Download started for source ${props.data.sourceName}`,
            life: 3000,
        })
    } catch (error) {
        console.error("Failed to redownload source:", error)
        toast.add({
            severity: "error",
            summary: "Download Failed",
            detail:
                error instanceof Error
                    ? error.message
                    : "Failed to start download",
            life: 5000,
        })
    } finally {
        isRedownloading.value = false
        // Clear progress when done
        activeDownloadProgress.value = null
    }
}

/**
 * Reingest a file with progress tracking (using SourcesTable.vue approach)
 */
const reingestFileWithProgress = async (fileRow: SourceFileRow) => {
    console.log(
        `Reingesting ${fileRow.fileType.toUpperCase()} file for source: ${fileRow.sourceName}`
    )

    try {
        const ingestEndpoint = `/api/${encodeURIComponent(fileRow.sourceName)}/loads/${fileRow.fileType}`
        const ingestResponse = await apiPost<{ task_id: string }>(
            ingestEndpoint,
            {},
            true,
            {
                successMessage: `${fileRow.fileType.toUpperCase()} processing started`,
                errorPrefix: `${fileRow.fileType.toUpperCase()} processing failed`,
            }
        )

        const taskId = ingestResponse.task_id
        console.log(
            `[DEBUG] Starting ingest progress polling for task ${taskId}...`
        )

        // Start polling for ingest progress using SourcesTable.vue approach
        let pollCount = 0
        const maxPolls = 300 // Stop after 5 minutes if no completion detected

        const interval = setInterval(async () => {
            pollCount++

            try {
                console.log(`[DEBUG] Polling ingest progress (attempt ${pollCount}) for task ${taskId}...`)
                const progress = await apiGet<{
                    ingest: Record<string, any>
                }>(`/api/ingest/progress`, false, {
                    showSuccessToast: false,
                    showErrorToast: false,
                })
                
                if (!progress) {
                    console.warn(`[DEBUG] No progress response received for task ${taskId} on attempt ${pollCount}`)
                    return
                }
                
                console.log(`[DEBUG] Progress response received:`, Object.keys(progress.ingest || {}).length, 'tasks')

                // Find our specific task in the progress response
                const taskProgress = progress.ingest?.[taskId]
                if (taskProgress) {
                    // Update progress tracking state by file type
                    ingestProgressByType.value[fileRow.fileType] = taskProgress

                    // Check if ingest is complete
                    if (
                        taskProgress.status === "completed" ||
                        taskProgress.status === "failed" ||
                        taskProgress.status === "cancelled"
                    ) {
                        console.log(
                            `Ingest task ${taskId} completed with status: ${taskProgress.status}`
                        )
                        clearInterval(interval)
                        // Remove completed task from progress tracking
                        delete ingestProgressByType.value[fileRow.fileType]
                        return
                    }
                } else if (pollCount > 10) {
                    // If task disappears from progress after 10 polls, assume it completed
                    console.log(
                        `Task ${taskId} no longer in progress response, assuming completed ${pollCount}`
                    )
                    clearInterval(interval)
                    // Remove completed task from progress tracking
                    delete ingestProgressByType.value[fileRow.fileType]
                    return
                }

                // Stop polling if we've exceeded max polls
                if (pollCount >= maxPolls) {
                    console.log(
                        `Max polls reached for task ${taskId}, stopping polling`
                    )
                    clearInterval(interval)
                    // Remove timed-out task from progress tracking
                    delete ingestProgressByType.value[fileRow.fileType]
                    return
                }
            } catch (error) {
                console.error(
                    `Ingest progress polling error for task ${taskId}:`,
                    error instanceof Error ? error.message : String(error),
                    error
                )
                clearInterval(interval)
                // Remove errored task from progress tracking
                delete ingestProgressByType.value[fileRow.fileType]
                return
            }
        }, 1000) // Poll every second

        // Wait for the polling to complete
        return new Promise<void>((resolve) => {
            const checkComplete = () => {
                if (!ingestProgressByType.value[fileRow.fileType]) {
                    resolve()
                } else {
                    setTimeout(checkComplete, 1000)
                }
            }
            checkComplete()
        })
    } catch (error) {
        console.error(
            `Failed to reingest ${fileRow.fileType} for ${fileRow.sourceName}:`,
            error
        )
        throw error
    }
}

const handleReingest = async () => {
    console.log("Reingest source:", props.data.sourceName)

    try {
        isReingesting.value = true
        const sourceFiles = createSourceFileRows()

        // Reingest all files for this source IN SERIES (one at a time)
        console.log(
            `Processing ${sourceFiles.length} files in series for ${props.data.sourceName}`
        )
        for (let i = 0; i < sourceFiles.length; i++) {
            const fileRow = sourceFiles[i]
            console.log(
                `[SERIAL] Processing file ${i + 1}/${sourceFiles.length}: ${fileRow.fileType} for ${fileRow.sourceName}`
            )

            // Wait for this file to complete before starting the next one
            await reingestFileWithProgress(fileRow)

            console.log(
                `[SERIAL] Completed file ${i + 1}/${sourceFiles.length}: ${fileRow.fileType} for ${fileRow.sourceName}`
            )
        }

        toast.add({
            severity: "success",
            summary: "Reingest Started",
            detail: `Reingest started for source ${props.data.sourceName}`,
            life: 3000,
        })
    } catch (error) {
        console.error("Failed to reingest source:", error)
        toast.add({
            severity: "error",
            summary: "Reingest Failed",
            detail:
                error instanceof Error
                    ? error.message
                    : "Failed to start reingest",
            life: 5000,
        })
    } finally {
        isReingesting.value = false
        // Clear all progress when done
        ingestProgressByType.value = {}
    }
}

const handleRefresh = async () => {
    console.log("Refresh source:", props.data.sourceName)

    try {
        isRefreshing.value = true
        const sourceFiles = createSourceFileRows()

        // Refresh (download + ingest) all files for this source
        await refreshAllFilesForSource(
            props.data.sourceName,
            sourceFiles,
            (progress) => {
                // Update progress tracking state based on progress type
                if (progress.bytes_downloaded !== undefined) {
                    // Download progress
                    activeDownloadProgress.value = progress
                    activeIngestProgress.value = null
                } else if (progress.current_step !== undefined) {
                    // Ingest progress
                    activeIngestProgress.value = progress
                    activeDownloadProgress.value = null
                }
            }
        )

        toast.add({
            severity: "success",
            summary: "Source Refresh Started",
            detail: `Refresh started for all files in source ${props.data.sourceName}`,
            life: 3000,
        })
    } catch (error) {
        console.error("Failed to refresh source:", error)
        toast.add({
            severity: "error",
            summary: "Source Refresh Failed",
            detail:
                error instanceof Error
                    ? error.message
                    : `Failed to refresh source ${props.data.sourceName}`,
            life: 5000,
        })
    } finally {
        isRefreshing.value = false
        // Clear progress when done
        activeDownloadProgress.value = null
        activeIngestProgress.value = null
    }
}

const handleSettings = () => {
    console.log("Open settings for source:", props.data.sourceName)

    // Navigate to the Sources tab where user can edit source settings
    router.push({ name: "Sources" })

    toast.add({
        severity: "info",
        summary: "Opening Sources",
        detail: `Navigate to Sources tab to configure ${props.data.sourceName}`,
        life: 3000,
    })
}

// Component lifecycle - resume active tasks when component mounts
onMounted(async () => {
    await resumeActiveIngestPolling()
})
</script>

<style scoped>
.source-node {
    background: var(--card-background);
    border: 2px solid var(--primary-color);
    border-radius: 0.5rem;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    min-width: 14rem;
    padding: 0.75rem;
    position: relative;
    transition: box-shadow 0.2s;
}

.source-node:hover {
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}

.node-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border-color);
}

.node-header i {
    color: var(--primary-color);
    font-size: 1.125rem;
}

.node-title {
    font-weight: 600;
    color: var(--text-color);
    font-size: 0.875rem;
}

.node-body {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.source-info {
    text-align: center;
}

.source-name {
    font-weight: 500;
    color: var(--text-color);
    font-size: 0.875rem;
}

.record-count {
    font-size: 0.75rem;
    color: var(--text-color);
    opacity: 0.7;
}

.stats-section {
    background: var(--card-background);
    border-radius: 0.25rem;
    padding: 0.5rem;
    border: 1px solid var(--border-color);
}

.stat-item {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
}

.table-stat {
    border-left: 3px solid;
    padding-left: 0.5rem;
    margin-left: -0.5rem;
    margin-top: 0.25rem;
}

.stat-label {
    color: var(--text-color);
    opacity: 0.7;
}

.stat-value {
    font-weight: 500;
    color: var(--primary-color);
}

.execution-status {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.75rem;
    color: var(--primary-color);
    background: var(--hover-color);
    border-radius: 0.25rem;
    padding: 0.25rem 0.5rem;
}

.output-handle {
    background: var(--primary-color);
    border: 2px solid var(--card-background);
    width: 0.75rem;
    height: 0.75rem;
}

.output-handle:hover {
    background: var(--primary-color);
    opacity: 0.8;
}

.table-handle {
    background: var(--primary-color);
}

.handle-label {
    @apply absolute right-0 text-xs font-medium pointer-events-none;
    @apply bg-white px-1 rounded shadow-sm border;
    transform: translateX(100%);
}

.table-label {
    @apply text-blue-700 border-blue-200;
}

.handle-label.table-label {
    background-color: var(--primary-color);
    color: white;
    padding: 0.125rem 0.375rem;
    border-radius: 0.25rem;
    font-size: 0.75rem;
    font-weight: 500;
    white-space: nowrap;
    pointer-events: none;
    z-index: 1000;
    position: absolute;
    right: -0.375rem;
    transform: translateX(50%) translateY(-50%);
}

/* Progress Container Styles */
.ingest-progress-container {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

/* Dual Progress Containers */
.dual-progress-container {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin-top: 0.5rem;
}

.progress-section {
    background: var(--surface-50);
    border: 1px solid var(--surface-200);
    border-radius: 0.5rem;
    padding: 0.75rem;
    position: relative;
}

.progress-section.m3u {
    border-left: 4px solid #10b981; /* Green accent for M3U */
}

.progress-section.epg {
    border-left: 4px solid #3b82f6; /* Blue accent for EPG */
}

.progress-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
    font-weight: 600;
    font-size: 0.875rem;
    color: var(--text-color);
}

.progress-header i {
    font-size: 1rem;
}

.progress-header.m3u {
    color: #059669; /* Darker green for M3U */
}

.progress-header.epg {
    color: #2563eb; /* Darker blue for EPG */
}

.step-info {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
}

.step-indicator {
    font-weight: 600;
    color: var(--p-primary-color);
    font-size: 0.75rem;
}

.step-name {
    font-weight: 500;
    color: var(--p-text-color);
    text-transform: capitalize;
}

.progress-details {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.75rem;
    color: var(--p-text-muted-color);
}

.progress-items {
    font-weight: 500;
}

.progress-current-item {
    font-weight: 500;
    color: var(--p-text-color);
}

.download-progress-container {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.progress-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.75rem;
    color: var(--p-text-muted-color);
}

.progress-status {
    font-weight: 500;
    color: var(--p-text-color);
}

.progress-bytes {
    font-weight: 500;
}

/* Toolbar Styles */
.toolbar-buttons {
    display: flex;
    gap: 0.25rem;
    background: var(--surface-ground);
    border: 1px solid var(--surface-border);
    border-radius: 0.375rem;
    padding: 0.25rem;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.toolbar-buttons :deep(.p-button) {
    width: 2rem;
    height: 2rem;
    border-radius: 0.25rem;
}

.toolbar-buttons :deep(.p-button:hover) {
    transform: translateY(-1px);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
</style>
