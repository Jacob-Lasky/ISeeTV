<template>
    <div class="table-viewer">
        <!-- Header with back button and table info -->
        <div class="table-header mb-4">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <Button
                        icon="pi pi-arrow-left"
                        label="Back to Sources"
                        size="small"
                        outlined
                        @click="goBack"
                    />
                    <div class="table-info">
                        <h2 class="text-2xl font-semibold text-gray-800">
                            {{ tableConfig.displayName }}
                        </h2>
                        <p class="text-gray-600">
                            Source: {{ sourceName }} •
                            {{ tableData.length }} records
                        </p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Loading state with skeleton -->
        <div v-if="loading" class="loading-container">
            <DataTable
                :value="skeletonData"
                scrollable
                scroll-height="calc(100vh - 320px)"
                table-style="min-width: 50rem"
                striped-rows
                class="virtual-table skeleton-table"
            >
                <template #header>
                    <div class="flex justify-end">
                        <IconField>
                            <InputIcon>
                                <i class="pi pi-search" />
                            </InputIcon>
                            <InputText placeholder="Loading..." disabled />
                        </IconField>
                    </div>
                </template>
                <Column
                    v-for="column in tableConfig.columns"
                    :key="column.field"
                    :field="column.field"
                    :header="column.header"
                    :style="column.style"
                >
                    <template #body>
                        <Skeleton height="1rem" class="mb-2" />
                    </template>
                </Column>
            </DataTable>
        </div>

        <!-- Main data table with search and filters -->
        <div v-else-if="!error && tableData.length > 0" class="data-container">
            <DataTable
                v-model:filters="filters"
                :value="tableData"
                scrollable
                scroll-height="calc(100vh - 320px)"
                :virtual-scroller-options="{ itemSize: 44 }"
                table-style="min-width: 50rem"
                striped-rows
                :loading="loading"
                filter-display="row"
                :global-filter-fields="globalFilterFields"
                class="virtual-table"
            >
                <template #header>
                    <div class="flex justify-end">
                        <IconField>
                            <InputIcon>
                                <i class="pi pi-search" />
                            </InputIcon>
                            <InputText
                                v-model="filters['global'].value"
                                placeholder="Search all columns..."
                                class="w-80"
                            />
                        </IconField>
                    </div>
                </template>
                <template #empty>
                    <div class="text-center py-8">
                        <i class="pi pi-search text-4xl text-gray-400 mb-4"></i>
                        <p class="text-gray-600">
                            No records found matching your search criteria.
                        </p>
                        <p class="text-sm text-gray-500 mt-2">
                            Try adjusting your filters or search terms.
                        </p>
                    </div>
                </template>
                <Column
                    v-for="column in tableConfig.columns"
                    :key="column.field"
                    :field="column.field"
                    :header="column.header"
                    :style="column.style"
                    :sortable="column.sortable !== false"
                    :filter-field="column.field"
                >
                    <template #body="{ data }">
                        <span v-if="column.type === 'datetime'">
                            {{ formatDateTime(data[column.field]) }}
                        </span>
                        <a
                            v-else-if="
                                column.type === 'url' && data[column.field]
                            "
                            :href="data[column.field]"
                            target="_blank"
                            class="text-blue-600 hover:text-blue-800 underline"
                        >
                            {{ data[column.field] }}
                        </a>
                        <span v-else>
                            {{ data[column.field] || "N/A" }}
                        </span>
                    </template>
                    <template #filter="{ filterModel, filterCallback }">
                        <!-- Source column filter -->
                        <Select
                            v-if="column.field === 'source'"
                            v-model="filterModel.value"
                            :options="sourceOptions"
                            placeholder="All Sources"
                            class="w-full"
                            :show-clear="true"
                            @change="filterCallback()"
                        />
                        <!-- Group column filter (M3U channels only) -->
                        <Select
                            v-else-if="
                                column.field === 'group' &&
                                tableName === 'm3u_channels'
                            "
                            v-model="filterModel.value"
                            :options="groupOptions"
                            placeholder="All Groups"
                            class="w-full"
                            :show-clear="true"
                            @change="filterCallback()"
                        />
                        <!-- Date column filter -->
                        <DatePicker
                            v-else-if="column.type === 'datetime'"
                            v-model="filterModel.value"
                            :placeholder="`Filter ${column.header.toLowerCase()}...`"
                            show-time
                            hour-format="24"
                            class="w-full"
                            @date-select="filterCallback()"
                            @clear-click="filterCallback()"
                        />
                        <!-- Default text input filter -->
                        <InputText
                            v-else
                            v-model="filterModel.value"
                            type="text"
                            :placeholder="`Search ${column.header.toLowerCase()}...`"
                            class="w-full"
                            @input="filterCallback()"
                        />
                    </template>
                </Column>
            </DataTable>
        </div>

        <!-- Error state -->
        <div v-else-if="error" class="error-state">
            <i class="pi pi-exclamation-triangle"></i>
            <h3>Error Loading Table</h3>
            <p>{{ error }}</p>
            <Button
                label="Retry"
                icon="pi pi-refresh"
                severity="secondary"
                @click="loadTableData"
            />
        </div>

        <!-- Empty state -->
        <div v-else-if="tableData.length === 0" class="empty-state">
            <i class="pi pi-inbox"></i>
            <h3>No Data Available</h3>
            <p>This table doesn't contain any data yet.</p>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import { useRoute, useRouter } from "vue-router"
