<template>
    <div>
        <!-- Refresh All Actions -->
        <div class="refresh-all-actions">
            <div class="refresh-all-buttons">
                <Button
                    label="Refresh All M3U"
                    icon="pi pi-refresh"
                    severity="info"
                    size="small"
                    :loading="refreshingAllM3u"
                    @click="refreshAllM3u"
                />
                <Button
                    label="Refresh All EPG"
                    icon="pi pi-refresh"
                    severity="info"
                    size="small"
                    :loading="refreshingAllEpg"
                    @click="refreshAllEpg"
                />
            </div>
        </div>

        <DataTable
            v-model:editingRows="editingRows"
            :value="sourceFileRows"
            rowGroupMode="subheader"
            groupRowsBy="sourceName"
            sortMode="single"
            sortField="sourceName"
            :sortOrder="1"
            responsiveLayout="scroll"
            showGridlines
            :rows="20"
            editMode="row"
            dataKey="fileId"
            scrollable
            scrollHeight="600px"
            :pt="{
                table: { style: 'width: 100%; min-width: 80rem' },
                column: {
                    bodycell: ({ state }) => ({
                        style:
                            state['d_editing'] &&
                            'padding-top: 0.75rem; padding-bottom: 0.75rem',
                    }),
                },
            }"
            @row-edit-save="onRowEditSave"
        >
            <!-- Source Name Column (for grouping) -->
            <Column
                field="sourceName"
                header="Source"
                style="display: none"
            ></Column>

            <!-- File Type Column -->
            <Column
                field="fileType"
                header="File Type"
                style="min-width: 120px"
            >
                <template #body="{ data }">
                    <div
                        v-if="data._isSkeleton"
                        class="file-type flex items-center gap-2"
                    >
                        <Skeleton
                            shape="circle"
                            size="1.5rem"
                            class="mr-2"
                        ></Skeleton>
                        <Skeleton width="4rem" height="1rem"></Skeleton>
                    </div>
                    <div
                        v-else
                        style="display: flex; align-items: center; gap: 16px"
                    >
                        <i
                            :class="getFileTypeIcon(data.fileType)"
                            :style="{ color: getFileTypeColor(data.fileType) }"
                        ></i>
                        <span
                            style="text-transform: uppercase; font-weight: 600"
                            >{{ data.fileType }}</span
                        >
                    </div>
                </template>
            </Column>

            <!-- File Actions Column -->
            <Column
                header="File Actions"
                style="width: 150px; min-width: 120px"
            >
                <template #body="{ data }">
                    <div v-if="data._isSkeleton" class="action-buttons">
                        <Skeleton
                            shape="circle"
                            size="2rem"
                            class="mr-1"
                        ></Skeleton>
                        <Skeleton shape="circle" size="2rem"></Skeleton>
                    </div>
                    <div v-else class="action-buttons">
                        <!-- Show stop button if file is downloading, refresh button otherwise -->
                        <Button
                            v-if="getProgressForFile(data.fileId)"
                            icon="pi pi-stop"
                            severity="danger"
                            size="small"
                            rounded
                            :title="`Stop ${data.fileType.toUpperCase()} download`"
                            @click="cancelDownload(data)"
                        />
                        <Button
                            v-else
                            icon="pi pi-refresh"
                            severity="secondary"
                            size="small"
                            rounded
                            :title="`Refresh ${data.fileType.toUpperCase()} file`"
                            @click="refreshFile(data)"
                        />
                        <Button
                            icon="pi pi-download"
                            severity="success"
                            size="small"
                            text
                            rounded
                            :title="`Download ${data.fileType.toUpperCase()} file`"
                            @click="downloadFile(data)"
                        />
                    </div>
                </template>
            </Column>

            <!-- File Last Refresh Column -->
            <Column
                field="fileLastRefresh"
                header="Last Refresh"
                style="min-width: 200px"
            >
                <template #body="{ data }">
                    <Skeleton
                        v-if="data._isSkeleton"
                        width="8rem"
                        height="1rem"
                    ></Skeleton>
                    <div v-else class="last-refresh-cell">
                        <!-- Show progress bar if file is currently downloading -->
                        <div
                            v-if="getProgressForFile(data.fileId)"
                            class="progress-container"
                        >
                            <div class="progress-info">
                                <span class="progress-status">{{
                                    getProgressForFile(data.fileId)?.status
                                }}</span>
                                <span
                                    v-if="
                                        getProgressForFile(data.fileId)
                                            ?.total_bytes > 0
                                    "
                                    class="progress-bytes"
                                >
                                    {{
                                        formatBytes(
                                            getProgressForFile(data.fileId)
                                                ?.bytes_downloaded || 0
                                        )
                                    }}
                                    /
                                    {{
                                        formatBytes(
                                            getProgressForFile(data.fileId)
                                                ?.total_bytes || 0
                                        )
                                    }}
                                </span>
                                <span v-else class="progress-bytes">
                                    {{
                                        formatBytes(
                                            getProgressForFile(data.fileId)
                                                ?.bytes_downloaded || 0
                                        )
                                    }}
                                    downloaded
                                </span>
                            </div>
                            <ProgressBar
                                v-if="
                                    getProgressForFile(data.fileId)
                                        ?.total_bytes > 0
                                "
                                :value="
                                    Math.round(
                                        ((getProgressForFile(data.fileId)
                                            ?.bytes_downloaded || 0) /
                                            (getProgressForFile(data.fileId)
                                                ?.total_bytes || 1)) *
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
                        <!-- Show last refresh status if not downloading -->
                        <span
                            v-else
                            :class="getRefreshStatusClass(data.fileMetadata)"
                        >
                            {{ formatRefreshStatus(data.fileMetadata) }}
                        </span>
                    </div>
                </template>
            </Column>

            <!-- File URL Column -->
            <Column field="fileUrl" header="URL" style="width: 300px">
                <template #body="{ data }">
                    <div v-if="data._isSkeleton">
                        <Skeleton width="100%" height="1rem"></Skeleton>
                    </div>
                    <div v-else class="url-cell" :title="data.fileUrl">
                        {{ data.fileUrl }}
                    </div>
                </template>
                <template #editor="{ data }">
                    <InputText
                        :model-value="data.fileUrl"
                        fluid
                        @update:model-value="data.fileUrl = $event"
                    />
                </template>
            </Column>

            <!-- Group Header Template - Source Metadata -->
            <template #groupheader="{ data }">
                <!-- Skeleton Group Header -->
                <div v-if="data._isSkeleton" class="source-group-header">
                    <div class="source-header-main">
                        <div class="source-name">
                            <Skeleton
                                shape="circle"
                                size="1.5rem"
                                class="mr-2"
                            ></Skeleton>
                            <Skeleton width="12rem" height="1.5rem"></Skeleton>
                        </div>
                        <div class="source-actions">
                            <Skeleton
                                shape="circle"
                                size="2rem"
                                class="mr-1"
                            ></Skeleton>
                            <Skeleton shape="circle" size="2rem"></Skeleton>
                        </div>
                    </div>
                    <div class="source-metadata">
                        <div class="metadata-item">
                            <Skeleton
                                width="4rem"
                                height="1rem"
                                class="mr-2"
                            ></Skeleton>
                            <Skeleton width="5rem" height="1.5rem"></Skeleton>
                        </div>
                        <div class="metadata-item">
                            <Skeleton
                                width="6rem"
                                height="1rem"
                                class="mr-2"
                            ></Skeleton>
                            <Skeleton width="2rem" height="1rem"></Skeleton>
                        </div>
                        <div class="metadata-item">
                            <Skeleton
                                width="4rem"
                                height="1rem"
                                class="mr-2"
                            ></Skeleton>
                            <Skeleton width="3rem" height="1rem"></Skeleton>
                        </div>
                        <div class="metadata-item">
                            <Skeleton
                                width="5rem"
                                height="1rem"
                                class="mr-2"
                            ></Skeleton>
                            <Skeleton width="4rem" height="1rem"></Skeleton>
                        </div>
                        <div class="metadata-item">
                            <Skeleton
                                width="4rem"
                                height="1rem"
                                class="mr-2"
                            ></Skeleton>
                            <Skeleton width="5rem" height="1rem"></Skeleton>
                        </div>
                    </div>
                </div>
                <!-- Normal Group Header -->
                <div v-else class="source-group-header">
                    <div class="source-header-main">
                        <div class="source-name">
                            <i class="pi pi-server" style="color: #6366f1"></i>
                            <span class="font-bold text-lg">{{
                                data.sourceName
                            }}</span>
                        </div>
                        <div class="source-actions">
                            <Button
                                icon="pi pi-pencil"
                                severity="info"
                                size="small"
                                text
                                rounded
                                title="Edit source"
                                @click="editSource(data.sourceId)"
                            />
                            <Button
                                icon="pi pi-trash"
                                severity="danger"
                                size="small"
                                text
                                rounded
                                title="Delete source"
                                @click="deleteSource(data.sourceId)"
                            />
                        </div>
                    </div>
                    <div class="source-metadata">
                        <div class="metadata-item">
                            <span class="metadata-label">Status:</span>
                            <Tag
                                :value="
                                    data.sourceEnabled ? 'Enabled' : 'Disabled'
                                "
                                :severity="
                                    data.sourceEnabled ? 'success' : 'danger'
                                "
                            />
                        </div>
                        <div class="metadata-item">
                            <span class="metadata-label">Connections:</span>
                            <span class="metadata-value">{{
                                data.sourceConnections || 1
                            }}</span>
                        </div>
                        <div class="metadata-item">
                            <span class="metadata-label">Refresh:</span>
                            <span class="metadata-value"
                                >{{ data.sourceRefreshHours || 24 }}h</span
                            >
                        </div>
                        <div class="metadata-item">
                            <span class="metadata-label">Timezone:</span>
                            <span class="metadata-value">{{
                                data.sourceTimezone || "UTC"
                            }}</span>
                        </div>
                        <div class="metadata-item">
                            <span class="metadata-label">Expires:</span>
                            <span class="metadata-value">{{
                                formatSubscriptionExpires(
                                    data.sourceSubscriptionExpires
                                )
                            }}</span>
                        </div>
                    </div>
                </div>
            </template>
        </DataTable>
        <br />
        <Button
            label="New Source"
            icon="pi pi-plus"
            class="mt-4"
            @click="openNewSourceDialog"
        />

        <Dialog
            v-model:visible="showSourceModal"
            :header="isEditMode ? 'Edit Source' : 'New Source'"
            :modal="true"
            :closable="false"
            :closeOnEscape="true"
            class="source-dialog"
        >
            <form @submit.prevent="saveSource">
                <div class="form-grid">
                    <div class="form-row">
                        <label>Name:</label>
                        <InputText v-model="sourceForm.name" required fluid />
                    </div>
                    <div class="form-row">
                        <label>Enabled:</label>
                        <Select
                            v-model="sourceForm.enabled"
                            :options="[
                                { label: 'Yes', value: true },
                                { label: 'No', value: false },
                            ]"
                            optionLabel="label"
                            optionValue="value"
                            fluid
                        />
                    </div>
                    <div class="form-row">
                        <label>Connections:</label>
                        <InputNumber
                            v-model="sourceForm.connections"
                            :min="1"
                            fluid
                        />
                    </div>
                    <div class="form-row">
                        <label>Timezone:</label>
                        <Select
                            v-model="sourceForm.timezone"
                            :options="timezoneOptions"
                            optionLabel="label"
                            optionValue="value"
                            placeholder="Select timezone"
                            fluid
                        />
                    </div>
                    <div class="form-row">
                        <label>Subscription Expires:</label>
                        <DatePicker
                            v-model="sourceForm.subscriptionExpires"
                            dateFormat="yy-mm-dd"
                            showIcon
                            fluid
                        />
                    </div>
                    <div class="form-row">
                        <label>Refresh Hours:</label>
                        <InputNumber
                            v-model="sourceForm.refreshHours"
                            :min="1"
                            fluid
                        />
                    </div>
                    <!-- M3U section -->
                    <div class="form-row">
                        <label>M3U URL:</label>
                        <InputText v-model="sourceForm.m3uUrl" required fluid />
                    </div>
                    <!-- EPG section -->
                    <div class="form-row">
                        <label>EPG URL:</label>
                        <InputText v-model="sourceForm.epgUrl" fluid />
                    </div>
                </div>
            </form>
            <template #footer>
                <div class="dialog-footer">
                    <Button
                        label="Cancel"
                        icon="pi pi-times"
                        severity="secondary"
                        text
                        @click="cancelSourceDialog"
                    />
                    <Button
                        label="Save"
                        icon="pi pi-check"
                        severity="success"
                        @click="saveSource"
                    />
                </div>
            </template>
        </Dialog>

        <!-- Delete Confirmation Dialog -->
        <Dialog
            v-model:visible="showDeleteDialog"
            header="Delete Confirmation"
            :modal="true"
            :closable="false"
            :closeOnEscape="true"
            class="delete-dialog"
        >
            <div class="confirmation-content">
                <i
                    class="pi pi-exclamation-triangle mr-3"
                    style="font-size: 2rem; color: var(--orange-500)"
                ></i>
                <span>Are you sure you want to delete this source?</span>
            </div>
            <template #footer>
                <div class="dialog-footer">
                    <Button
                        label="No"
                        icon="pi pi-times"
                        text
                        class="p-button-secondary"
                        @click="showDeleteDialog = false"
                    />
                    <Button
                        label="Yes"
                        icon="pi pi-check"
                        severity="danger"
                        @click="confirmDelete"
                    />
                </div>
            </template>
        </Dialog>

        <p v-if="error" class="error">{{ error }}</p>
        <p v-if="saveSuccess" class="success">{{ saveSuccess }}</p>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import DataTable from "primevue/datatable"
