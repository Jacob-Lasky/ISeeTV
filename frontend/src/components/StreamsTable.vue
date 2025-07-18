<template>
    <div class="streams-table">
        <!-- Loading state with skeleton -->
        <div v-if="loading" class="loading-container">
            <DataTable
                :value="skeletonData"
                scrollable
                scrollHeight="calc(100vh - 320px)"
                class="streams-datatable skeleton-table"
            >
                <!-- Skeleton Channel Name Column -->
                <Column
                    field="name"
                    header="Channel Name"
                    style="min-width: 200px"
                >
                    <template #body>
                        <div class="channel-name-cell">
                            <Skeleton
                                width="32px"
                                height="32px"
                                borderRadius="4px"
                                class="skeleton-logo"
                            />
                            <div class="channel-info">
                                <Skeleton
                                    height="1rem"
                                    width="120px"
                                    class="skeleton-name"
                                />
                                <Skeleton
                                    height="0.75rem"
                                    width="80px"
                                    class="skeleton-display-name"
                                />
                            </div>
                        </div>
                    </template>
                </Column>

                <!-- Skeleton TVG ID Column -->
                <Column field="tvg_id" header="TVG ID" style="min-width: 150px">
                    <template #body>
                        <Skeleton
                            height="1rem"
                            width="80%"
                            borderRadius="4px"
                        />
                    </template>
                </Column>

                <!-- Skeleton Source Column -->
                <Column field="source" header="Source" style="min-width: 120px">
                    <template #body>
                        <Skeleton
                            height="1.5rem"
                            width="70%"
                            borderRadius="12px"
                        />
                    </template>
                </Column>

                <!-- Skeleton Group Column -->
                <Column field="group" header="Group" style="min-width: 150px">
                    <template #body>
                        <Skeleton
                            height="1.5rem"
                            width="85%"
                            borderRadius="12px"
                        />
                    </template>
                </Column>

                <!-- Skeleton Program Count Column -->
                <Column
                    field="program_count"
                    header="Programs"
                    style="min-width: 100px"
                >
                    <template #body>
                        <div class="program-count">
                            <Skeleton
                                width="2rem"
                                height="1.5rem"
                                borderRadius="12px"
                            />
                        </div>
                    </template>
                </Column>

                <!-- Skeleton Next Program Column -->
                <Column header="Next Program" style="min-width: 200px">
                    <template #body>
                        <div class="next-program">
                            <Skeleton height="0.875rem" class="mb-1" />
                            <Skeleton height="0.75rem" width="60%" />
                        </div>
                    </template>
                </Column>

                <!-- Skeleton Actions Column -->
                <Column header="Actions" style="min-width: 150px">
                    <template #body>
                        <div class="action-buttons">
                            <Skeleton
                                width="2rem"
                                height="2rem"
                                borderRadius="4px"
                            />
                            <Skeleton
                                width="2rem"
                                height="2rem"
                                borderRadius="4px"
                            />
                        </div>
                    </template>
                </Column>
            </DataTable>
        </div>

        <!-- Data Table -->
        <DataTable
            v-else
            v-model:filters="filters"
            :value="streams"
            :lazy="true"
            :paginator="true"
            :rows="pageSize"
            :totalRecords="totalRecords"
            :loading="false"
            :rowsPerPageOptions="[50, 100, 200, 500]"
            :sortField="sortField"
            :sortOrder="sortOrder === 'asc' ? 1 : -1"
            responsiveLayout="scroll"
            dataKey="m3u_id"
            scrollable
            scrollHeight="calc(100vh - 320px)"
            striped-rows
            paginatorTemplate="RowsPerPageDropdown FirstPageLink PrevPageLink CurrentPageReport NextPageLink LastPageLink"
            currentPageReportTemplate="{first} to {last} of {totalRecords}"
            filterDisplay="row"
            :globalFilterFields="globalFilterFields"
            class="streams-datatable"
            @page="onPageChange"
            @sort="onSort"
            @filter="onFilter"
        >
            <template #header>
                <div class="flex justify-between align-items-center">
                    <!-- Filter Visibility Toggle -->
                    <div class="filter-visibility-toggle">
                        <div class="toggle-label">Filter View:</div>
                        <div class="toggle-buttons">
                            <Button
                                :class="{
                                    'p-button-primary': filterView === 'normal',
                                    'p-button-outlined':
                                        filterView !== 'normal',
                                }"
                                :label="`Normal (${filterViewCounts.normal || 0})`"
                                @click="setFilterView('normal')"
                            />
                            <Button
                                :class="{
                                    'p-button-primary':
                                        filterView === 'inverse',
                                    'p-button-outlined':
                                        filterView !== 'inverse',
                                }"
                                :label="`Inverse (${filterViewCounts.inverse || 0})`"
                                @click="setFilterView('inverse')"
                            />
                            <Button
                                :class="{
                                    'p-button-primary': filterView === 'all',
                                    'p-button-outlined': filterView !== 'all',
                                }"
                                :label="`All (${filterViewCounts.all || 0})`"
                                @click="setFilterView('all')"
                            />
                        </div>
                    </div>

                    <!-- Search and Filters -->
                    <div class="flex align-items-center gap-2">
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
                </div>
            </template>

            <!-- Channel Name Column -->
            <Column
                field="name"
                header="Channel Name"
                :sortable="true"
                style="min-width: 200px"
                :filterField="'name'"
            >
                <template #body="{ data }">
                    <div class="channel-name-cell">
                        <img
                            v-if="data.logo_url || data.icon_url"
                            :src="data.logo_url || data.icon_url"
                            :alt="data.name"
                            class="channel-logo"
                            @error="onImageError"
                        />
                        <div class="channel-info">
                            <div class="channel-name">{{ data.name }}</div>
                            <div
                                v-if="
                                    data.display_name &&
                                    data.display_name !== data.name
                                "
                                class="channel-display-name"
                            >
                                {{ data.display_name }}
                            </div>
                        </div>
                    </div>
                </template>
                <template #filter="{ filterModel, filterCallback }">
                    <InputText
                        v-model="filterModel.value"
                        type="text"
                        placeholder="Search channel name..."
                        class="w-full"
                        @input="filterCallback()"
                    />
                </template>
            </Column>

            <!-- TVG ID Column -->
            <Column
                field="tvg_id"
                header="TVG ID"
                :sortable="true"
                style="min-width: 150px"
                :filterField="'tvg_id'"
            >
                <template #body="{ data }">
                    <code class="tvg-id">{{ data.tvg_id }}</code>
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

            <!-- Source Column -->
            <Column
                field="source"
                header="Source"
                :sortable="true"
                style="min-width: 120px"
                :filterField="'source'"
            >
                <template #body="{ data }">
                    <Tag :value="data.source" severity="info" />
                </template>
                <template #filter="{ filterModel, filterCallback }">
                    <Select
                        v-model="filterModel.value"
                        :options="sourceFilterOptions"
                        placeholder="All Sources"
                        class="w-full"
                        :show-clear="true"
                        @change="filterCallback()"
                    />
                </template>
            </Column>

            <!-- Group Column -->
            <Column
                field="group"
                header="Group"
                :sortable="true"
                style="min-width: 150px"
                :filterField="'group'"
            >
                <template #body="{ data }">
                    <Tag
                        v-if="data.group"
                        :value="data.group"
                        severity="secondary"
                    />
                    <span v-else class="no-group">—</span>
                </template>
                <template #filter="{ filterModel, filterCallback }">
                    <Select
                        v-model="filterModel.value"
                        :options="groupFilterOptions"
                        placeholder="All Groups"
                        class="w-full"
                        :show-clear="true"
                        @change="filterCallback()"
                    />
                </template>
            </Column>

            <!-- Filter Reason Column -->
            <Column
                field="filter_reasons"
                header="Filter Status"
                :sortable="true"
                style="min-width: 200px"
                :filterField="'filter_reasons'"
            >
                <template #body="{ data }">
                    <div v-if="data.filter_reasons" class="filter-reason">
                        <Tag
                            :value="
                                data.filter_reasons.includes('Blacklisted')
                                    ? 'Filtered'
                                    : 'Not Whitelisted'
                            "
                            :severity="
                                data.filter_reasons.includes('Blacklisted')
                                    ? 'danger'
                                    : 'warn'
                            "
                        />
                        <div
                            class="filter-detail"
                            v-tooltip="data.filter_reasons"
                        >
                            {{
                                data.filter_reasons.length > 50
                                    ? data.filter_reasons.substring(0, 50) +
                                      "..."
                                    : data.filter_reasons
                            }}
                        </div>
                    </div>
                    <Tag v-else value="Active" severity="success" />
                </template>
                <template #filter="{ filterModel, filterCallback }">
                    <Select
                        v-model="filterModel.value"
                        :options="filterStatusOptions"
                        placeholder="All Status"
                        class="w-full"
                        :show-clear="true"
                        @change="filterCallback()"
                    />
                </template>
            </Column>

            <!-- Program Count Column -->
            <Column
                field="program_count"
                header="Programs"
                :sortable="true"
                style="min-width: 100px"
            >
                <template #body="{ data }">
                    <div class="program-count">
                        <Badge
                            :value="data.program_count"
                            :severity="
                                data.program_count > 0 ? 'success' : 'secondary'
                            "
                        />
                    </div>
                </template>
            </Column>

            <!-- Next Program Column -->
            <Column header="Next Program" style="min-width: 200px">
                <template #body="{ data }">
                    <div v-if="data.next_program_title" class="next-program">
                        <div class="program-title">
                            {{ data.next_program_title }}
                        </div>
                        <div
                            v-if="data.next_program_start"
                            class="program-time"
                        >
                            {{ formatDateTime(data.next_program_start) }}
                        </div>
                    </div>
                    <span v-else class="no-program">No upcoming programs</span>
                </template>
            </Column>

            <!-- Actions Column -->
            <Column header="Actions" style="min-width: 150px">
                <template #body="{ data }">
                    <div class="action-buttons">
                        <Button
                            icon="pi pi-video"
                            severity="info"
                            size="small"
                            outlined
                            v-tooltip="'View Programs'"
                            @click="viewPrograms(data)"
                        />
                        <Button
                            icon="pi pi-external-link"
                            severity="secondary"
                            size="small"
                            outlined
                            v-tooltip="'Open Stream'"
                            @click="openStream(data)"
                        />
                    </div>
                </template>
            </Column>

            <!-- Empty State -->
            <template #empty>
                <div class="empty-state">
                    <i
                        class="pi pi-video"
                        style="
                            font-size: 3rem;
                            color: var(--text-color-secondary);
                        "
                    ></i>
                    <h3>No streams found</h3>
                    <p>Try adjusting your filters or search terms.</p>
                </div>
            </template>

            <!-- Loading State -->
            <template #loading>
                <div class="loading-state">
                    <ProgressSpinner />
                    <p>Loading streams...</p>
                </div>
            </template>
        </DataTable>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue"