import { FilterMatchMode } from "@primevue/core/api"
import { useToast } from "primevue/usetoast"
import { apiGet } from "@/utils/apiUtils"
import { getFileTypeIcon } from "@/utils/fileUtils"
import { useToastListener } from "@/services/toastService"

// PrimeVue components
import DataTable from "primevue/datatable"
import Column from "primevue/column"
import Button from "primevue/button"
import Skeleton from "primevue/skeleton"
import InputText from "primevue/inputtext"
import IconField from "primevue/iconfield"
import InputIcon from "primevue/inputicon"
import DatePicker from "primevue/datepicker"
import Select from "primevue/select"

// Route and navigation
const route = useRoute()
const router = useRouter()

// Toast setup
const toast = useToast()
const toastListener = useToastListener()

// Props from route params
const sourceName = computed(() => route.params.sourceName as string)
const tableName = computed(() => route.params.tableName as string)

// Reactive state
const loading = ref(true)
const error = ref("")
const tableData = ref([])

// Search and filtering state
const filters = ref({})
const globalFilterFields = ref([])
const totalRecords = ref(0)

// Column filter options
const sourceOptions = ref([])
const groupOptions = ref([])

// Skeleton data for loading state (20 empty rows)
const skeletonData = ref(new Array(20).fill({}))

// Table configuration interface
interface TableColumn {
    field: string
    header: string
    style: string
    type?: "text" | "datetime" | "url" | "id"
    sortable?: boolean
}

interface TableConfig {
    displayName: string
    description: string
    icon: string
    columns: TableColumn[]
}

