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
                class="skeleton-table"
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
        <div v-else-if="!error" class="data-container">
            <DataTable
                v-model:filters="filters"
                :value="tableData"
                scrollable
                scroll-height="calc(100vh - 320px)"
                table-style="min-width: 50rem"
                striped-rows
                :loading="loading"
                filter-display="row"
                :global-filter-fields="globalFilterFields"
                paginator
                :rows="pageSize"
                :rowsPerPageOptions="[50, 100, 200, 500]"
                :totalRecords="totalRecords"
                :lazy="true"
                @page="onPage"
                dataKey="id"
                :sortField="sortField"
                :sortOrder="sortOrderNum"
                @sort="onSort"
            >
                <template #header>
                    <div class="flex justify-between items-center gap-2">
                        <div class="flex items-center gap-2">
                            <Button
                                size="small"
                                :outlined="filterView !== 'all'"
                                label="All"
                                @click="setFilterView('all')"
                            />
                            <Button
                                size="small"
                                :outlined="filterView !== 'normal'"
                                label="Passed"
                                @click="setFilterView('normal')"
                            />
                            <Button
                                size="small"
                                :outlined="filterView !== 'inverse'"
                                label="Filtered"
                                @click="setFilterView('inverse')"
                            />
                        </div>
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
                <Column
                    field="id"
                    header="ID"
                    style="max-width: 60px"
                    :sortable="true"
                    :showFilterMenu="false"
                >
                    <template #body="{ data }">
                        {{ data?.id ?? "" }}
                    </template>
                    <template #filter="{ filterModel, filterCallback }">
                        <InputText
                            v-model="filterModel.value"
                            type="text"
                            placeholder="Search ID..."
                            class="w-full"
                            style="max-width: 40px"
                            @input="filterCallback()"
                        />
                    </template>
                </Column>

                <!-- Filter Reason Column -->
                <Column
                    field="filter_reasons"
                    header="Filter Reason"
                    :sortable="true"
                    :showFilterMenu="false"
                    :style="{ width: '300px', minWidth: '300px', maxWidth: '300px' }"
                >
                    <template #body="{ data }">
                        <div v-if="data?.filter_reasons" :style="{ maxWidth: '100%', overflow: 'hidden' }">
                            <pre :style="{
                                fontFamily: 'Courier New, monospace',
                                fontSize: '11px',
                                lineHeight: '1.3',
                                margin: '0',
                                padding: '4px 6px',
                                background: '#2d3748',
                                border: '1px solid #4a5568',
                                borderRadius: '4px',
                                whiteSpace: 'pre-wrap',
                                wordWrap: 'break-word',
                                maxHeight: '120px',
                                overflowY: 'auto',
                                color: '#e2e8f0'
                            }">{{ formatJSON(data.filter_reasons) }}</pre>
                        </div>
                        <Tag
                            v-else
                            value="Passed"
                            severity="success"
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
                                    :severity="
                                        getFilterReasonSeverity(
                                            slotProps.option === 'Passed'
                                                ? null
                                                : slotProps.option
                                        )
                                    "
                                />
                            </template>
                        </Select>
                    </template>
                </Column>

                <!-- Dynamic columns based on table type -->
                <template v-if="tableName === 'epg_channels'">
                    <!-- Channel ID Column -->
                    <Column
                        field="channel_id"
                        header="Channel ID"
                        style="width: 150px"
                        :sortable="true"
                    >
                        <template #body="{ data }">
                            {{ data?.channel_id ?? "" }}
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
                    <Column
                        field="display_name"
                        header="Display Name"
                        style="width: 200px"
                        :sortable="true"
                    >
                        <template #body="{ data }">
                            {{ data?.display_name ?? "" }}
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
                    <Column
                        field="icon_url"
                        header="Icon URL"
                        style="width: 300px"
                        :sortable="true"
                    >
                        <template #body="{ data }">
                            <a
                                v-if="data?.icon_url"
                                :href="data?.icon_url"
                                target="_blank"
                                rel="noopener noreferrer"
                                class="url-link"
                            >
                                {{ data?.icon_url }}
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
                    <!-- Stream Mode Column-->
                    <Column
                        field="stream_mode"
                        header="Stream Mode"
                        :sortable="true"
                        :showFilterMenu="false"
                        :style="{ width: '100px', minWidth: '100px', maxWidth: '100px' }"
                    >
                        <template #body="{ data }">
                            <Tag
                                v-if="data?.stream_mode"
                                :value="data?.stream_mode"
                                severity="secondary"
                            />
                        </template>
                        <template #filter="{ filterModel, filterCallback }">
                            <Select
                                v-model="filterModel.value"
                                :options="streamModeOptions"
                                placeholder="All Stream Modes"
                                :show-clear="true"
                                @change="filterCallback()"
                                :style="{ width: '90px', minWidth: '90px' }"
                            >
                                <template #option="slotProps">
                                    <Tag
                                        :value="slotProps.option"
                                        severity="secondary"
                                    />
                                </template>
                            </Select>
                        </template>
                    </Column>
                    <!-- Group Column -->
                    <Column
                        field="group"
                        header="Group"
                        style="width: 150px"
                        :sortable="true"
                        :showFilterMenu="false"
                    >
                        <template #body="{ data }">
                            <Tag
                                v-if="data?.group"
                                :value="data?.group"
                                severity="secondary"
                            />
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
                                    <Tag
                                        :value="slotProps.option"
                                        severity="secondary"
                                    />
                                </template>
                            </Select>
                        </template>
                    </Column>

                    <!-- TVG ID Column -->
                    <Column
                        field="tvg_id"
                        header="TVG ID"
                        style="width: 150px"
                        :sortable="true"
                    >
                        <template #body="{ data }">
                            <code>{{ data?.tvg_id ?? "" }}</code>
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
                    <Column
                        field="name"
                        header="Name"
                        style="width: 250px"
                        :sortable="true"
                    >
                        <template #body="{ data }">
                            {{ data?.name ?? "" }}
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

                    <!-- Trace Column -->
                    <Column
                        field="_trace"
                        header="Trace"
                        :sortable="true"
                        :showFilterMenu="false"
                        :style="{ width: '400px', minWidth: '400px', maxWidth: '400px' }"
                    >
                        <template #body="{ data }">
                            <div v-if="data?._trace" :style="{ maxWidth: '100%', overflow: 'hidden' }">
                                <pre :style="{
                                    fontFamily: 'Courier New, monospace',
                                    fontSize: '11px',
                                    lineHeight: '1.3',
                                    margin: '0',
                                    padding: '4px 6px',
                                    background: '#2d3748',
                                    border: '1px solid #4a5568',
                                    borderRadius: '4px',
                                    whiteSpace: 'pre-wrap',
                                    wordWrap: 'break-word',
                                    maxHeight: '120px',
                                    overflowY: 'auto',
                                    color: '#e2e8f0'
                                }">{{ formatJSON(data._trace) }}</pre>
                            </div>
                            <span v-else :style="{ color: 'var(--p-text-muted-color)' }">No trace</span>
                        </template>
                        <template #filter="{ filterModel, filterCallback }">
                            <InputText
                                v-model="filterModel.value"
                                type="text"
                                placeholder="Search Trace..."
                                @input="filterCallback()"
                                :style="{ width: '380px', minWidth: '380px' }"
                            />
                        </template>
                    </Column>

                    <!-- Stream URL Column -->
                    <Column
                        field="stream_url"
                        header="Stream URL"
                        style="width: 600px"
                        :sortable="true"
                    >
                        <template #body="{ data }">
                            <a
                                :href="data?.stream_url"
                                target="_blank"
                                rel="noopener noreferrer"
                                class="url-link"
                            >
                                {{ data?.stream_url }}
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
                    <Column
                        field="logo_url"
                        header="Logo URL"
                        style="width: 400px"
                        :sortable="true"
                    >
                        <template #body="{ data }">
                            <a
                                v-if="data?.logo_url"
                                :href="data?.logo_url"
                                target="_blank"
                                rel="noopener noreferrer"
                                class="url-link"
                            >
                                {{ data?.logo_url }}
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
                    <Column
                        field="program_id"
                        header="Program ID"
                        style="width: 150px"
                        :sortable="true"
                    >
                        <template #body="{ data }">
                            {{ data?.program_id ?? "" }}
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
                    <Column
                        field="channel_id"
                        header="Channel ID"
                        style="width: 150px"
                        :sortable="true"
                    >
                        <template #body="{ data }">
                            {{ data?.channel_id ?? "" }}
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
                    <Column
                        field="title"
                        header="Title"
                        style="width: 250px"
                        :sortable="true"
                    >
                        <template #body="{ data }">
                            {{ data?.title ?? "" }}
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
                    <Column
                        field="description"
                        header="Description"
                        style="width: 600px"
                        :sortable="true"
                    >
                        <template #body="{ data }">
                            {{ data?.description ?? "" }}
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
                    <Column
                        field="start_time"
                        header="Start Time"
                        style="width: 180px"
                        :sortable="true"
                    >
                        <template #body="{ data }">
                            {{ formatDateTime(data?.start_time) }}
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
                    <Column
                        field="end_time"
                        header="End Time"
                        style="width: 180px"
                        :sortable="true"
                    >
                        <template #body="{ data }">
                            {{ formatDateTime(data?.end_time) }}
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
                <Column
                    field="created_at"
                    header="Created"
                    style="width: 180px"
                    :sortable="true"
                >
                    <template #body="{ data }">
                        {{ formatDateTime(data?.created_at) }}
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

                <Column
                    field="updated_at"
                    header="Updated"
                    style="width: 180px"
                    :sortable="true"
                >
                    <template #body="{ data }">
                        {{ formatDateTime(data?.updated_at) }}
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
        <div v-else-if="totalRecords === 0" class="empty-state">
            <i class="pi pi-inbox"></i>
            <h3>No Data Available</h3>
            <p>This table doesn't contain any data yet.</p>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { FilterMatchMode, FilterService } from "@primevue/core/api"