import { useRouter } from "vue-router"
import { useToast } from "primevue/usetoast"
import { FilterMatchMode } from "@primevue/core/api"
import DataTable from "primevue/datatable"
import Column from "primevue/column"
import Button from "primevue/button"
import InputText from "primevue/inputtext"
import Select from "primevue/select"
import Tag from "primevue/tag"
import Badge from "primevue/badge"
import ProgressSpinner from "primevue/progressspinner"
import Skeleton from "primevue/skeleton"
import IconField from "primevue/iconfield"
import InputIcon from "primevue/inputicon"
import type {
    StreamChannel,
    StreamsResponse,
    FilterValue,
    FilterViewCounts,
} from "@/types/types"

// Composables
const router = useRouter()
const toast = useToast()

// Reactive state
const streams = ref<StreamChannel[]>([])
const loading = ref(false)
const totalRecords = ref(0)
const pageSize = ref(100)
const currentPage = ref(1)
const sortField = ref("name")
const sortOrder = ref<"asc" | "desc">("asc")
const globalFilter = ref("")
const selectedSource = ref<string | null>(null)
const selectedGroup = ref<string | null>(null)

// Filter view toggle state
const filterView = ref<"normal" | "inverse" | "all">("normal")
const filterViewCounts = ref<{
    normal: number
    inverse: number
    all: number
}>({
    normal: 0,
    inverse: 0,
    all: 0,
})