// Function to get table configuration
const getTableConfig = (tableName: string): TableConfig => {
    switch (tableName) {
        case "epg_channels":
            return {
                displayName: "EPG Channels",
                description: "Electronic Program Guide channel data",
                icon: getFileTypeIcon("epg-channels"),
                columns: [
                    {
                        field: "id",
                        header: "ID",
                        style: "width: 80px; height: 44px",
                        type: "id",
                    },
                    {
                        field: "source",
                        header: "Source",
                        style: "width: 150px; height: 44px",
                    },
                    {
                        field: "channel_id",
                        header: "Channel ID",
                        style: "width: 150px; height: 44px",
                    },
                    {
                        field: "display_name",
                        header: "Display Name",
                        style: "width: 200px; height: 44px",
                    },
                    {
                        field: "icon_url",
                        header: "Icon URL",
                        style: "width: 300px; height: 44px",
                        type: "url",
                    },
                    {
                        field: "created_at",
                        header: "Created",
                        style: "width: 180px; height: 44px",
                        type: "datetime",
                    },
                    {
                        field: "updated_at",
                        header: "Updated",
                        style: "width: 180px; height: 44px",
                        type: "datetime",
                    },
                ],
            }
        case "m3u_channels":
            return {
                displayName: "M3U Channels",
                description: "M3U playlist channel data",
                icon: getFileTypeIcon("m3u"),
                columns: [
                    {
                        field: "id",
                        header: "ID",
                        style: "width: 80px; height: 44px",
                        type: "id",
                    },
                    {
                        field: "source",
                        header: "Source",
                        style: "width: 150px; height: 44px",
                    },
                    {
                        field: "tvg_id",
                        header: "TVG ID",
                        style: "width: 150px; height: 44px",
                    },
                    {
                        field: "name",
                        header: "Name",
                        style: "width: 200px; height: 44px",
                    },
                    {
                        field: "stream_url",
                        header: "Stream URL",
                        style: "width: 300px; height: 44px",
                        type: "url",
                    },
                    {
                        field: "logo_url",
                        header: "Logo URL",
                        style: "width: 300px; height: 44px",
                        type: "url",
                    },
                    {
                        field: "group",
                        header: "Group",
                        style: "width: 150px; height: 44px",
                    },
                    {
                        field: "created_at",
                        header: "Created",
                        style: "width: 180px; height: 44px",
                        type: "datetime",
                    },
                    {
                        field: "updated_at",
                        header: "Updated",
                        style: "width: 180px; height: 44px",
                        type: "datetime",
                    },
                ],
            }
        case "programs":
            return {
                displayName: "EPG Programs",
                description: "Electronic Program Guide program data",
                icon: getFileTypeIcon("epg-programs"),
                columns: [
                    {
                        field: "id",
                        header: "ID",
                        style: "width: 80px; height: 44px",
                        type: "id",
                    },
                    {
                        field: "source",
                        header: "Source",
                        style: "width: 150px; height: 44px",
                    },
                    {
                        field: "program_id",
                        header: "Program ID",
                        style: "width: 150px; height: 44px",
                    },
                    {
                        field: "channel_id",
                        header: "Channel ID",
                        style: "width: 150px; height: 44px",
                    },
                    {
                        field: "start_time",
                        header: "Start Time",
                        style: "width: 180px; height: 44px",
                        type: "datetime",
                    },
                    {
                        field: "end_time",
                        header: "End Time",
                        style: "width: 180px; height: 44px",
                        type: "datetime",
                    },
                    {
                        field: "title",
                        header: "Title",
                        style: "width: 250px; height: 44px",
                    },
                    {
                        field: "description",
                        header: "Description",
                        style: "width: 400px; height: 44px",
                    },
                    {
                        field: "created_at",
                        header: "Created",
                        style: "width: 180px; height: 44px",
                        type: "datetime",
                    },
                    {
                        field: "updated_at",
                        header: "Updated",
                        style: "width: 180px; height: 44px",
                        type: "datetime",
                    },
                ],
            }
        default:
            return {
                displayName: "Unknown Table",
                description: "Table data",
                icon: "pi pi-table",
                columns: [],
            }
    }
}

// Computed table configuration
const tableConfig = computed(() => getTableConfig(tableName.value))

// Initialize filters when table config changes
const initializeFilters = () => {
    const config = tableConfig.value
    const newFilters = {
        global: { value: null, matchMode: FilterMatchMode.CONTAINS },
    }

    // Set up global filter fields
    globalFilterFields.value = config.columns.map((col) => col.field)

    // Set up individual column filters
    config.columns.forEach((column) => {
        if (column.type === "datetime") {
            newFilters[column.field] = {
                value: null,
                matchMode: FilterMatchMode.DATE_IS,
            }
        } else {
            newFilters[column.field] = {
                value: null,
                matchMode: FilterMatchMode.CONTAINS,
            }
        }
    })

    filters.value = newFilters
}

// Utility functions
const formatDateTime = (dateString: string): string => {
    if (!dateString) return "N/A"
    try {
        return new Date(dateString).toLocaleString()
    } catch {
        return dateString
    }
}

const goBack = () => {
    router.push("/sources")
}

// Function to load table data
const loadTableData = async () => {
    loading.value = true
    error.value = ""

    try {
        console.log(
            `Loading table data for: ${tableName.value}, source: ${sourceName.value}`
        )

        const response = await apiGet(
            `/api/tables/${tableName.value}?source=${encodeURIComponent(sourceName.value)}`
        )

        if (response.success && response.data) {
            tableData.value = response.data.records || []
            totalRecords.value = response.data.total || tableData.value.length

            // Load precomputed filter values from backend
            await loadFilterOptions()

            console.log(
                `Loaded ${tableData.value.length} records from ${tableName.value}`
            )
        } else {
            throw new Error(response.error || "Failed to load table data")
        }
    } catch (err) {
        console.error("Error loading table data:", err)
        error.value =
            err instanceof Error ? err.message : "Unknown error occurred"

        toast.add({
            severity: "error",
            summary: "Error",
            detail: `Failed to load ${tableConfig.value.displayName}`,
            life: 5000,
        })
    } finally {
        loading.value = false
    }
}

