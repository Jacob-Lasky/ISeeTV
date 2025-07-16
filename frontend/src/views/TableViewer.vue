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
                            Source: {{ sourceName }} • Passed:
                            {{ passedRecords }} | Caught by filter:
                            {{ filteredRecords }} | Total: {{ totalRecords }}
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

                <!-- ID Column -->
                <Column field="id" header="ID" style="width: 80px; height: 44px" :sortable="true">
                    <template #body="{ data }">
                        {{ data.id }}
                    </template>
                    <template #filter="{ filterModel, filterCallback }">
                        <InputText
                            v-model="filterModel.value"
                            type="text"
                            placeholder="Search ID..."
                            class="w-full"
                            @input="filterCallback()"
                        />
                    </template>
                </Column>

                <!-- Source Column -->
                <Column field="source" header="Source" style="width: 150px; height: 44px" :sortable="true" :showFilterMenu="false">
                    <template #body="{ data }">
                        <Tag :value="data.source" severity="info" />
                    </template>
                    <template #filter="{ filterModel, filterCallback }">
                        <Select
                            v-model="filterModel.value"
                            :options="sourceOptions"
                            placeholder="All Sources"
                            class="w-full"
                            :show-clear="true"
                            @change="filterCallback()"
                        >
                            <template #option="slotProps">
                                <Tag :value="slotProps.option" severity="info" />
                            </template>
                        </Select>
                    </template>
                </Column>

                <!-- Filter Reason Column -->
                <Column field="filter_reasons" header="Filter Reason" style="width: 200px; height: 44px" :sortable="true" :showFilterMenu="false">
                    <template #body="{ data }">
                        <Tag 
                            :value="formatFilterReasons(data.filter_reasons)" 
                            :severity="getFilterReasonSeverity(data.filter_reasons)"
                        />
                    </template>
                    <template #filter="{ filterModel, filterCallback }">
                        <Select
                            v-model="filterModel.value"
                            :options="filterReasonOptions"
                            placeholder="All Filter Reasons"
                            class="w-full"
                            :show-clear="true"
                            @change="filterCallback()"
                        >
                            <template #option="slotProps">
                                <Tag 
                                    :value="slotProps.option" 
                                    :severity="getFilterReasonSeverity(slotProps.option === 'Passed' ? null : slotProps.option)"
                                />
                            </template>
                        </Select>
                    </template>
                </Column>

                <!-- Dynamic columns based on table type -->
                <template v-if="tableName === 'epg_channels'">
                    <!-- Channel ID Column -->
                    <Column field="channel_id" header="Channel ID" style="width: 150px; height: 44px" :sortable="true">
                        <template #body="{ data }">
                            {{ data.channel_id }}
                        </template>
                        <template #filter="{ filterModel, filterCallback }">
                            <InputText
                                v-model="filterModel.value"
                                type="text"
                                placeholder="Search channel ID..."
                                class="w-full"
                                @input="filterCallback()"
                            />
                        </template>
                    </Column>

                    <!-- Display Name Column -->
                    <Column field="display_name" header="Display Name" style="width: 200px; height: 44px" :sortable="true">
                        <template #body="{ data }">
                            {{ data.display_name }}
                        </template>
                        <template #filter="{ filterModel, filterCallback }">
                            <InputText
                                v-model="filterModel.value"
                                type="text"
                                placeholder="Search display name..."
                                class="w-full"
                                @input="filterCallback()"
                            />
                        </template>
                    </Column>

                    <!-- Icon URL Column -->
                    <Column field="icon_url" header="Icon URL" style="width: 300px; height: 44px" :sortable="true">
                        <template #body="{ data }">
                            <a
                                v-if="data.icon_url"
                                :href="data.icon_url"
                                target="_blank"
                                rel="noopener noreferrer"
                                class="url-link"
                            >
                                {{ data.icon_url }}
                            </a>
                        </template>
                        <template #filter="{ filterModel, filterCallback }">
                            <InputText
                                v-model="filterModel.value"
                                type="text"
                                placeholder="Search icon URL..."
                                class="w-full"
                                @input="filterCallback()"
                            />
                        </template>
                    </Column>
                </template>

                <template v-else-if="tableName === 'm3u_channels'">
                    <!-- Group Column -->
                    <Column field="group" header="Group" style="width: 150px; height: 44px" :sortable="true" :showFilterMenu="false">
                        <template #body="{ data }">
                            <Tag v-if="data.group" :value="data.group" severity="secondary" />
                        </template>
                        <template #filter="{ filterModel, filterCallback }">
                            <Select
                                v-model="filterModel.value"
                                :options="groupOptions"
                                placeholder="All Groups"
                                class="w-full"
                                :show-clear="true"
                                @change="filterCallback()"
                            >
                                <template #option="slotProps">
                                    <Tag :value="slotProps.option" severity="secondary" />
                                </template>
                            </Select>
                        </template>
                    </Column>

                    <!-- TVG ID Column -->
                    <Column field="tvg_id" header="TVG ID" style="width: 150px; height: 44px" :sortable="true">
                        <template #body="{ data }">
                            <code>{{ data.tvg_id }}</code>
                        </template>
                        <template #filter="{ filterModel, filterCallback }">
                            <InputText
                                v-model="filterModel.value"
                                type="text"
                                placeholder="Search TVG ID..."
                                class="w-full"
                                @input="filterCallback()"
                            />
                        </template>
                    </Column>

                    <!-- Name Column -->
                    <Column field="name" header="Name" style="width: 200px; height: 44px" :sortable="true">
                        <template #body="{ data }">
                            {{ data.name }}
                        </template>
                        <template #filter="{ filterModel, filterCallback }">
                            <InputText
                                v-model="filterModel.value"
                                type="text"
                                placeholder="Search name..."
                                class="w-full"
                                @input="filterCallback()"
                            />
                        </template>
                    </Column>

                    <!-- Stream URL Column -->
                    <Column field="stream_url" header="Stream URL" style="width: 300px; height: 44px" :sortable="true">
                        <template #body="{ data }">
                            <a
                                :href="data.stream_url"
                                target="_blank"
                                rel="noopener noreferrer"
                                class="url-link"
                            >
                                {{ data.stream_url }}
                            </a>
                        </template>
                        <template #filter="{ filterModel, filterCallback }">
                            <InputText
                                v-model="filterModel.value"
                                type="text"
                                placeholder="Search stream URL..."
                                class="w-full"
                                @input="filterCallback()"
                            />
                        </template>
                    </Column>

                    <!-- Logo URL Column -->
                    <Column field="logo_url" header="Logo URL" style="width: 300px; height: 44px" :sortable="true">
                        <template #body="{ data }">
                            <a
                                v-if="data.logo_url"
                                :href="data.logo_url"
                                target="_blank"
                                rel="noopener noreferrer"
                                class="url-link"
                            >
                                {{ data.logo_url }}
                            </a>
                        </template>
                        <template #filter="{ filterModel, filterCallback }">
                            <InputText
                                v-model="filterModel.value"
                                type="text"
                                placeholder="Search logo URL..."
                                class="w-full"
                                @input="filterCallback()"
                            />
                        </template>
                    </Column>
                </template>

                <template v-else-if="tableName === 'programs'">
                    <!-- Program ID Column -->
                    <Column field="program_id" header="Program ID" style="width: 150px; height: 44px" :sortable="true">
                        <template #body="{ data }">
                            {{ data.program_id }}
                        </template>
                        <template #filter="{ filterModel, filterCallback }">
                            <InputText
                                v-model="filterModel.value"
                                type="text"
                                placeholder="Search program ID..."
                                class="w-full"
                                @input="filterCallback()"
                            />
                        </template>
                    </Column>

                    <!-- Channel ID Column -->
                    <Column field="channel_id" header="Channel ID" style="width: 150px; height: 44px" :sortable="true">
                        <template #body="{ data }">
                            {{ data.channel_id }}
                        </template>
                        <template #filter="{ filterModel, filterCallback }">
                            <InputText
                                v-model="filterModel.value"
                                type="text"
                                placeholder="Search channel ID..."
                                class="w-full"
                                @input="filterCallback()"
                            />
                        </template>
                    </Column>

                    <!-- Title Column -->
                    <Column field="title" header="Title" style="width: 250px; height: 44px" :sortable="true">
                        <template #body="{ data }">
                            {{ data.title }}
                        </template>
                        <template #filter="{ filterModel, filterCallback }">
                            <InputText
                                v-model="filterModel.value"
                                type="text"
                                placeholder="Search title..."
                                class="w-full"
                                @input="filterCallback()"
                            />
                        </template>
                    </Column>

                    <!-- Description Column -->
                    <Column field="description" header="Description" style="width: 400px; height: 44px" :sortable="true">
                        <template #body="{ data }">
                            {{ data.description }}
                        </template>
                        <template #filter="{ filterModel, filterCallback }">
                            <InputText
                                v-model="filterModel.value"
                                type="text"
                                placeholder="Search description..."
                                class="w-full"
                                @input="filterCallback()"
                            />
                        </template>
                    </Column>

                    <!-- Start Time Column -->
                    <Column field="start_time" header="Start Time" style="width: 180px; height: 44px" :sortable="true">
                        <template #body="{ data }">
                            {{ formatDateTime(data.start_time) }}
                        </template>
                        <template #filter="{ filterModel, filterCallback }">
                            <DatePicker
                                v-model="filterModel.value"
                                placeholder="Filter start time..."
                                show-time
                                hour-format="24"
                                class="w-full"
                                @date-select="filterCallback()"
                                @clear-click="filterCallback()"
                            />
                        </template>
                    </Column>

                    <!-- End Time Column -->
                    <Column field="end_time" header="End Time" style="width: 180px; height: 44px" :sortable="true">
                        <template #body="{ data }">
                            {{ formatDateTime(data.end_time) }}
                        </template>
                        <template #filter="{ filterModel, filterCallback }">
                            <DatePicker
                                v-model="filterModel.value"
                                placeholder="Filter end time..."
                                show-time
                                hour-format="24"
                                class="w-full"
                                @date-select="filterCallback()"
                                @clear-click="filterCallback()"
                            />
                        </template>
                    </Column>
                </template>

                <!-- Common timestamp columns -->
                <Column field="created_at" header="Created" style="width: 180px; height: 44px" :sortable="true">
                    <template #body="{ data }">
                        {{ formatDateTime(data.created_at) }}
                    </template>
                    <template #filter="{ filterModel, filterCallback }">
                        <DatePicker
                            v-model="filterModel.value"
                            placeholder="Filter created..."
                            show-time
                            hour-format="24"
                            class="w-full"
                            @date-select="filterCallback()"
                            @clear-click="filterCallback()"
                        />
                    </template>
                </Column>

                <Column field="updated_at" header="Updated" style="width: 180px; height: 44px" :sortable="true">
                    <template #body="{ data }">
                        {{ formatDateTime(data.updated_at) }}
                    </template>
                    <template #filter="{ filterModel, filterCallback }">
                        <DatePicker
                            v-model="filterModel.value"
                            placeholder="Filter updated..."
                            show-time
                            hour-format="24"
                            class="w-full"
                            @date-select="filterCallback()"
                            @clear-click="filterCallback()"
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
import { FilterMatchMode, FilterService } from "@primevue/core/api"
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
import Tag from "primevue/tag"

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