// Filter options (for header dropdowns)
const sourceOptions = ref<{ label: string; value: string }[]>([])
const groupOptions = ref<{ label: string; value: string }[]>([])

// Column filter options (for DataTable column filters)
const sourceFilterOptions = ref<string[]>([])
const groupFilterOptions = ref<string[]>([])
const filterStatusOptions = ref<{ label: string; value: string }[]>([
    { label: "Active", value: "null" },
    { label: "Filtered", value: "filtered" },
    { label: "Not Whitelisted", value: "not_whitelisted" },
])

// PrimeVue DataTable filters
const filters = ref({
    global: { value: null, matchMode: FilterMatchMode.CONTAINS },
    name: { value: null, matchMode: FilterMatchMode.CONTAINS },
    tvg_id: { value: null, matchMode: FilterMatchMode.CONTAINS },
    source: { value: null, matchMode: FilterMatchMode.CONTAINS },
    group: { value: null, matchMode: FilterMatchMode.CONTAINS },
    filter_reasons: { value: "null", matchMode: FilterMatchMode.EQUALS }, // Default to show only active (non-filtered) records
})
const globalFilterFields = ref<string[]>([
    "name",
    "tvg_id",
    "source",
    "group",
    "filter_reasons",
])

// Skeleton data for loading state (15 empty rows)
const skeletonData = ref(new Array(15).fill({}))