import Column from "primevue/column"
import Button from "primevue/button"
import InputText from "primevue/inputtext"
import InputNumber from "primevue/inputnumber"
import Select from "primevue/select"
import Dialog from "primevue/dialog"
import Tag from "primevue/tag"
import DatePicker from "primevue/datepicker"
import Skeleton from "primevue/skeleton"
import ProgressBar from "primevue/progressbar"
import { apiGet, apiPost } from "../utils/apiUtils"
import type {
    FileMetadata,
    Source,
    SourceFileRow,
    DownloadTaskResponse,
    DownloadAllTasksResponse,
    DownloadProgress,
} from "../types/types"
import { timezoneOptions } from "../utils/timezones"

// Reactive state for sources and UI
const sources = ref<Source[]>([])
const editingRows = ref([])
const loading = ref(true)
const error = ref("")
const saveSuccess = ref("")

// Refresh all loading states
const refreshingAllM3u = ref(false)
const refreshingAllEpg = ref(false)

// Task ID tracking for progress bars
const activeTaskIds = ref<Map<string, string>>(new Map()) // fileId -> taskId
const downloadProgress = ref<Map<string, DownloadProgress>>(new Map()) // taskId -> progress
const progressPollingIntervals = ref<Map<string, number>>(new Map()) // taskId -> interval