// Filter statistics (from /api/tables/{table_name}/filtered_counts/{source})
const totalRecords = ref(0)
const passedRecords = ref(0)
const filteredRecords = ref(0)

// Column filter options
const sourceOptions = ref([])
const groupOptions = ref([])
const filterReasonOptions = ref([])

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
                        field: "filter_reasons",
                        header: "Filter Reason",
                        style: "width: 200px; height: 44px",
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
                        field: "filter_reasons",
                        header: "Filter Reason",
                        style: "width: 200px; height: 44px",
                    },
                    {
                        field: "group",
                        header: "Group",
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
                        field: "filter_reasons",
                        header: "Filter Reason",
                        style: "width: 200px; height: 44px",
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

// Register custom filter constraint for filter_reasons
FilterService.register('filterReasonEquals', (value, filter) => {
    // If no filter is applied, show all records
    if (!filter) {
        return true
    }
    
    // Handle "Passed" case - match null, empty, or "[]" values
    if (filter === "Passed") {
        return !value || value === "" || value === "[]" || value === null
    }
    
    // For other filter values, parse JSON array and check if filter is included
    try {
        if (typeof value === 'string' && value.startsWith('[')) {
            const filterReasons = JSON.parse(value)
            return Array.isArray(filterReasons) && filterReasons.includes(filter)
        }
        // Fallback for non-JSON values
        return value === filter
    } catch (e) {
        // If JSON parsing fails, fall back to exact match
        return value === filter
    }
})

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
        } else if (column.field === "filter_reasons") {
            // Use custom filter constraint for filter_reasons
            newFilters[column.field] = {
                value: null,
                matchMode: 'filterReasonEquals',
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

// Format filter reasons for display
const formatFilterReasons = (filterReasons: string | null): string => {
    if (!filterReasons || filterReasons === "" || filterReasons === "[]" || filterReasons === null) {
        return "Passed"
    }
    
    try {
        if (typeof filterReasons === 'string' && filterReasons.startsWith('[')) {
            const parsed = JSON.parse(filterReasons)
            if (Array.isArray(parsed) && parsed.length > 0) {
                return parsed.join(", ")
            }
        }
        return filterReasons
    } catch (e) {
        return filterReasons
    }
}

// Get severity for filter reason tags
const getFilterReasonSeverity = (filterReason: string | null): string => {
    const formatted = formatFilterReasons(filterReason)
    if (!filterReason || filterReason === "Passed" || formatted === "Passed") {
        return "success"
    }
    return "warn"
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

            // Set filter reason options
            if (filterData.filter_reasons) {
                filterReasonOptions.value = filterData.filter_reasons.map(
                    (item) => item.value
                )
                console.log(
                    `Loaded ${filterReasonOptions.value.length} filter reason options`
                )
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
        filterReasonOptions.value = []
    }
}

// Load filter statistics from new backend endpoint
const loadFilterStatistics = async () => {
    try {
        console.log(
            `Loading filter statistics for ${tableName.value}/${sourceName.value}...`
        )

        const response = await apiGet(
            `/api/tables/${tableName.value}/filtered_counts/${encodeURIComponent(sourceName.value)}`,
            false,
            { showSuccessToast: false }
        )

        if (response.success && response.data) {
            const data = response.data

            // Map the new API response to our variables
            passedRecords.value = data.passed || 0
            filteredRecords.value = data.all_not_passed || 0
            totalRecords.value = data.total || 0

            console.log(
                `Filter statistics loaded: ${passedRecords.value} passed, ${filteredRecords.value} caught by filter, ${totalRecords.value} total`
            )
        } else {
            console.warn(
                `No filter statistics received for ${tableName.value}/${sourceName.value}`
            )
            // Set default values
            passedRecords.value = 0
            filteredRecords.value = 0
            totalRecords.value = 0
        }
    } catch (err) {
        console.error(`Error loading filter statistics:`, err)
        // Set default values on error
        passedRecords.value = 0
        filteredRecords.value = 0
        totalRecords.value = 0
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
    loadFilterStatistics()
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