// Debounce timer for search
let searchTimeout: NodeJS.Timeout | null = null

// Computed properties
const totalPages = computed(() =>
    Math.ceil(totalRecords.value / pageSize.value)
)
const hasNext = computed(() => currentPage.value < totalPages.value)
const hasPrev = computed(() => currentPage.value > 1)

// Atomic functions
const buildApiUrl = (): string => {
    const params = new URLSearchParams({
        page: currentPage.value.toString(),
        page_size: pageSize.value.toString(),
        sort_field: sortField.value,
        sort_order: sortOrder.value,
        filter_view: filterView.value,
    })

    if (globalFilter.value) {
        params.append("global_filter", globalFilter.value)
    }

    if (selectedSource.value) {
        params.append("source", selectedSource.value)
    }

    if (selectedGroup.value) {
        params.append("group", selectedGroup.value)
    }

    return `/api/streams?${params.toString()}`
}

const loadStreams = async (resetPage = false): Promise<void> => {
    if (resetPage) {
        currentPage.value = 1
    }

    loading.value = true

    try {
        const response = await fetch(buildApiUrl())

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }

        const data: StreamsResponse = await response.json()

        if (data.success) {
            streams.value = data.data
            totalRecords.value = data.total
            currentPage.value = data.page

            // Update filter view counts if available
            if (data.filter_view_counts) {
                filterViewCounts.value = {
                    normal: data.filter_view_counts.normal || 0,
                    inverse: data.filter_view_counts.inverse || 0,
                    all: data.filter_view_counts.all || 0,
                }
            }

            // Update filter options if available
            if (data.filters && Object.keys(data.filters).length > 0) {
                console.log("API response filters:", Object.keys(data.filters).length, "filter types")
                updateFilterOptions(data.filters)
            } else {
                console.log(
                    "No filters in API response, attempting to precompute..."
                )
                try {
                    await precomputeFilterValues()
                    // Reload streams data after precomputing filters
                    const retryResponse = await fetch(buildApiUrl())
                    if (retryResponse.ok) {
                        const retryData: StreamsResponse =
                            await retryResponse.json()
                        if (retryData.success && retryData.filters) {
                            console.log(
                                "Retry API response filters:",
                                Object.keys(retryData.filters).length, "filter types"
                            )
                            updateFilterOptions(retryData.filters)
                        }
                    }
                } catch (error) {
                    console.error("Failed to precompute filter values:", error)
                    // Continue without filters - the table will still work
                }
            }
        } else {
            throw new Error("API returned success: false")
        }
    } catch (error) {
        console.error("Error loading streams:", error)
        toast.add({
            severity: "error",
            summary: "Error",
            detail: "Failed to load streams. Please try again.",
            life: 5000,
        })
        streams.value = []
        totalRecords.value = 0
    } finally {
        loading.value = false
    }
}