import { useToast } from "primevue/usetoast"
import { getFileTypeIcon } from "@/utils/fileUtils"
import { useToastListener } from "@/services/toastService"
import { fetchTablePage } from "@/api/tables"
import { searchIndex } from "@/api/search"

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
const tableData = ref([]) // rows for current page (server-side pagination)

// Search and filtering state
const filters = ref({})
const globalFilterFields = ref([])

// Meilisearch availability cache for this session (null = unknown)
const meiliAvailable = ref<null | boolean>(null)

// Pagination & sorting state
const page = ref(1)
const pageSize = ref(50)
const sortField = ref<string>("id")
const sortOrder = ref<"asc" | "desc">("asc")
const sortOrderNum = computed(() => (sortOrder.value === "asc" ? 1 : -1))

// Rules/filter view
const filterView = ref<"all" | "normal" | "inverse">("all")
const applyRules = ref(true)

// Filter statistics
const totalRecords = ref(0)
const passedRecords = ref(0)
const filteredRecords = ref(0)

// Column filter options
const sourceOptions = ref([])
const groupOptions = ref([])
const filterReasonOptions = ref([])
const streamModeOptions = ref([])

// Skeleton data for loading state (20 empty rows)
const skeletonData = ref(new Array(20).fill({}))

// Initialization guard to prevent duplicate loads
const isInitializing = ref(true)

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
                        style: "width: 60px",
                        type: "id",
                    },
                    {
                        field: "filter_reasons",
                        header: "Filter Reason",
                        style: "width: 200px",
                    },
                    {
                        field: "channel_id",
                        header: "Channel ID",
                        style: "width: 150px",
                    },
                    {
                        field: "display_name",
                        header: "Display Name",
                        style: "width: 200px",
                    },
                    {
                        field: "icon_url",
                        header: "Icon URL",
                        style: "width: 300px",
                        type: "url",
                    },
                    {
                        field: "created_at",
                        header: "Created",
                        style: "width: 180px",
                        type: "datetime",
                    },
                    {
                        field: "updated_at",
                        header: "Updated",
                        style: "width: 180px",
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
                        style: "width: 60px",
                        type: "id",
                    },
                    {
                        field: "filter_reasons",
                        header: "Filter Reason",
                        style: "width: 200px",
                    },
                    {
                        field: "group",
                        header: "Group",
                        style: "width: 150px",
                    },
                    {
                        field: "stream_mode",
                        header: "Stream Mode",
                        style: "width: 120px",
                    },
                    {
                        field: "tvg_id",
                        header: "TVG ID",
                        style: "width: 150px",
                    },
                    {
                        field: "name",
                        header: "Name",
                        style: "width: 250px",
                    },
                    {
                        field: "_trace",
                        header: "Trace",
                        style: "width: 200px",
                    },
                    {
                        field: "stream_url",
                        header: "Stream URL",
                        style: "width: 300px",
                        type: "url",
                    },
                    {
                        field: "logo_url",
                        header: "Logo URL",
                        style: "width: 300px",
                        type: "url",
                    },
                    {
                        field: "created_at",
                        header: "Created",
                        style: "width: 180px",
                        type: "datetime",
                    },
                    {
                        field: "updated_at",
                        header: "Updated",
                        style: "width: 180px",
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
                        style: "width: 60px",
                        type: "id",
                    },
                    {
                        field: "filter_reasons",
                        header: "Filter Reason",
                        style: "width: 200px",
                    },
                    {
                        field: "program_id",
                        header: "Program ID",
                        style: "width: 150px",
                    },
                    {
                        field: "channel_id",
                        header: "Channel ID",
                        style: "width: 150px",
                    },
                    {
                        field: "title",
                        header: "Title",
                        style: "width: 250px",
                    },
                    {
                        field: "description",
                        header: "Description",
                        style: "width: 600px",
                    },
                    {
                        field: "start_time",
                        header: "Start Time",
                        style: "width: 180px",
                        type: "datetime",
                    },
                    {
                        field: "end_time",
                        header: "End Time",
                        style: "width: 180px",
                        type: "datetime",
                    },
                    {
                        field: "created_at",
                        header: "Created",
                        style: "width: 180px",
                        type: "datetime",
                    },
                    {
                        field: "updated_at",
                        header: "Updated",
                        style: "width: 180px",
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

// Map table names to Meilisearch index names. Return null if unsupported.
const meiliIndexForTable = (name: string): string | null => {
    switch (name) {
        case "m3u_channels":
            return "m3u_channels"
        case "epg_channels":
            return "epg_channels"
        case "programs":
            return "programs"
        default:
            return null
    }
}

// Determine if we should use Meili for current query
// Only when a global search is present, table is supported, Meili isn't known-disabled,
// and no special rule-view filters (filter_reasons/inverse/normal) are active.
const shouldUseMeili = (
    globalFilter: string | null,
    name: string,
    columnFilters?: Record<string, any>,
    effectiveFilterView?: "all" | "normal" | "inverse"
): boolean => {
    const idx = meiliIndexForTable(name)
    
    // Debug logging
    console.debug("shouldUseMeili check:", {
        globalFilter,
        name,
        idx,
        meiliAvailable: meiliAvailable.value,
        effectiveFilterView,
        columnFilters,
        hasFilterReasons: columnFilters && Object.prototype.hasOwnProperty.call(columnFilters, "filter_reasons"),
        hasColumnFilters: columnFilters && Object.keys(columnFilters).length > 0
    })
    
    // Don't use Meilisearch if index doesn't exist or is disabled
    if (!idx || meiliAvailable.value === false) return false
    
    // Don't use Meilisearch for filter view changes (normal/inverse) as backend handles filter_reasons logic better
    if (effectiveFilterView && effectiveFilterView !== "all") return false
    
    // Don't use Meilisearch for filter_reasons column as backend has special logic for this
    if (columnFilters && Object.prototype.hasOwnProperty.call(columnFilters, "filter_reasons")) {
        return false
    }
    
    // Use Meilisearch if we have either a global filter OR column filters
    const hasGlobalFilter = globalFilter && globalFilter.trim().length > 0
    const hasColumnFilters = columnFilters && Object.keys(columnFilters).length > 0
    
    return hasGlobalFilter || hasColumnFilters
}

// Build Meili sort parameter
const buildMeiliSort = (): string[] => {
    return sortField.value ? [`${sortField.value}:${sortOrder.value}`] : []
}

// Build a conservative Meili filter expression from column filters (exact match only)
const buildMeiliFilterExpr = (columnFilters: Record<string, any>): string | undefined => {
    const parts: string[] = []
    for (const [field, val] of Object.entries(columnFilters || {})) {
        if (val === null || val === undefined || val === "") continue
        if (field === "filter_reasons") continue // skip special semantics; backend handles this better
        // Normalize value for Meili filter (wrap strings, leave numbers)
        if (typeof val === "number") {
            parts.push(`${field} = ${val}`)
        } else if (val instanceof Date) {
            parts.push(`${field} = "${val.toISOString()}"`)
        } else {
            const escaped = String(val).replace(/"/g, '\\"')
            parts.push(`${field} = "${escaped}"`)
        }
    }
    return parts.length > 0 ? parts.join(" AND ") : undefined
}

// Choose facet fields per table to populate filter dropdowns when using Meili
const meiliFacetsForTable = (name: string): string[] => {
    switch (name) {
        case "m3u_channels":
            return ["source", "group", "stream_mode", "filter_reasons"]
        case "epg_channels":
            return ["source", "filter_reasons"]
        case "programs":
            return ["source", "channel_id", "filter_reasons"]
        default:
            return []
    }
}

// Convert Meili facet distributions into Table filter option shape
const meiliFacetsToFilterValues = (facets: Record<string, any> | null | undefined): Record<string, { value: string; count: number }[]> => {
    const out: Record<string, { value: string; count: number }[]> = {}
    if (!facets) return out
    for (const [key, dist] of Object.entries(facets)) {
        if (dist && typeof dist === "object") {
            out[key] = Object.entries(dist as Record<string, number>)
                .map(([value, count]) => ({ value, count }))
                .sort((a, b) => b.count - a.count)
        }
    }
    return out
}

// Register custom filter constraint for filter_reasons
FilterService.register("filterReasonEquals", (value, filter) => {
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
        if (typeof value === "string" && value.startsWith("[")) {
            const filterReasons = JSON.parse(value)
            return (
                Array.isArray(filterReasons) && filterReasons.includes(filter)
            )
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
                matchMode: "filterReasonEquals",
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
const formatDateTime = (dateString: string | null | undefined): string => {
    if (!dateString) return "N/A"
    try {
        return new Date(dateString).toLocaleString()
    } catch {
        return dateString || "N/A"
    }
}

// Format filter reasons for display
const formatFilterReasons = (filterReasons: string | null): string => {
    if (
        !filterReasons ||
        filterReasons === "" ||
        filterReasons === "[]" ||
        filterReasons === null
    ) {
        return "Passed"
    }

    try {
        if (
            typeof filterReasons === "string" &&
            filterReasons.startsWith("[")
        ) {
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

// Helper to build current query filters and effective filter view
const buildCurrentQuery = () => {
    const config = tableConfig.value
    const columnFilters: Record<string, any> = {}
    let effectiveFilterView = filterView.value
    const globalFilter = (filters.value as any)?.global?.value || null

    for (const col of config.columns) {
        const f = (filters.value as any)[col.field]
        if (!f || f.value === null || f.value === undefined || f.value === "")
            continue

        if (col.field === "filter_reasons") {
            if (f.value === "Passed") {
                effectiveFilterView = "normal"
                continue
            } else {
                effectiveFilterView = "inverse"
                columnFilters[col.field] = f.value
                continue
            }
        }

        if (col.type === "datetime") {
            const v = f.value
            columnFilters[col.field] = v instanceof Date ? v.toISOString() : v
        } else {
            columnFilters[col.field] = f.value
        }
    }

    return {
        globalFilter,
        columnFilters,
        effectiveFilterView,
    }
}

// Function to load table data with conditional Meili usage
const loadTableData = async () => {
    loading.value = true
    error.value = ""
    tableData.value = []
    totalRecords.value = 0
    try {
        const { globalFilter, columnFilters, effectiveFilterView } =
            buildCurrentQuery()
        const useMeili = shouldUseMeili(
            globalFilter,
            tableName.value,
            columnFilters,
            effectiveFilterView
        )

        if (useMeili) {
            // Attempt Meilisearch; fallback to backend if fails
            try {
                const idx = meiliIndexForTable(tableName.value) as string
                const meiliResp = await searchIndex<Record<string, any>>(
                    sourceName.value,
                    idx,
                    {
                        q: globalFilter || "",
                        offset: 0,
                        limit: pageSize.value,
                        filter: buildMeiliFilterExpr(columnFilters),
                        sort: buildMeiliSort(),
                        facets: meiliFacetsForTable(tableName.value),
                    },
                    false
                )

                const hits = meiliResp.hits || []
                tableData.value = hits
                const total =
                    (meiliResp as any).totalHits ?? meiliResp.estimatedTotalHits ?? hits.length
                totalRecords.value = typeof total === "number" ? total : hits.length

                // Convert facets to filter options
                const facetFilters = meiliFacetsToFilterValues(
                    meiliResp.facetDistribution || meiliResp.facetsDistribution
                )
                sourceOptions.value = (facetFilters.source || []).map((x: any) => x.value)
                if (tableName.value === "m3u_channels") {
                    groupOptions.value = (facetFilters.group || []).map((x: any) => x.value)
                    streamModeOptions.value = (facetFilters.stream_mode || []).map(
                        (x: any) => x.value
                    )
                }
                filterReasonOptions.value = (
                    (facetFilters.filter_reasons || []).map((x: any) => x.value) || []
                )
                    .concat("Passed")
                    .filter((v: any, i: number, arr: any[]) => arr.indexOf(v) === i)

                // We don't have filter_view_counts from Meili; derive minimal stats
                passedRecords.value = 0
                filteredRecords.value = 0
                meiliAvailable.value = true
            } catch (meiliErr) {
                const errMsg = meiliErr instanceof Error ? meiliErr.message : String(meiliErr)
                console.warn("Meilisearch failed; falling back to backend:", errMsg, meiliErr)
                meiliAvailable.value = false
                // Fallback to backend pagination
                const resp = await fetchTablePage<Record<string, any>>(
                    sourceName.value,
                    tableName.value,
                    {
                        page: 1,
                        page_size: pageSize.value,
                        sort_field: sortField.value,
                        sort_order: sortOrder.value,
                        global_filter: globalFilter,
                        column_filters:
                            Object.keys(columnFilters).length > 0
                                ? columnFilters
                                : null,
                        apply_rules: applyRules.value,
                        filter_view: effectiveFilterView,
                    },
                    false
                )

                if (resp && resp.success) {
                    tableData.value = resp.data || []
                    totalRecords.value = resp.filter_view_counts?.all ?? resp.total ?? 0

                    const f = resp.filters || {}
                    sourceOptions.value = (f.source || []).map((x: any) => x.value)
                    if (tableName.value === "m3u_channels") {
                        groupOptions.value = (f.group || []).map((x: any) => x.value)
                        streamModeOptions.value = (f.stream_mode || []).map(
                            (x: any) => x.value
                        )
                    }
                    filterReasonOptions.value = (
                        (f.filter_reasons || []).map((x: any) => x.value) || []
                    )
                        .concat("Passed")
                        .filter((v: any, i: number, arr: any[]) => arr.indexOf(v) === i)

                    passedRecords.value = resp.filter_view_counts?.normal ?? 0
                    filteredRecords.value =
                        resp.filter_view_counts?.inverse ??
                        Math.max(0, totalRecords.value - passedRecords.value)
                } else {
                    throw new Error("Failed to load table data")
                }
            }
        } else {
            // Use existing backend pagination
            const resp = await fetchTablePage<Record<string, any>>(
                sourceName.value,
                tableName.value,
                {
                    page: 1,
                    page_size: pageSize.value,
                    sort_field: sortField.value,
                    sort_order: sortOrder.value,
                    global_filter: globalFilter,
                    column_filters:
                        Object.keys(columnFilters).length > 0
                            ? columnFilters
                            : null,
                    apply_rules: applyRules.value,
                    filter_view: effectiveFilterView,
                },
                false
            )

            if (resp && resp.success) {
                tableData.value = resp.data || []

                // Update counts and totals
                totalRecords.value = resp.filter_view_counts?.all ?? resp.total ?? 0

                // Update filter options from response
                const f = resp.filters || {}
                sourceOptions.value = (f.source || []).map((x: any) => x.value)
                if (tableName.value === "m3u_channels") {
                    groupOptions.value = (f.group || []).map((x: any) => x.value)
                    streamModeOptions.value = (f.stream_mode || []).map(
                        (x: any) => x.value
                    )
                }
                filterReasonOptions.value = (
                    (f.filter_reasons || []).map((x: any) => x.value) || []
                )
                    .concat("Passed")
                    .filter((v: any, i: number, arr: any[]) => arr.indexOf(v) === i)

                passedRecords.value = resp.filter_view_counts?.normal ?? 0
                filteredRecords.value =
                    resp.filter_view_counts?.inverse ??
                    Math.max(0, totalRecords.value - passedRecords.value)
            } else {
                throw new Error("Failed to load table data")
            }
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

// Pagination & sorting handlers (server-side)
const onSort = (event: any) => {
    const newSortField = event.sortField || sortField.value
    const newSortOrder = event.sortOrder === 1 ? "asc" : "desc"

    // Avoid reloading if sort hasn't actually changed
    if (
        newSortField === sortField.value &&
        newSortOrder === sortOrder.value
    ) {
        return
    }

    sortField.value = newSortField
    sortOrder.value = newSortOrder
    page.value = 1
    loadTableData()
}

// Paginator lazy load handler
const onPage = async (event: any) => {
    try {
        console.debug("onPage event", event)
        loading.value = true
        error.value = ""
        const first = Number(event?.first ?? 0)
        const rows = Number(event?.rows ?? pageSize.value)
        const newPage = Math.floor(first / rows) + 1
        pageSize.value = rows
        page.value = newPage

        const { globalFilter, columnFilters, effectiveFilterView } =
            buildCurrentQuery()
        const useMeili = shouldUseMeili(
            globalFilter,
            tableName.value,
            columnFilters,
            effectiveFilterView
        )

        if (useMeili) {
            try {
                const idx = meiliIndexForTable(tableName.value) as string
                const meiliResp = await searchIndex<Record<string, any>>(
                    sourceName.value,
                    idx,
                    {
                        q: globalFilter || "",
                        offset: (page.value - 1) * pageSize.value,
                        limit: pageSize.value,
                        filter: buildMeiliFilterExpr(columnFilters),
                        sort: buildMeiliSort(),
                        facets: meiliFacetsForTable(tableName.value),
                    },
                    false
                )

                const hits = meiliResp.hits || []
                tableData.value = hits
                const total =
                    (meiliResp as any).totalHits ?? meiliResp.estimatedTotalHits ?? hits.length
                totalRecords.value = typeof total === "number" ? total : hits.length

                const facetFilters = meiliFacetsToFilterValues(
                    meiliResp.facetDistribution || meiliResp.facetsDistribution
                )
                sourceOptions.value = (facetFilters.source || []).map((x: any) => x.value)
                if (tableName.value === "m3u_channels") {
                    groupOptions.value = (facetFilters.group || []).map((x: any) => x.value)
                    streamModeOptions.value = (facetFilters.stream_mode || []).map(
                        (x: any) => x.value
                    )
                }
                filterReasonOptions.value = (
                    (facetFilters.filter_reasons || []).map((x: any) => x.value) || []
                )
                    .concat("Passed")
                    .filter((v: any, i: number, arr: any[]) => arr.indexOf(v) === i)

                passedRecords.value = 0
                filteredRecords.value = 0
                meiliAvailable.value = true
            } catch (meiliErr) {
                const errMsg = meiliErr instanceof Error ? meiliErr.message : String(meiliErr)
                console.warn("Meili page search failed; falling back:", errMsg, meiliErr)
                meiliAvailable.value = false
                const resp = await fetchTablePage<Record<string, any>>(
                    sourceName.value,
                    tableName.value,
                    {
                        page: page.value,
                        page_size: pageSize.value,
                        sort_field: sortField.value,
                        sort_order: sortOrder.value,
                        global_filter: globalFilter,
                        column_filters:
                            Object.keys(columnFilters).length > 0
                                ? columnFilters
                                : null,
                        apply_rules: applyRules.value,
                        filter_view: effectiveFilterView,
                    },
                    false
                )

                if (resp && resp.success) {
                    tableData.value = resp.data || []
                    totalRecords.value = resp.filter_view_counts?.all ?? resp.total ?? 0

                    const f = resp.filters || {}
                    sourceOptions.value = (f.source || []).map((x: any) => x.value)
                    if (tableName.value === "m3u_channels") {
                        groupOptions.value = (f.group || []).map((x: any) => x.value)
                        streamModeOptions.value = (f.stream_mode || []).map(
                            (x: any) => x.value
                        )
                    }
                    filterReasonOptions.value = (
                        (f.filter_reasons || []).map((x: any) => x.value) || []
                    )
                        .concat("Passed")
                        .filter((v: any, i: number, arr: any[]) => arr.indexOf(v) === i)

                    passedRecords.value = resp.filter_view_counts?.normal ?? 0
                    filteredRecords.value =
                        resp.filter_view_counts?.inverse ??
                        Math.max(0, totalRecords.value - passedRecords.value)
                } else {
                    throw new Error("Failed to load page")
                }
            }
        } else {
            const resp = await fetchTablePage<Record<string, any>>(
                sourceName.value,
                tableName.value,
                {
                    page: page.value,
                    page_size: pageSize.value,
                    sort_field: sortField.value,
                    sort_order: sortOrder.value,
                    global_filter: globalFilter,
                    column_filters:
                        Object.keys(columnFilters).length > 0
                            ? columnFilters
                            : null,
                    apply_rules: applyRules.value,
                    filter_view: effectiveFilterView,
                },
                false
            )

            if (resp && resp.success) {
                tableData.value = resp.data || []
                totalRecords.value = resp.filter_view_counts?.all ?? resp.total ?? 0

                const f = resp.filters || {}
                sourceOptions.value = (f.source || []).map((x: any) => x.value)
                if (tableName.value === "m3u_channels") {
                    groupOptions.value = (f.group || []).map((x: any) => x.value)
                    streamModeOptions.value = (f.stream_mode || []).map(
                        (x: any) => x.value
                    )
                }
                filterReasonOptions.value = (
                    (f.filter_reasons || []).map((x: any) => x.value) || []
                )
                    .concat("Passed")
                    .filter((v: any, i: number, arr: any[]) => arr.indexOf(v) === i)

                passedRecords.value = resp.filter_view_counts?.normal ?? 0
                filteredRecords.value =
                    resp.filter_view_counts?.inverse ??
                    Math.max(0, totalRecords.value - passedRecords.value)
            } else {
                throw new Error("Failed to load page")
            }
        }
    } catch (err) {
        console.error("Error loading page:", err)
        error.value =
            err instanceof Error ? err.message : "Unknown error occurred"
    } finally {
        loading.value = false
    }
}

// Filter view toggle
const setFilterView = (view: "all" | "normal" | "inverse") => {
    if (filterView.value !== view) {
        filterView.value = view
    }
}

// Debounced reload on filter changes
let filterTimer: any = null
const scheduleReload = () => {
    // Suppress during initial setup to avoid duplicate initial load
    if (isInitializing.value) return
    if (filterTimer) clearTimeout(filterTimer)
    filterTimer = setTimeout(() => {
        page.value = 1
        loadTableData()
    }, 300)
}
watch(
    () => filters.value,
    () => {
        scheduleReload()
    },
    { deep: true }
)
watch(
    () => filterView.value,
    () => {
        scheduleReload()
    }
)

// Load data on component mount
onMounted(async () => {
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
    await loadTableData()
    isInitializing.value = false
})

// Format JSON for display
const formatJSON = (jsonData: string | object | null): string => {
    if (!jsonData) return ''
    
    try {
        // If it's already a string, try to parse it first
        let parsed = jsonData
        if (typeof jsonData === 'string') {
            parsed = JSON.parse(jsonData)
        }
        
        // Return formatted JSON with 2-space indentation
        return JSON.stringify(parsed, null, 2)
    } catch (error) {
        // If parsing fails, return the original string
        return typeof jsonData === 'string' ? jsonData : JSON.stringify(jsonData)
    }
}
</script>

<style scoped>
.json-display {
    max-width: 100%;
    overflow: hidden;
}

.json-display pre {
    font-family: 'Courier New', monospace;
    font-size: 11px;
    line-height: 1.3;
    margin: 0;
    padding: 4px 6px;
    background: var(--p-surface-50);
    border: 1px solid var(--p-surface-200);
    border-radius: 4px;
    white-space: pre-wrap;
    word-wrap: break-word;
    max-height: 120px;
    overflow-y: auto;
    color: var(--p-text-color);
}

.json-display pre::-webkit-scrollbar {
    width: 4px;
}

.json-display pre::-webkit-scrollbar-track {
    background: var(--p-surface-100);
}

.json-display pre::-webkit-scrollbar-thumb {
    background: var(--p-surface-300);
    border-radius: 2px;
}

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

/* Allow cells to wrap content for full visibility */
:deep(.p-datatable-table) {
    table-layout: auto;
}

:deep(.p-datatable-tbody > tr > td) {
    white-space: normal;
    overflow-wrap: anywhere;
    word-break: break-word;
    line-height: 1.35;
    vertical-align: top;
    padding-top: 0.5rem;
    padding-bottom: 0.5rem;
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

.url-link {
    font-family: monospace;
    font-size: 0.875rem;
    white-space: normal;
    overflow-wrap: anywhere;
    word-break: break-word;
    max-width: 100%;
    display: inline;
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
