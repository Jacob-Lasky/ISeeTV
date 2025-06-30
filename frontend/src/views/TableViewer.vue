<template>
    <div class="table-viewer">
        <div class="table-viewer-header">
            <div class="header-content">
                <Button
                    icon="pi pi-arrow-left"
                    label="Back to Sources"
                    severity="secondary"
                    class="back-button"
                    @click="goBack"
                />
                <div class="table-info">
                    <h2 class="table-title">
                        <i :class="tableConfig.icon" class="table-icon"></i>
                        {{ tableConfig.displayName }}
                    </h2>
                    <p class="table-description">
                        {{ tableConfig.description }}
                    </p>
                    <div class="table-metadata">
                        <span class="metadata-item">
                            <i class="pi pi-server"></i>
                            Source: {{ sourceName }}
                        </span>
                        <span v-if="totalRecords > 0" class="metadata-item">
                            <i class="pi pi-list"></i>
                            {{ formatNumber(totalRecords) }} records
                        </span>
                    </div>
                </div>
            </div>
        </div>

        <div class="table-content">
            <div v-if="loading" class="data-table-container">
                <DataTable
                    :value="skeletonData"
                    scrollable
                    scroll-height="calc(100vh - 280px)"
                    table-style="min-width: 50rem"
                    show-gridlines
                    striped-rows
                    class="virtual-table skeleton-table"
                >
                    <Column
                        v-for="column in tableConfig.columns"
                        :key="column.field"
                        :field="column.field"
                        :header="column.header"
                        :style="column.style"
                    >
                        <template #body>
                            <Skeleton
                                height="1rem"
                                class="skeleton-cell"
                            ></Skeleton>
                        </template>
                    </Column>
                </DataTable>
            </div>

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

            <div v-else-if="tableData.length === 0" class="empty-state">
                <i class="pi pi-inbox"></i>
                <h3>No Data Available</h3>
                <p>This table doesn't contain any data yet.</p>
            </div>

            <div v-else class="data-table-container">
                <DataTable
                    :value="tableData"
                    scrollable
                    scroll-height="calc(100vh - 280px)"
                    :virtual-scroller-options="{ itemSize: 44 }"
                    table-style="min-width: 50rem"
                    show-gridlines
                    striped-rows
                    :loading="loading"
                    class="virtual-table"
                >
                    <Column
                        v-for="column in tableConfig.columns"
                        :key="column.field"
                        :field="column.field"
                        :header="column.header"
                        :style="column.style"
                        :sortable="column.sortable !== false"
                    >
                        <template
                            v-if="column.type === 'datetime'"
                            #body="{ data }"
                        >
                            <span class="datetime-cell">
                                {{ formatDateTime(data[column.field]) }}
                            </span>
                        </template>
                        <template
                            v-else-if="column.type === 'url'"
                            #body="{ data }"
                        >
                            <span class="url-cell" :title="data[column.field]">
                                {{ data[column.field] }}
                            </span>
                        </template>
                        <template
                            v-else-if="column.type === 'id'"
                            #body="{ data }"
                        >
                            <span class="id-cell">
                                {{ data[column.field] }}
                            </span>
                        </template>
                    </Column>
                </DataTable>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import { useToast } from "primevue/usetoast"
import Button from "primevue/button"
import DataTable from "primevue/datatable"
import Column from "primevue/column"
import Skeleton from "primevue/skeleton"
import { apiGet } from "../utils/apiUtils"
import { getFileTypeIcon } from "../utils/fileUtils"

// Route and navigation
const route = useRoute()
const router = useRouter()
const toast = useToast()

// Props from route params
const sourceName = computed(() => route.params.sourceName as string)
const tableName = computed(() => route.params.tableName as string)

// Component state
const loading = ref(true)
const error = ref("")
const tableData = ref<any[]>([])
const totalRecords = ref(0)

// Skeleton data for loading state (20 empty rows)
const skeletonData = ref(new Array(20).fill({}))

//  table configuration interface
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

//  function to get table configuration
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

//  utility functions
const formatDateTime = (dateString: string): string => {
    if (!dateString) return "N/A"
    try {
        return new Date(dateString).toLocaleString()
    } catch {
        return dateString
    }
}

const formatNumber = (num: number): string => {
    return new Intl.NumberFormat().format(num)
}

const goBack = () => {
    router.push("/sources")
}

//  function to load table data
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

// Load data on component mount
onMounted(() => {
    if (!sourceName.value || !tableName.value) {
        error.value = "Missing required parameters"
        loading.value = false
        return
    }

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
