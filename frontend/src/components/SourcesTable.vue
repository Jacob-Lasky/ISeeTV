<template>
    <div>
        <DataTable
            v-model:editingRows="editingRows"
            :value="displaySources"
            responsiveLayout="scroll"
            stripedRows
            showGridlines
            :rows="10"
            editMode="row"
            dataKey="name"
            :pt="{
                table: { style: 'width: 100%; min-width: 70rem' },
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
            <!-- Dynamic columns based on configuration -->
            <Column
                v-for="column in tableColumns"
                :key="column.field"
                :field="column.field"
                :header="column.header"
                :sortable="column.sortable"
                :style="column.style"
                :bodyStyle="column.bodyStyle"
            >
                <template #body="{ data }">
                    <component
                        :is="getBodyComponent(column, data)"
                        v-bind="getBodyProps(column, data)"
                    >
                        <template
                            v-if="
                                !data.isSkeletonRow && column.type !== 'boolean'
                            "
                        >
                            {{ getBodyContent(column, data) }}
                        </template>
                    </component>
                </template>
                <template v-if="column.editable" #editor="{ data, field }">
                    <component
                        :is="getEditorComponent(column)"
                        v-model="data[field]"
                        v-bind="getEditorProps(column)"
                    />
                </template>
            </Column>

            <!-- Action columns -->
            <Column
                header="Edit"
                :rowEditor="true"
                style="width: 10%; min-width: 8rem"
                bodyStyle="text-align: center"
            />
            <Column header="Delete" style="width: 10%; min-width: 8rem">
                <template #body="{ data, index }">
                    <Button
                        v-if="!data.isSkeletonRow"
                        icon="pi pi-trash"
                        severity="danger"
                        text
                        rounded
                        @click="deleteSource(index)"
                    />
                </template>
            </Column>
        </DataTable>
        <br />
        <Button
            label="New Source"
            icon="pi pi-plus"
            class="mt-4"
            @click="showNewSourceModal = true"
        />

        <!-- New Source Dialog -->
        <Dialog
            v-model:visible="showNewSourceModal"
            header="New Source"
            :modal="true"
            :closable="false"
            :closeOnEscape="true"
            class="new-source-dialog"
        >
            <form @submit.prevent="saveNewSource">
                <div class="form-grid">
                    <div class="form-row">
                        <label>Name:</label>
                        <InputText v-model="newSource.name" required fluid />
                    </div>
                    <div class="form-row">
                        <label>Enabled:</label>
                        <Select
                            v-model="newSource.enabled"
                            :options="[true, false]"
                            fluid
                        />
                    </div>
                    <div class="form-row">
                        <label>M3U URL:</label>
                        <InputText v-model="newSource.m3u_url" required fluid />
                    </div>
                    <div class="form-row">
                        <label>EPG URL:</label>
                        <InputText v-model="newSource.epg_url" fluid />
                    </div>
                    <div class="form-row">
                        <label>Connections:</label>
                        <InputNumber
                            v-model="newSource.number_of_connections"
                            :min="1"
                            required
                            fluid
                        />
                    </div>
                    <div class="form-row">
                        <label>Refresh (h):</label>
                        <InputNumber
                            v-model="newSource.refresh_every_hours"
                            :min="1"
                            required
                            fluid
                        />
                    </div>
                    <div class="form-row">
                        <label>Subscription Expires:</label>
                        <DatePicker
                            v-model="newSource.subscription_expires"
                            dateFormat="yy-mm-dd"
                            showIcon
                            fluid
                        />
                    </div>
                    <div class="form-row">
                        <label>Source Timezone:</label>
                        <Select
                            v-model="newSource.source_timezone"
                            :options="timezoneOptions"
                            optionLabel="label"
                            optionValue="value"
                            placeholder="Select timezone"
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
                        @click="showNewSourceModal = false"
                    />
                    <Button
                        label="Save"
                        icon="pi pi-check"
                        severity="success"
                        @click="saveNewSource"
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
import type { Source } from "../types/types"
import { timezoneOptions } from "../utils/timezones"