// Data transformation
const sourceFileRows = computed<SourceFileRow[]>(() => {
    if (loading.value) {
        // Return skeleton data during loading
        return createSkeletonRows()
    }

    return transformSourcesToRows(sources.value)
})

// Transform sources to normalized row structure
function transformSourcesToRows(sourcesData: Source[]): SourceFileRow[] {
    const rows: SourceFileRow[] = []

    sourcesData.forEach((source, sourceIndex) => {
        const sourceId = `source-${sourceIndex}-${source.name}`
        const fileTypes: Array<"m3u" | "epg"> = ["m3u", "epg"]

        fileTypes.forEach((fileType, fileIndex) => {
            const fileMetadata = source.file_metadata?.[fileType]
            if (!fileMetadata) return // Skip if file metadata doesn't exist

            const row: SourceFileRow = {
                // Source fields (will be row-spanned)
                sourceId,
                sourceName: source.name,
                sourceEnabled: source.enabled,
                sourceTimezone: source.source_timezone,
                sourceConnections: source.number_of_connections,
                sourceRefreshHours: source.refresh_every_hours,
                sourceSubscriptionExpires: source.subscription_expires,

                // File fields (unique per row)
                fileId: `${sourceId}-${fileType}`,
                fileType,
                fileUrl: fileMetadata.url,
                fileLastRefreshStartedTimestamp:
                    fileMetadata.last_refresh_started_timestamp || null,
                fileLastRefreshFinishedTimestamp:
                    fileMetadata.last_refresh_finished_timestamp || null,
                fileSizeBytes: fileMetadata.last_size_bytes,
                fileStatus: determineFileStatus(fileMetadata),
                fileMetadata: fileMetadata,

                // UI helpers for rowspan logic
                isFirstFileForSource: fileIndex === 0,
                rowSpanCount: fileTypes.length,
            }

            rows.push(row)
        })
    })

    return rows
}

// Determine file status based on metadata
function determineFileStatus(
    fileMetadata: FileMetadata
): "active" | "inactive" | "error" {
    if (!fileMetadata.url) return "inactive"
    if (fileMetadata.last_refresh_started_timestamp) return "active"
    return "inactive"
}

// Create skeleton rows for loading state
function createSkeletonRows(): SourceFileRow[] {
    return Array.from(
        { length: 1 },
        (_, index) =>
            ({
                sourceId: `skeleton-${index}`,
                sourceName: `Skeleton Source ${index + 1}`,
                sourceEnabled: true,
                sourceTimezone: "UTC",
                sourceConnections: 1,
                sourceRefreshHours: 24,
                sourceSubscriptionExpires: null,
                fileId: `skeleton-file-${index}-m3u`,
                fileType: "m3u" as const,
                fileUrl: "skeleton-url",
                fileLastRefreshStartedTimestamp: null,
                fileLastRefreshFinishedTimestamp: null,
                fileSizeBytes: 0,
                fileStatus: "active" as const,
                isFirstFileForSource: true,
                rowSpanCount: 1,
                _isSkeleton: true, // Flag to identify skeleton rows
            }) as SourceFileRow & { _isSkeleton: boolean }
    )
}