// Load precomputed filter values from backend API
const loadFilterOptions = async () => {
    try {
        console.log(`Loading filter options for table: ${tableName.value}`)

        const response = await apiGet(
            `/api/tables/${tableName.value}/filters`,
            false,
            { showSuccessToast: false }
        )

        if (response.success && response.data) {
            const filterData = response.data

            // Set source options
            if (filterData.source) {
                sourceOptions.value = filterData.source.map(
                    (item) => item.value
                )
                console.log(
                    `Loaded ${sourceOptions.value.length} source options`
                )
            }

            // Set group options for M3U channels
            if (tableName.value === "m3u_channels" && filterData.group) {
                groupOptions.value = filterData.group.map((item) => item.value)
                console.log(`Loaded ${groupOptions.value.length} group options`)
            }
        } else {
            console.warn(
                `No filter data received for table: ${tableName.value}`
            )
        }
    } catch (err) {
        console.error(
            `Error loading filter options for ${tableName.value}:`,
            err
        )
        // Fallback to empty arrays
        sourceOptions.value = []
        groupOptions.value = []
    }
}

// Load data on component mount
onMounted(() => {
    // Set up toast listener for API notifications
    toastListener.subscribe((message) => {
        toast.add({
            severity: message.severity,
            summary: message.summary,
            detail: message.detail,
            life: message.life || 3000,
        })
    })

    if (!sourceName.value || !tableName.value) {
        error.value = "Missing required parameters"
        loading.value = false
        return
    }

    initializeFilters()
    loadTableData()
})
</script>

<style scoped>
.table-viewer {
    height: 100vh;
    display: flex;
    flex-direction: column;
    background: var(--p-surface-ground);
}

.table-viewer-header {
    background: var(--p-surface-section);
    border-bottom: 1px solid var(--p-surface-border);
    padding: 1.5rem;
    flex-shrink: 0;
}

.header-content {
    max-width: 1200px;
    margin: 0 auto;
    display: flex;
    align-items: flex-start;
    gap: 1.5rem;
}

.back-button {
    flex-shrink: 0;
    margin-top: 0.25rem;
}

.table-info {
    flex: 1;
}

.table-title {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin: 0 0 0.5rem 0;
    font-size: 1.75rem;
    font-weight: 600;
    color: var(--p-text-color);
}

.table-icon {
    font-size: 1.5rem;
    color: var(--p-primary-color);
}

.table-description {
    margin: 0 0 1rem 0;
    color: var(--p-text-muted-color);
    font-size: 1.125rem;
}

.table-metadata {
    display: flex;
    gap: 1.5rem;
    flex-wrap: wrap;
}

.metadata-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--p-text-muted-color);
    font-size: 0.875rem;
}

.metadata-item i {
    color: var(--p-primary-color);
}

.table-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.data-table-container {
    flex: 1;
    padding: 1rem;
    overflow: hidden;
}

.virtual-table {
    height: 100%;
}

/* State styling */
.error-state,
.empty-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 2rem;
    gap: 1rem;
}

.error-state p,
.empty-state p {
    color: var(--p-text-muted-color);
    margin: 0;
}

.error-state i,
.empty-state i {
    font-size: 3rem;
    color: var(--p-text-muted-color);
}

.error-state h3,
.empty-state h3 {
    margin: 0;
    color: var(--p-text-color);
}

/* Cell styling */
.datetime-cell {
    font-family: monospace;
    font-size: 0.875rem;
}

.url-cell {
    font-family: monospace;
    font-size: 0.875rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 100%;
    display: block;
}

.id-cell {
    font-family: monospace;
    font-weight: 600;
    color: var(--p-primary-color);
}

/* Skeleton loading styling */
.skeleton-table {
    opacity: 0.7;
}

.skeleton-cell {
    width: 100%;
    border-radius: 4px;
}

/* Responsive design */
@media (max-width: 768px) {
    .header-content {
        flex-direction: column;
        gap: 1rem;
    }

    .table-metadata {
        flex-direction: column;
        gap: 0.5rem;
    }

    .table-viewer-header {
        padding: 1rem;
    }

    .data-table-container {
        padding: 0.5rem;
    }
}
</style>