const updateFilterOptions = (filters: Record<string, FilterValue[]>): void => {
    console.log("Updating filter options with", Object.keys(filters).length, "filter types")

    if (filters.source) {
        // Update header dropdown options
        sourceOptions.value = filters.source.map((f) => ({
            label: `${f.value} (${f.count})`,
            value: f.value,
        }))

        // Update column filter options
        sourceFilterOptions.value = filters.source.map((f) => f.value)
        console.log("Updated sourceFilterOptions:", sourceFilterOptions.value.length, "options")
    }

    if (filters.group) {
        // Update header dropdown options
        groupOptions.value = filters.group.map((f) => ({
            label: `${f.value} (${f.count})`,
            value: f.value,
        }))

        // Update column filter options
        groupFilterOptions.value = filters.group.map((f) => f.value)
        console.log(
            "Updated groupFilterOptions:",
            groupFilterOptions.value.length,
            "options"
        )
    } else {
        console.log("No group filters found in API response")
    }
}

const precomputeFilterValues = async (): Promise<void> => {
    try {
        console.log("Precomputing streams filter values...")
        const response = await fetch("/api/streams/precompute-filters", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
        })

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }

        const result = await response.json()
        console.log("Filter values precomputed successfully:", result)
    } catch (error) {
        console.error("Error precomputing filter values:", error)
        throw error
    }
}

// Initialize PrimeVue DataTable filters (now done at initialization)
const initializeFilters = (): void => {
    // Filters are now initialized immediately in the ref declaration
    // This function is kept for potential future use
}

// Handle DataTable filter events
const onFilter = (event: any): void => {
    // The DataTable handles client-side filtering automatically
    // We can add custom logic here if needed
    console.log("Filter event:", event)
}

const formatDateTime = (dateString: string): string => {
    try {
        const date = new Date(dateString)
        return date.toLocaleString()
    } catch {
        return dateString
    }
}

const onImageError = (event: Event): void => {
    const img = event.target as HTMLImageElement
    img.style.display = "none"
}

// Event handlers
const onPageChange = (event: any): void => {
    currentPage.value = event.page + 1
    pageSize.value = event.rows
    loadStreams()
}

const onSort = (event: any): void => {
    sortField.value = event.sortField
    sortOrder.value = event.sortOrder === 1 ? "asc" : "desc"
    loadStreams(true)
}

const onGlobalFilterChange = (): void => {
    if (searchTimeout) {
        clearTimeout(searchTimeout)
    }

    searchTimeout = setTimeout(() => {
        loadStreams(true)
    }, 500)
}

const onSourceFilterChange = (): void => {
    loadStreams(true)
}

const onGroupFilterChange = (): void => {
    loadStreams(true)
}

const viewPrograms = (stream: StreamChannel): void => {
    router.push(`/streams/${stream.source}/${stream.tvg_id}/programs`)
}

const openStream = (stream: StreamChannel): void => {
    if (stream.stream_url) {
        window.open(stream.stream_url, "_blank")
    } else {
        toast.add({
            severity: "warn",
            summary: "No Stream URL",
            detail: "This channel does not have a stream URL available.",
            life: 3000,
        })
    }
}

// Filter view toggle function
const setFilterView = (view: "normal" | "inverse" | "all"): void => {
    filterView.value = view
    loadStreams(true) // Reset to first page when changing filter view
}

// Lifecycle
onMounted(() => {
    loadStreams()
})

// Cleanup
const cleanup = (): void => {
    if (searchTimeout) {
        clearTimeout(searchTimeout)
    }
}

// Watch for cleanup on unmount
watch(() => {}, cleanup)
</script>