/**
 * Utility functions for UI display and interactions
 */

// Get file type icon
function getFileTypeIcon(fileType: "m3u" | "epg"): string {
    switch (fileType) {
        case "m3u":
            return "pi pi-list"
        case "epg":
            return "pi pi-calendar"
        default:
            return "pi pi-file"
    }
}

// Get file type color
function getFileTypeColor(fileType: "m3u" | "epg"): string {
    switch (fileType) {
        case "m3u":
            return "#10b981" // green
        case "epg":
            return "#3b82f6" // blue
        default:
            return "#6b7280" // gray
    }
}

// User timezone state for atomic timezone-aware formatting
const userTimezone = ref<string>("UTC")

// Atomic function to fetch user timezone from settings
async function fetchUserTimezone(): Promise<void> {
    try {
        const settings = await apiGet("/api/settings", false, {
            showSuccessToast: false,
            errorPrefix: "Failed to load timezone settings",
        })
        if (settings?.user_timezone) {
            userTimezone.value = settings.user_timezone
        }
    } catch (error) {
        console.warn("Could not fetch user timezone, using UTC:", error)
        userTimezone.value = "UTC"
    }
}

function formatSubscriptionExpires(expiresDate: string | null): string {
    if (!expiresDate) return "Never"

    const date = new Date(expiresDate)
    if (isNaN(date.getTime())) return "Invalid date"

    // Format to yyyy-mm-dd
    const year = date.getFullYear().toString() // Year
    const month = (date.getMonth() + 1).toString().padStart(2, "0") // Month (1-12) with leading zero
    const day = date.getDate().toString().padStart(2, "0") // Day with leading zero

    return `${year}-${month}-${day}`
}

/**
 * Action handlers for file and source operations
 */

async function loadSources() {
    sources.value = await apiGet("/api/sources", false, {
        showSuccessToast: true,
        errorPrefix: "Failed to load sources",
    })
}

// Smart reload that preserves active downloads
async function preserveActiveDownloadsAndReload() {
    // Capture current active downloads before reload
    const activeDownloads = new Map(activeTaskIds.value)

    // Reload sources data
    await loadSources()

    // Restore active downloads and restart progress polling
    for (const [fileId, taskId] of activeDownloads) {
        // Check if this task is still active on the backend
        try {
            const progress = await fetch(`/api/download/progress/${taskId}`)
            if (progress.ok) {
                const progressData = await progress.json()
                // Only restore if download is still active (not completed/failed/cancelled)
                if (
                    progressData.status === "downloading" ||
                    progressData.status === "pending"
                ) {
                    activeTaskIds.value.set(fileId, taskId)
                    downloadProgress.value.set(taskId, progressData)
                    // Restart progress polling for this task
                    startProgressPolling(taskId, fileId)
                }
            }
        } catch {
            // If we can't check the task, assume it's no longer active
            console.log(
                `Task ${taskId} no longer active, not restoring progress polling`
            )
        }
    }
}

// Auto-detect active downloads on component mount (for tab navigation persistence)
async function detectAndRestoreActiveDownloads() {
    console.log("Starting auto-detection of active downloads...")
    try {
        // Get all active downloads from the backend
        const response = await fetch("/api/download/progress")
        console.log("Fetch response status:", response.status, response.ok)

        if (!response.ok) {
            console.log("No active downloads to restore (response not ok)")
            return
        }

        const allProgress = await response.json()
        console.log("All progress data from backend:", allProgress)
        console.log("Number of tasks found:", Object.keys(allProgress).length)

        // For each active download, find the corresponding file and restore progress polling
        for (const [taskId, progressData] of Object.entries(allProgress)) {
            const progress = progressData as DownloadProgress
            console.log(`Processing task ${taskId}:`, {
                status: progress.status,
                current_item: progress.current_item,
                total_items: progress.total_items,
                completed_items: progress.completed_items,
            })

            // Only restore downloads that are still active
            if (
                progress.status === "downloading" ||
                progress.status === "pending"
            ) {
                console.log(
                    `Task ${taskId} is active, looking for matching file...`
                )

                // Find the file that matches this task
                const fileId = findFileIdForTask(
                    taskId,
                    progress.current_item,
                    progress.file_type
                )
                console.log(`File ID match result for ${taskId}:`, fileId)

                if (fileId) {
                    console.log(
                        `Restoring progress for ${progress.current_item} (${taskId}) -> ${fileId}`
                    )
                    activeTaskIds.value.set(fileId, taskId)
                    downloadProgress.value.set(taskId, progress)
                    // Start progress polling for this task
                    startProgressPolling(taskId, fileId)
                    console.log(`Progress polling started for ${taskId}`)
                } else {
                    console.log(
                        `Could not find matching file for task ${taskId} (source: ${progress.current_item})`
                    )
                }
            } else {
                console.log(
                    `Task ${taskId} is not active (status: ${progress.status}), skipping`
                )
            }
        }

        console.log("Auto-detection completed")
    } catch (error) {
        console.log("Failed to detect active downloads:", error)
    }
}

// Helper function to find fileId based on progress data
function findFileIdForTask(
    taskId: string,
    sourceName: string | null,
    fileType?: string | null
): string | null {
    console.log(
        `Finding file ID for task: ${taskId}, source: ${sourceName}, fileType: ${fileType}`
    )

    if (!sourceName) {
        console.log(`No source name provided for task ${taskId}`)
        return null
    }

    console.log(
        `Available source rows:`,
        sourceFileRows.value.map((row) => ({
            fileId: row.fileId,
            sourceName: row.sourceName,
            fileType: row.fileType,
        }))
    )

    // Find the matching file in our current sources
    for (const row of sourceFileRows.value) {
        console.log(
            `Checking row: ${row.sourceName} (${row.fileType}) vs ${sourceName} (${fileType})`
        )
        if (row.sourceName === sourceName && row.fileType === fileType) {
            console.log(`Found match! File ID: ${row.fileId}`)
            return row.fileId
        }
    }

    console.log(`No matching file found for ${sourceName} (${fileType})`)
    return null
}

