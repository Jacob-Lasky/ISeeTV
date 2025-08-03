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
                    <!-- Show multi-step progress if file is being processed -->
                    <div
                        v-if="activeIngestProgress"
                        class="ingest-progress-container"
                    >
                        <div class="step-info">
                            <span class="step-indicator">
                                Step
                                {{ activeIngestProgress.current_step || 1 }}/{{
                                    activeIngestProgress.total_steps || 3
                                }}:
                            </span>
                            <span class="step-name">
                                {{
                                    formatStepName(
                                        activeIngestProgress.step_name
                                    )
                                }}
                            </span>
                        </div>
                        <div class="progress-details">
                            <span
                                v-if="activeIngestProgress.total_items > 0"
                                class="progress-items"
                            >
                                {{ activeIngestProgress.completed_items || 0 }}
                                /
                                {{ activeIngestProgress.total_items }}
                                items
                            </span>
                            <span
                                v-else-if="
                                    activeIngestProgress.completed_items > 0
                                "
                                class="progress-items"
                            >
                                {{
                                    formatNumber(
                                        activeIngestProgress.completed_items ||
                                            0
                                    )
                                }}
                                records processed
                            </span>
                            <span
                                v-else-if="activeIngestProgress.current_item"
                                class="progress-current-item"
                            >
                                {{ activeIngestProgress.current_item }}
                            </span>
                        </div>
                        <!-- Progress bar: step-specific progress or indeterminate -->
                        <ProgressBar
                            v-if="getStepProgressValue() !== null"
                            :value="getStepProgressValue()"
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
                                Downloading {{ activeDownloadProgress.file_type?.toUpperCase() || 'file' }}:
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
import { computed, inject, ref } from "vue"
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

const getStepProgressValue = (): number | null => {
    if (!activeIngestProgress.value) return null

    const progress = activeIngestProgress.value
    if (progress.total_items > 0) {
        return Math.round(
            (progress.completed_items / progress.total_items) * 100
        )
    }
    return null // Indeterminate progress
}

// Router and toast for navigation and notifications
const router = useRouter()
const toast = useToast()

// Loading states for toolbar buttons
const isRedownloading = ref(false)
const isReingesting = ref(false)
const isRefreshing = ref(false)

// Progress tracking state
const activeDownloadProgress = ref<DownloadProgress | null>(null)
const activeIngestProgress = ref<IngestProgress | null>(null)

// Computed property to check if there's any active progress
const hasActiveProgress = computed(() => {
    return (
        activeDownloadProgress.value !== null ||
        activeIngestProgress.value !== null
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

    console.log("Created file rows for download:", fileRows)
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

const handleReingest = async () => {
    console.log("Reingest source:", props.data.sourceName)

    try {
        isReingesting.value = true
        const sourceFiles = createSourceFileRows()

        // Reingest all files for this source
        for (const fileRow of sourceFiles) {
            await reingestFile(fileRow, (progress) => {
                // Update progress tracking state
                activeIngestProgress.value = progress
            })
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
        // Clear progress when done
        activeIngestProgress.value = null
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

        // Note: refreshAllFilesForSource already shows success toast
    } catch (error) {
        console.error("Failed to refresh source:", error)
        // Error toast is already shown by refreshAllFilesForSource
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
