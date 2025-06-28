<template>
    <div>
        <DataTable
            v-model:editingRows="editingRows"
            :value="sourceFileRows"
            rowGroupMode="subheader"
            groupRowsBy="sourceName"
            sortMode="single"
            sortField="sourceName"
            :sortOrder="1"
            responsiveLayout="scroll"
            stripedRows
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
                        class="flex items-center gap-2"
                    >
                        <Skeleton
                            shape="circle"
                            size="1.5rem"
                            class="mr-2"
                        ></Skeleton>
                        <Skeleton width="4rem" height="1rem"></Skeleton>
                    </div>
                    <div v-else style="display: flex; align-items: center; gap: 16px;">
                        <i
                            :class="getFileTypeIcon(data.fileType)"
                            :style="{ color: getFileTypeColor(data.fileType) }"
                        ></i>
                        <span style="text-transform: uppercase; font-weight: 600;">{{
                            data.fileType
                        }}</span>
                    </div>
                </template>
            </Column>

            <!-- File URL Column -->
            <Column field="fileUrl" header="URL" style="min-width: 300px">
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

            <!-- File Last Refresh Column -->
            <Column
                field="fileLastRefresh"
                header="Last Refresh"
                style="min-width: 150px"
            >
                <template #body="{ data }">
                    <Skeleton
                        v-if="data._isSkeleton"
                        width="8rem"
                        height="1rem"
                    ></Skeleton>
                    <span v-else>{{
                        formatLastRefresh(data.fileLastRefresh || "")
                    }}</span>
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
                        <Button
                            icon="pi pi-refresh"
                            severity="info"
                            size="small"
                            text
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
                        <label>M3U URL:</label>
                        <InputText v-model="sourceForm.m3uUrl" required fluid />
                    </div>
                    <div class="form-row">
                        <label>EPG URL:</label>
                        <InputText v-model="sourceForm.epgUrl" fluid />
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
                        <label>Refresh Hours:</label>
                        <InputNumber
                            v-model="sourceForm.refreshHours"
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
import { apiGet, apiPost } from "../utils/apiUtils"
import type { Source, SourceFileRow } from "../types/types"
import { timezoneOptions } from "../utils/timezones"

// Reactive state for sources and UI
const sources = ref<Source[]>([])
const editingRows = ref([])
const loading = ref(true)
const error = ref("")
const saveSuccess = ref("")

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
                fileLastRefresh: fileMetadata.last_refresh || null,
                fileSizeBytes: fileMetadata.last_size_bytes,
                fileStatus: determineFileStatus(fileMetadata),
                fileLastError: null, // TODO: Add error tracking

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
    if (fileMetadata.last_refresh) return "active"
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
                fileLastRefresh: null,
                fileSizeBytes: 0,
                fileStatus: "active" as const,
                fileLastError: null,
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

// Format last refresh time
function formatLastRefresh(lastRefresh: string): string {
    if (!lastRefresh) return "Never"

    const date = new Date(lastRefresh)
    if (isNaN(date.getTime())) return "Invalid date"

    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffHours / 24)

    if (diffDays > 0) {
        return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`
    } else if (diffHours > 0) {
        return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`
    } else {
        return "Less than 1 hour ago"
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

// File-specific actions
function refreshFile(fileRow: SourceFileRow) {
    console.log(
        `Refreshing ${fileRow.fileType.toUpperCase()} file for source: ${fileRow.sourceName}`
    )
    // TODO: Implement file refresh logic
}

function downloadFile(fileRow: SourceFileRow) {
    console.log(
        `Downloading ${fileRow.fileType.toUpperCase()} file for source: ${fileRow.sourceName}`
    )
    // TODO: Implement file download logic
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
        ;(sourceForm.value as any)[formField] =
            value ??
            DEFAULT_SOURCE_FORM[formField as keyof typeof DEFAULT_SOURCE_FORM]
    })

    // Map file-level fields
    Object.entries(FILE_FIELD_MAP).forEach(([formField, fileConfig]) => {
        const fileData = source.file_metadata?.[fileConfig.fileType]
        const value = fileData?.[fileConfig.property as keyof typeof fileData]
        ;(sourceForm.value as any)[formField] = value || ""
    })
}

// Helper function to update source from form data
function updateSourceFromForm(source: Source): Source {
    const updatedSource = { ...source }

    // Update source-level fields
    Object.entries(SOURCE_FIELD_MAP).forEach(([formField, sourceField]) => {
        const value = (sourceForm.value as any)[formField]
        ;(updatedSource as any)[sourceField] = value
    })

    // Update file-level fields
    Object.entries(FILE_FIELD_MAP).forEach(([formField, fileConfig]) => {
        const value = (sourceForm.value as any)[formField]
        if (!updatedSource.file_metadata) {
            updatedSource.file_metadata = {}
        }
        if (!updatedSource.file_metadata[fileConfig.fileType]) {
            updatedSource.file_metadata[fileConfig.fileType] = {
                url: "",
                last_refresh: "",
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
        const value = (sourceForm.value as any)[formField]
        ;(newSource as any)[sourceField] = value
    })

    // Set file metadata
    newSource.file_metadata = {}
    Object.entries(FILE_FIELD_MAP).forEach(([formField, fileConfig]) => {
        const value = (sourceForm.value as any)[formField]
        if (!newSource.file_metadata![fileConfig.fileType]) {
            newSource.file_metadata![fileConfig.fileType] = {
                url: "",
                last_refresh: "",
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
            ;(updatedSource as any)[sourceField] = value
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
        sources.value = await apiGet("/api/sources", false, {
            showSuccessToast: true,
            errorPrefix: "Failed to load sources",
        })
    } catch (err) {
        error.value = `Failed to load sources: ${err instanceof Error ? err.message : String(err)}`
    } finally {
        loading.value = false
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

/* Skeleton Cell Loading */
.skeleton-cell {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: flex-start;
}

/* URL Cell Styling */
.url-cell {
    max-width: 300px;
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
        var(--p-surface-50) 0%,
        var(--p-surface-100) 100%
    );
    border: 1px solid var(--p-surface-200);
    border-radius: 8px;
    padding: 1rem;
    margin: 0.5rem 0;
    transition: all 0.2s ease;
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
    background: var(--p-surface-0);
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    border: 1px solid var(--p-surface-200);
    transition: all 0.2s ease;
}

/* Dark mode specific adjustments */
:global(.p-dark) .source-group-header {
    background: linear-gradient(
        135deg,
        var(--p-surface-800) 0%,
        var(--p-surface-700) 100%
    );
    border-color: var(--p-surface-600);
}

:global(.p-dark) .metadata-value {
    background: var(--p-surface-900);
    border-color: var(--p-surface-600);
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .url-cell {
        max-width: 200px;
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