// File-specific actions
async function refreshFile(fileRow: SourceFileRow) {
    console.log(
        `Refreshing ${fileRow.fileType.toUpperCase()} file for source: ${fileRow.sourceName}`
    )

    try {
        const endpoint = `/api/download/${fileRow.fileType}/${encodeURIComponent(fileRow.sourceName)}`

        const response = await apiGet<DownloadTaskResponse>(endpoint, true, {
            successMessage: `${fileRow.fileType.toUpperCase()} refresh started`,
            errorPrefix: `${fileRow.fileType.toUpperCase()} refresh failed`,
        })

        // Start progress polling for this file
        startProgressPolling(response.task_id, fileRow.fileId)
    } catch (error) {
        console.error(
            `Failed to refresh ${fileRow.fileType} for ${fileRow.sourceName}:`,
            error
        )
    }
}

// Refresh all M3U files
async function refreshAllM3u() {
    console.log("Refreshing all M3U files")

    try {
        refreshingAllM3u.value = true

        const response = await apiGet<DownloadAllTasksResponse>(
            "/api/download/m3u/all",
            true,
            {
                successMessage: "All M3U refresh started",
                errorPrefix: "All M3U refresh failed",
            }
        )

        // Start progress polling for each task
        response.task_ids.forEach((taskId) => {
            // Find the corresponding file for this task
            const fileRows = sourceFileRows.value.filter(
                (row) => row.fileType === "m3u"
            )
            const matchingRow = fileRows.find((row) => {
                // Match by source name and file type (task ID format: sourceName_fileType_timestamp)
                return taskId.includes(row.sourceName.replace(/\s+/g, "_"))
            })

            if (matchingRow) {
                startProgressPolling(taskId, matchingRow.fileId)
            }
        })
    } catch (error) {
        console.error("Failed to refresh all M3U files:", error)
    } finally {
        refreshingAllM3u.value = false
    }
}

// Refresh all EPG files
async function refreshAllEpg() {
    console.log("Refreshing all EPG files")

    try {
        refreshingAllEpg.value = true

        const response = await apiGet<DownloadAllTasksResponse>(
            "/api/download/epg/all",
            true,
            {
                successMessage: "All EPG refresh started",
                errorPrefix: "All EPG refresh failed",
            }
        )

        // Start progress polling for each task
        response.task_ids.forEach((taskId) => {
            // Find the corresponding file for this task
            const fileRows = sourceFileRows.value.filter(
                (row) => row.fileType === "epg"
            )
            const matchingRow = fileRows.find((row) => {
                // Match by source name and file type (task ID format: sourceName_fileType_timestamp)
                return taskId.includes(row.sourceName.replace(/\s+/g, "_"))
            })

            if (matchingRow) {
                startProgressPolling(taskId, matchingRow.fileId)
            }
        })
    } catch (error) {
        console.error("Failed to refresh all EPG files:", error)
    } finally {
        refreshingAllEpg.value = false
    }
}

// Progress tracking functions
function startProgressPolling(taskId: string, fileId: string) {
    // Store the task ID for this file
    activeTaskIds.value.set(fileId, taskId)

    // Start polling for progress
    const interval = setInterval(async () => {
        try {
            const progress = await apiGet<DownloadProgress>(
                `/api/download/progress/${taskId}`,
                false,
                {
                    showSuccessToast: false,
                    showErrorToast: false,
                }
            )

            downloadProgress.value.set(taskId, progress)

            // Check if download is complete
            if (
                progress.status === "completed" ||
                progress.status === "failed" ||
                progress.status === "cancelled"
            ) {
                stopProgressPolling(taskId, fileId)
                // Note: Sources will be updated automatically when user refreshes or navigates
                // No need to call loadSources() here as it causes excessive API calls
            }
        } catch (error) {
            console.error(`Failed to fetch progress for task ${taskId}:`, error)
            // Stop polling on error
            stopProgressPolling(taskId, fileId)
        }
    }, 1000) // Poll every second

    progressPollingIntervals.value.set(taskId, interval)
}

function stopProgressPolling(taskId: string, fileId: string) {
    const interval = progressPollingIntervals.value.get(taskId)
    if (interval) {
        clearInterval(interval)
        progressPollingIntervals.value.delete(taskId)
    }

    activeTaskIds.value.delete(fileId)
    downloadProgress.value.delete(taskId)
}

function getProgressForFile(fileId: string): DownloadProgress | null {
    const taskId = activeTaskIds.value.get(fileId)
    if (!taskId) return null

    return downloadProgress.value.get(taskId) || null
}

// Utility function to format bytes
function formatBytes(bytes: number, decimals = 2): string {
    if (bytes === 0) return "0 Bytes"

    const k = 1024
    const dm = decimals < 0 ? 0 : decimals
    const sizes = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]

    const i = Math.floor(Math.log(bytes) / Math.log(k))

    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i]
}

// Utility function to format refresh status with relative time
function formatRefreshStatus(metadata: FileMetadata | undefined): string {
    if (
        !metadata ||
        !metadata.last_refresh_status ||
        !metadata.last_refresh_finished_timestamp
    ) {
        return "Never refreshed"
    }

    const timestamp = new Date(metadata.last_refresh_finished_timestamp)
    const now = new Date()
    const diffMs = now.getTime() - timestamp.getTime()

    // Convert to relative time
    const minutes = Math.floor(diffMs / (1000 * 60))
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)

    let timeAgo: string
    if (minutes < 1) {
        timeAgo = "Just now"
    } else if (minutes < 60) {
        timeAgo = `${minutes} minute${minutes === 1 ? "" : "s"} ago`
    } else if (hours < 24) {
        timeAgo = `${hours} hour${hours === 1 ? "" : "s"} ago`
    } else {
        timeAgo = `${days} day${days === 1 ? "" : "s"} ago`
    }

    // Format status with proper capitalization
    const status =
        metadata.last_refresh_status.charAt(0).toUpperCase() +
        metadata.last_refresh_status.slice(1)

    return `${status}: ${timeAgo}`
}