<style scoped>
.streams-table {
    width: 100%;
    height: 100%;
}

.table-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-bottom: 1rem;
    gap: 1rem;
    flex-wrap: wrap;
}

.header-left {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
}

.header-right {
    display: flex;
    gap: 1rem;
}

.filter-group,
.search-group {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.filter-group label,
.search-group label {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-color);
}

.filter-select {
    min-width: 150px;
}

.search-input {
    min-width: 200px;
}

/* Filter Visibility Toggle Styles */
.filter-visibility-toggle {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.toggle-label {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-color);
    white-space: nowrap;
}

.toggle-buttons {
    display: flex;
    gap: 0.5rem;
}

.toggle-buttons .p-button {
    font-size: 0.875rem;
    padding: 0.375rem 0.75rem;
    border-radius: 4px;
    transition: all 0.2s ease;
}

.toggle-buttons .p-button.p-button-outlined {
    background: var(--surface-ground);
    border-color: var(--surface-border);
    color: var(--text-color-secondary);
}

.toggle-buttons .p-button.p-button-outlined:hover {
    background: var(--surface-hover);
    border-color: var(--primary-color);
    color: var(--primary-color);
}

.toggle-buttons .p-button.p-button-primary {
    background: var(--primary-color);
    border-color: var(--primary-color);
    color: var(--primary-color-text);
}

.streams-datatable {
    border-radius: 6px;
    overflow: hidden;
}

.channel-name-cell {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.channel-logo {
    width: 32px;
    height: 32px;
    object-fit: contain;
    border-radius: 4px;
    background: var(--surface-100);
}

.channel-info {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.channel-name {
    font-weight: 500;
    color: var(--text-color);
}

.channel-display-name {
    font-size: 0.875rem;
    color: var(--text-color-secondary);
}

.tvg-id {
    font-family: "Courier New", monospace;
    font-size: 0.875rem;
    background: var(--surface-100);
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    color: var(--text-color);
}

.no-group {
    color: var(--text-color-secondary);
    font-style: italic;
}

.filter-reason {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.filter-detail {
    font-size: 0.75rem;
    color: var(--text-color-secondary);
    line-height: 1.2;
    max-width: 180px;
    word-wrap: break-word;
}

.program-count {
    display: flex;
    justify-content: center;
}

.next-program {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.program-title {
    font-weight: 500;
    color: var(--text-color);
    font-size: 0.875rem;
}

.program-time {
    font-size: 0.75rem;
    color: var(--text-color-secondary);
}

.no-program {
    color: var(--text-color-secondary);
    font-style: italic;
    font-size: 0.875rem;
}

.action-buttons {
    display: flex;
    gap: 0.5rem;
}

.empty-state {
    text-align: center;
    padding: 3rem 1rem;
    color: var(--text-color-secondary);
}

.empty-state h3 {
    margin: 1rem 0 0.5rem 0;
    color: var(--text-color);
}

.empty-state p {
    margin: 0;
}

.loading-state {
    text-align: center;
    padding: 3rem 1rem;
    color: var(--text-color-secondary);
}

.loading-state p {
    margin-top: 1rem;
}

/* Skeleton loading styling */
.skeleton-table {
    opacity: 0.7;
}

.skeleton-table .channel-logo {
    background: var(--surface-200);
}

.skeleton-table .channel-info {
    gap: 0.25rem;
}

.skeleton-table .next-program {
    gap: 0.25rem;
}

.skeleton-table .action-buttons {
    gap: 0.5rem;
}

.skeleton-table .program-count {
    justify-content: center;
}

/* Responsive design */
@media (max-width: 768px) {
    .table-header {
        flex-direction: column;
        align-items: stretch;
    }

    .header-left {
        justify-content: space-between;
    }

    .filter-select,
    .search-input {
        min-width: auto;
        flex: 1;
    }

    .channel-name-cell {
        gap: 0.5rem;
    }

    .channel-logo {
        width: 24px;
        height: 24px;
    }

    .action-buttons {
        flex-direction: column;
        gap: 0.25rem;
    }
}
</style>