interface SourceFieldSchema {
    field: keyof Source
    header: string
    type:
        | "text"
        | "number"
        | "boolean"
        | "date"
        | "url"
        | "timezone"
        | "last_refresh"
    defaultValue: any
    sortable?: boolean
    editable?: boolean
    style?: string
    bodyStyle?: string
    skeletonWidth?: string
}

// Schema drives everything - add new fields here
const sourceFieldsSchema: SourceFieldSchema[] = [
    {
        field: "name",
        header: "Name",
        type: "text",
        defaultValue: "",
        sortable: true,
        editable: true,
    },
    {
        field: "enabled",
        header: "Enabled",
        type: "boolean",
        defaultValue: true,
        sortable: true,
        editable: true,
    },
    {
        field: "m3u_url",
        header: "M3U URL",
        type: "url",
        defaultValue: "",
        sortable: true,
        editable: true,
        style: "min-width: 8rem; max-width: none",
        bodyStyle:
            "max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space;",
        skeletonWidth: "150px",
    },
    {
        field: "epg_url",
        header: "EPG URL",
        type: "url",
        defaultValue: "",
        sortable: true,
        editable: true,
        style: "min-width: 8rem; max-width: none",
        bodyStyle:
            "max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space;",
        skeletonWidth: "150px",
    },
    {
        field: "number_of_connections",
        header: "Connections",
        type: "number",
        defaultValue: 1,
        sortable: true,
        editable: true,
        skeletonWidth: "50px",
    },
    {
        field: "refresh_every_hours",
        header: "Refresh (h)",
        type: "number",
        defaultValue: 24,
        sortable: true,
        editable: true,
        skeletonWidth: "50px",
    },
    {
        field: "last_refresh",
        header: "Last Refresh",
        type: "last_refresh",
        defaultValue: "",
        sortable: true,
        editable: false,
        skeletonWidth: "100px",
    },
    {
        field: "subscription_expires",
        header: "Expires",
        type: "date",
        defaultValue: "",
        sortable: true,
        editable: true,
        skeletonWidth: "100px",
    },
    {
        field: "source_timezone",
        header: "Timezone",
        type: "timezone",
        defaultValue: "",
        sortable: true,
        editable: true,
        skeletonWidth: "120px",
    },
]

// Derived table columns from schema
interface TableColumn {
    field: string
    header: string
    sortable?: boolean
    editable?: boolean
    style?: string
    bodyStyle?: string
    type: string
    skeletonWidth?: string
}

const tableColumns = ref<TableColumn[]>(
    sourceFieldsSchema.map((schema) => ({
        field: schema.field,
        header: schema.header,
        type: schema.type,
        sortable: schema.sortable,
        editable: schema.editable,
        style: schema.style,
        bodyStyle: schema.bodyStyle,
        skeletonWidth: schema.skeletonWidth,
    }))
)

// DRY Default Source Factory - driven by schema
function createDefaultSource(): Source {
    const defaults: Partial<Source> = {}

    sourceFieldsSchema.forEach((schema) => {
        defaults[schema.field] = schema.defaultValue
    })

    return defaults as Source
}

// Modal state and new source object
const showNewSourceModal = ref(false)
const showDeleteDialog = ref(false)
const sourceToDeleteIndex = ref<number | null>(null)

const newSource = ref<Source>(createDefaultSource())

function resetNewSource() {
    newSource.value = createDefaultSource()
}

const saveNewSource = async () => {
    try {
        // Add the new source to the sources array
        const updatedSources = [...sources.value, newSource.value]

        // Send the updated sources to the backend
        await apiPost("/api/sources", updatedSources, true, {
            successMessage: "New source added successfully",
            errorPrefix: "Failed to add source",
        })

        // Update local sources and reset form
        sources.value = updatedSources
        resetNewSource()
        showNewSourceModal.value = false
    } catch (err) {
        error.value = `Failed to add source: ${err instanceof Error ? err.message : String(err)}`

        // Clear error message after 5 seconds
        setTimeout(() => {
            error.value = ""
        }, 5000)
    }
}

const sources = ref<Source[]>([])
const loading = ref(true)
const error = ref("")
const saveSuccess = ref("")
const editingRows = ref<Source[]>([])