// Utility function to get CSS class based on refresh status
function getRefreshStatusClass(metadata: FileMetadata | undefined): string {
    const baseClass = "last-refresh-status"

    if (!metadata || !metadata.last_refresh_status) {
        return `${baseClass} status-never`
    }

    switch (metadata.last_refresh_status) {
        case "success":
            return `${baseClass} status-success`
        case "failed":
            return `${baseClass} status-failed`
        case "cancelled":
            return `${baseClass} status-cancelled`
        default:
            return `${baseClass} status-never`
    }
}

async function downloadFile(fileRow: SourceFileRow) {
    console.log(
        `Downloading ${fileRow.fileType.toUpperCase()} file for source: ${fileRow.sourceName}`
    )

    try {
        const endpoint = `/api/download/file/${encodeURIComponent(fileRow.sourceName)}/${fileRow.fileType}`

        // Create a temporary link to trigger the download
        const link = document.createElement("a")
        link.href = endpoint
        link.download = `${fileRow.sourceName}_${fileRow.fileType}.${fileRow.fileType}`
        link.style.display = "none"

        // Add to DOM, click, and remove
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)

        console.log(
            `Download started for ${fileRow.fileType.toUpperCase()} file from ${fileRow.sourceName}`
        )
    } catch (error) {
        console.error(
            `Failed to download ${fileRow.fileType} for ${fileRow.sourceName}:`,
            error
        )
    }
}