// DRY Skeleton Factory - reuses createDefaultSource()
function createSkeletonSource(
    index: number
): Source & { isSkeletonRow: boolean } {
    return {
        ...createDefaultSource(),
        name: `skeleton-${index}`,
        isSkeletonRow: true,
    }
}

// Create skeleton data for loading state
const skeletonData = Array.from({ length: 1 }, (_, index) =>
    createSkeletonSource(index)
)

// Computed property to show skeleton data when loading, real data when loaded
const displaySources = computed(() => {
    return loading.value ? skeletonData : sources.value
})

function formatDate(date: string | Date) {
    if (!date) return ""
    const d = typeof date === "string" ? new Date(date) : date
    if (isNaN(d.getTime())) return ""
    const yyyy = d.getFullYear()
    const mm = String(d.getMonth() + 1).padStart(2, "0")
    const dd = String(d.getDate()).padStart(2, "0")
    return `${yyyy}-${mm}-${dd}`
}

function calculateHoursAgo(date: string | Date) {
    if (!date) return "Never"
    const d = typeof date === "string" ? new Date(date) : date
    if (isNaN(d.getTime())) return "Unknown"
    const hoursAgo = Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60))
    return `${hoursAgo} hours ago`
}

// DRY Component Rendering Functions
function getBodyComponent(column: TableColumn, data: any) {
    if (data.isSkeletonRow) return Skeleton

    switch (column.type) {
        case "boolean":
            return Tag
        default:
            return "span"
    }
}

function getBodyProps(column: TableColumn, data: any) {
    if (data.isSkeletonRow) {
        return column.skeletonWidth ? { width: column.skeletonWidth } : {}
    }

    switch (column.type) {
        case "boolean":
            return {
                severity: data[column.field] ? "success" : "danger",
                value: data[column.field] ? "Yes" : "No",
            }
        default:
            return {}
    }
}

function getBodyContent(column: TableColumn, data: any) {
    if (data.isSkeletonRow) return ""

    switch (column.type) {
        case "boolean":
            return "" // Content handled by Tag component props
        case "date":
            return formatDate(data[column.field])
        case "last_refresh":
            return calculateHoursAgo(data[column.field])
        default:
            return data[column.field] || ""
    }
}

function getEditorComponent(column: TableColumn) {
    switch (column.type) {
        case "number":
            return InputNumber
        case "boolean":
            return Select
        case "date":
            return DatePicker
        case "timezone":
            return Select
        default:
            return InputText
    }
}

function getEditorProps(column: TableColumn) {
    const baseProps = { fluid: true }

    switch (column.type) {
        case "boolean":
            return {
                ...baseProps,
                options: [
                    { label: "Yes", value: true },
                    { label: "No", value: false },
                ],
                optionLabel: "label",
                optionValue: "value",
                placeholder: "Select status",
            }
        case "timezone":
            return {
                ...baseProps,
                options: timezoneOptions,
                optionLabel: "label",
                optionValue: "value",
                placeholder: "Select timezone",
            }
        case "date":
            return {
                ...baseProps,
                showIcon: true,
                dateFormat: "yy-mm-dd",
            }
        case "url":
            return { ...baseProps, style: "min-width: 160px" }
        default:
            return baseProps
    }
}

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

// Show delete confirmation dialog
const deleteSource = (index: number) => {
    sourceToDeleteIndex.value = index
    showDeleteDialog.value = true
}

// Handle delete confirmation
const confirmDelete = async () => {
    try {
        if (sourceToDeleteIndex.value === null) return

        const index = sourceToDeleteIndex.value
        const updated = [...sources.value]
        updated.splice(index, 1)

        await apiPost("/api/sources", updated, true, {
            successMessage: "Source deleted successfully",
            errorPrefix: "Failed to delete source",
        })

        sources.value = updated
        showDeleteDialog.value = false
        sourceToDeleteIndex.value = null
    } catch (err) {
        error.value = `Failed to delete source: ${err instanceof Error ? err.message : String(err)}`
        showDeleteDialog.value = false
    }
}

const onRowEditSave = async (event: {
    data: Source
    newData: Source
    index: number
}) => {
    try {
        // Update the local data
        const { newData, index } = event
        sources.value[index] = newData

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
</style>