// Cancel download function
async function cancelDownload(fileRow: SourceFileRow) {
    console.log(
        `Cancelling ${fileRow.fileType.toUpperCase()} download for source: ${fileRow.sourceName}`
    )

    try {
        const taskId = activeTaskIds.value.get(fileRow.fileId)
        if (!taskId) {
            console.warn("No active task found for file:", fileRow.fileId)
            return
        }

        const endpoint = `/api/download/cancel/${taskId}`

        // Use apiGet with DELETE method (note: apiGet can handle different HTTP methods)
        await fetch(endpoint, {
            method: "DELETE",
            headers: {
                "Content-Type": "application/json",
            },
        }).then((response) => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`)
            }
            // Success - show a simple console message instead of toast
            console.log(
                `${fileRow.fileType.toUpperCase()} download cancelled successfully`
            )

            // Preserve active downloads and only reload after a short delay
            // This allows the backend to update the cancelled status
            setTimeout(() => {
                preserveActiveDownloadsAndReload()
            }, 500)
        })

        // Stop local progress polling immediately
        stopProgressPolling(taskId, fileRow.fileId)
    } catch (error) {
        console.error(
            `Failed to cancel ${fileRow.fileType} download for ${fileRow.sourceName}:`,
            error
        )
    }
}

// Source-specific actions
function editSource(sourceId: string) {
    console.log(`Editing source: ${sourceId}`)

    // Find the source to edit
    const sourceIndex = sources.value.findIndex(
        (source) =>
            `source-${sources.value.indexOf(source)}-${source.name}` ===
            sourceId
    )

    if (sourceIndex === -1) {
        console.error("Source not found for editing:", sourceId)
        return
    }

    // Set up the editing state
    const sourceToEdit = sources.value[sourceIndex]
    isEditMode.value = true
    editingSourceId.value = sourceId

    // Populate the form using dynamic field mapping
    populateFormFromSource(sourceToEdit)

    showSourceModal.value = true
}

function cancelSourceDialog() {
    showSourceModal.value = false
    isEditMode.value = false
    editingSourceId.value = null
    resetSourceForm()
}

async function saveSource() {
    try {
        if (isEditMode.value) {
            // Edit existing source
            if (!editingSourceId.value) return

            const sourceIndex = sources.value.findIndex(
                (source) =>
                    `source-${sources.value.indexOf(source)}-${source.name}` ===
                    editingSourceId.value
            )

            if (sourceIndex === -1) {
                console.error(
                    "Source not found for saving:",
                    editingSourceId.value
                )
                return
            }

            // Update the source using dynamic field mapping
            const updatedSource = updateSourceFromForm(
                sources.value[sourceIndex]
            )
            sources.value[sourceIndex] = updatedSource

            await apiPost("/api/sources", sources.value, true, {
                successMessage: "Source updated successfully",
                errorPrefix: "Failed to update source",
            })
        } else {
            // Create new source using dynamic field mapping
            const newSource = createSourceFromForm()
            const updatedSources = [...sources.value, newSource]

            await apiPost("/api/sources", updatedSources, true, {
                successMessage: "Source created successfully",
                errorPrefix: "Failed to create source",
            })

            sources.value = updatedSources
        }

        // Close the modal and reset state
        cancelSourceDialog()
    } catch (err) {
        error.value = `Failed to ${isEditMode.value ? "update" : "create"} source: ${err instanceof Error ? err.message : String(err)}`

        // Clear error message after 5 seconds
        setTimeout(() => {
            error.value = ""
        }, 5000)
    }
}

function deleteSource(sourceId: string) {
    sourceToDeleteId.value = sourceId
    showDeleteDialog.value = true
}

// Modal and form state
const showSourceModal = ref(false)
const showDeleteDialog = ref(false)
const isEditMode = ref(false)
const editingSourceId = ref<string | null>(null)
const sourceToDeleteId = ref<string | null>(null)

// TypeScript interface for source form data
interface SourceFormData {
    name: string
    enabled: boolean
    timezone: string
    connections: number
    refreshHours: number
    subscriptionExpires: string
    m3uUrl: string
    epgUrl: string
    [key: string]: string | number | boolean // Index signature for dynamic access
}

// Default values for source form fields (single source of truth)
const DEFAULT_SOURCE_FORM = {
    name: "",
    enabled: true,
    connections: 1,
    refreshHours: 24,
    timezone: "UTC",
    subscriptionExpires: null as string | null,
    m3uUrl: "",
    epgUrl: "",
} as const

// Source field mapping: form field -> source property
const SOURCE_FIELD_MAP = {
    name: "name",
    enabled: "enabled",
    connections: "number_of_connections",
    refreshHours: "refresh_every_hours",
    timezone: "source_timezone",
    subscriptionExpires: "subscription_expires",
} as const

// File field mapping: form field -> file metadata property
const FILE_FIELD_MAP = {
    m3uUrl: { fileType: "m3u", property: "url" },
    epgUrl: { fileType: "epg", property: "url" },
} as const

// Unified source form data (initialized from defaults)
const sourceForm = ref({ ...DEFAULT_SOURCE_FORM })

// Helper function to reset form to default values
function resetSourceForm() {
    sourceForm.value = { ...DEFAULT_SOURCE_FORM }
}

// Helper function to populate form from source data
function populateFormFromSource(source: Source): void {
    // Map source-level fields
    Object.entries(SOURCE_FIELD_MAP).forEach(([formField, sourceField]) => {
        const value = source[sourceField as keyof Source]
        ;(sourceForm.value as SourceFormData)[formField] =
            value ??
            DEFAULT_SOURCE_FORM[formField as keyof typeof DEFAULT_SOURCE_FORM]
    })

    // Map file-level fields
    Object.entries(FILE_FIELD_MAP).forEach(([formField, fileConfig]) => {
        const fileData = source.file_metadata?.[fileConfig.fileType]
        const value = fileData?.[fileConfig.property as keyof typeof fileData]
        ;(sourceForm.value as SourceFormData)[formField] = value || ""
    })
}

// Helper function to update source from form data
function updateSourceFromForm(source: Source): Source {
    const updatedSource = { ...source }

    // Update source-level fields
    Object.entries(SOURCE_FIELD_MAP).forEach(([formField, sourceField]) => {
        const value = (sourceForm.value as SourceFormData)[formField]
        ;(updatedSource as Record<string, unknown>)[sourceField] = value
    })

    // Update file-level fields
    Object.entries(FILE_FIELD_MAP).forEach(([formField, fileConfig]) => {
        const value = (sourceForm.value as SourceFormData)[formField]
        if (!updatedSource.file_metadata) {
            updatedSource.file_metadata = {}
        }
        if (!updatedSource.file_metadata[fileConfig.fileType]) {
            updatedSource.file_metadata[fileConfig.fileType] = {
                url: "",
                last_refresh_started_timestamp: "",
                last_size_bytes: 0,
            }
        }
        updatedSource.file_metadata[fileConfig.fileType][
            fileConfig.property as "url"
        ] = value
    })

    return updatedSource
}

// Helper function to create new source from form data
function createSourceFromForm(): Source {
    const newSource: Partial<Source> = {}

    // Set source-level fields
    Object.entries(SOURCE_FIELD_MAP).forEach(([formField, sourceField]) => {
        const value = (sourceForm.value as SourceFormData)[formField]
        ;(newSource as Record<string, unknown>)[sourceField] = value
    })

    // Set file metadata
    newSource.file_metadata = {}
    Object.entries(FILE_FIELD_MAP).forEach(([formField, fileConfig]) => {
        const value = (sourceForm.value as SourceFormData)[formField]
        if (!newSource.file_metadata![fileConfig.fileType]) {
            newSource.file_metadata![fileConfig.fileType] = {
                url: "",
                last_refresh_started_timestamp: "",
                last_size_bytes: 0,
            }
        }
        newSource.file_metadata![fileConfig.fileType][
            fileConfig.property as "url"
        ] = value
    })

    return newSource as Source
}

// Helper function to update source from SourceFileRow data (for inline editing)
function updateSourceFromFileRow(
    source: Source,
    fileRowData: SourceFileRow
): Source {
    const updatedSource = { ...source }

    // Use the same SOURCE_FIELD_MAP but with 'source' prefix for SourceFileRow fields
    Object.entries(SOURCE_FIELD_MAP).forEach(([formField, sourceField]) => {
        const fileRowField =
            `source${formField.charAt(0).toUpperCase() + formField.slice(1)}` as keyof SourceFileRow
        const value = fileRowData[fileRowField]
        if (value !== undefined) {
            ;(updatedSource as Record<string, unknown>)[sourceField] = value
        }
    })

    // Update file-level fields
    if (
        updatedSource.file_metadata &&
        updatedSource.file_metadata[fileRowData.fileType]
    ) {
        updatedSource.file_metadata[fileRowData.fileType].url =
            fileRowData.fileUrl
    }

    return updatedSource
}

// Open dialog for new source
function openNewSourceDialog() {
    isEditMode.value = false
    editingSourceId.value = null
    resetSourceForm()
    showSourceModal.value = true
}

// Handle delete confirmation
const confirmDelete = async () => {
    try {
        if (sourceToDeleteId.value === null) return

        // Find the source to delete by ID
        const sourceIndex = sources.value.findIndex(
            (source) =>
                `source-${sources.value.indexOf(source)}-${source.name}` ===
                sourceToDeleteId.value
        )

        if (sourceIndex === -1) return

        const updated = [...sources.value]
        updated.splice(sourceIndex, 1)

        await apiPost("/api/sources", updated, true, {
            successMessage: "Source deleted successfully",
            errorPrefix: "Failed to delete source",
        })

        sources.value = updated
        showDeleteDialog.value = false
        sourceToDeleteId.value = null
    } catch (err) {
        error.value = `Failed to delete source: ${err instanceof Error ? err.message : String(err)}`
        showDeleteDialog.value = false
    }
}

// Handle row edit save
const onRowEditSave = async (event: {
    data: SourceFileRow
    newData: SourceFileRow
    index: number
}) => {
    try {
        const { newData } = event

        // Find the source that this file belongs to
        const sourceIndex = sources.value.findIndex(
            (source) =>
                `source-${sources.value.indexOf(source)}-${source.name}` ===
                newData.sourceId
        )

        if (sourceIndex === -1) return

        // Update the source using dynamic field mapping
        const updatedSource = updateSourceFromFileRow(
            sources.value[sourceIndex],
            newData
        )
        sources.value[sourceIndex] = updatedSource

        // Send the updated sources to the backend
        await apiPost("/api/sources", sources.value, true, {
            successMessage: "Source updated successfully",
            errorPrefix: "Failed to update source",
        })
    } catch (err) {
        error.value = `Failed to update source: ${err instanceof Error ? err.message : String(err)}`

        // Clear error message after 5 seconds
        setTimeout(() => {
            error.value = ""
        }, 5000)
    }
}

/**
 * Component lifecycle
 */

onMounted(async () => {
    try {
        // Load user timezone settings for accurate time formatting
        await fetchUserTimezone()

        // Load sources data and wait for it to complete
        await loadSources()

        // Set loading to false so sourceFileRows shows real data instead of skeleton
        loading.value = false

        // Wait a bit for reactive updates to complete
        await new Promise((resolve) => setTimeout(resolve, 100))

        // Verify sources are loaded before detecting downloads
        console.log(
            `Sources loaded, checking sourceFileRows:`,
            sourceFileRows.value.length,
            "rows"
        )
        console.log(
            `First few rows:`,
            sourceFileRows.value.slice(0, 3).map((r) => ({
                sourceName: r.sourceName,
                fileType: r.fileType,
            }))
        )

        // Auto-detect and restore any active downloads after component mount
        await detectAndRestoreActiveDownloads()
    } catch (err) {
        error.value = `Failed to load sources: ${err instanceof Error ? err.message : String(err)}`
        loading.value = false // Ensure loading is false even on error
    }
})
</script>

<style scoped>
.error {
    color: red;
    margin-top: 1rem;
}

.success {
    color: green;
    margin-top: 1rem;
}
:deep(.new-source-dialog) {
    min-width: 400px;
    max-width: 90vw;
}

:deep(.new-source-dialog .p-dialog-header) {
    padding-bottom: 0.5rem;
}

:deep(.new-source-dialog .p-dialog-content) {
    padding: 0 1.5rem 1rem 1.5rem;
}

:deep(.delete-dialog) {
    width: 450px;
}

.confirmation-content {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    gap: 1rem;
    padding: 1rem 0;
}

.confirmation-content i {
    font-size: 2rem;
}
.form-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1rem;
    padding: 1rem 0;
}

@media (min-width: 768px) {
    .form-grid {
        grid-template-columns: 1fr 1fr;
    }
}

.form-row {
    margin-bottom: 0.5rem;
    display: flex;
    flex-direction: column;
}

.form-row label {
    font-weight: bold;
    margin-bottom: 0.3rem;
}

/* Dialog Footer */
.dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
}

.error {
    color: red;
    margin-top: 1rem;
}

.success {
    color: green;
    margin-top: 1rem;
}

/* Refresh All Actions */
.refresh-all-actions {
    margin-bottom: 1rem;
    padding: 1rem;
    background: var(--p-surface-section);
    border: 1px solid var(--p-surface-border);
    border-radius: 8px;
}

.refresh-all-buttons {
    display: flex;
    gap: 0.75rem;
    align-items: center;
}

@media (max-width: 768px) {
    .refresh-all-buttons {
        flex-direction: column;
        align-items: stretch;
    }
}

/* Last Refresh Cell with Progress Bar */
.last-refresh-cell {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.progress-container {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.progress-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.875rem;
}

.progress-status {
    font-weight: 600;
    text-transform: capitalize;
    color: var(--p-primary-color);
}

.progress-bytes {
    font-size: 0.75rem;
    color: var(--p-text-muted-color);
    font-family: monospace;
}

.last-refresh-time {
    font-size: 0.875rem;
    color: var(--p-text-color);
}

.last-refresh-status {
    font-size: 0.875rem;
    font-style: italic;
    font-weight: 500;
}

/* Status-based colors */
.status-success {
    color: var(--green-600);
}

.status-failed {
    color: var(--red-600);
}

.status-cancelled {
    color: var(--orange-600);
}

.status-never {
    color: var(--text-color-secondary);
}

/* Skeleton Cell Loading */
.skeleton-cell {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: flex-start;
}

/* URL Cell Styling */
.url-cell {
    width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-family: monospace;
    font-size: 0.9em;
}

/* File Type Styling */
.file-type-cell {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* Source Name Styling */
.source-name-cell {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 600;
}

/* Action Button Styling */
.action-buttons {
    display: flex;
    gap: 0.25rem;
    justify-content: center;
}

/* Row Group Styling */
:deep(.p-datatable-tbody > tr:first-child td) {
    border-top: 2px solid #e5e7eb;
}

:deep(.p-datatable-tbody > tr[data-p-rowgroup-first="true"] td) {
    border-top: 2px solid #e5e7eb;
    background-color: #f9fafb;
}

/* Source Group Header Styling */
.source-group-header {
    background: linear-gradient(
        135deg,
        var(--p-surface-100) 0%,
        var(--p-surface-200) 100%
    );
    border: 1px solid var(--p-surface-200);
    border-radius: 8px;
    padding: 1rem;
    margin: 0.5rem 0;
    transition: all 0.2s ease;
}

.dark-theme .source-group-header {
    background: linear-gradient(
        135deg,
        var(--p-surface-900) 0%,
        var(--p-surface-800) 100%
    );
    border: 1px solid var(--p-surface-600);
}

.source-header-main {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
}

.source-name {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--p-text-color);
}

.source-actions {
    display: flex;
    gap: 0.25rem;
}

.source-metadata {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    padding-top: 0.75rem;
    border-top: 1px solid var(--p-surface-200);
}

.metadata-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.metadata-label {
    font-weight: 500;
    color: var(--p-text-muted-color);
    min-width: 80px;
}

.metadata-value {
    font-weight: 600;
    color: var(--p-text-color);
    background: var(--p-surface-section);
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    border: 1px solid var(--p-surface-border);
    transition: all 0.2s ease;
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .url-cell {
        max-width: 250px;
    }

    .action-buttons {
        flex-direction: column;
        gap: 0.125rem;
    }

    .source-header-main {
        flex-direction: column;
        align-items: flex-start;
        gap: 0.5rem;
    }

    .source-metadata {
        grid-template-columns: 1fr;
        gap: 0.5rem;
    }
}
</style>
