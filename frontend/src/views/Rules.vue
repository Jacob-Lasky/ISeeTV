<template>
    <div class="rules-container">
        <!-- Header Section -->
        <div class="header-section">
            <div class="flex justify-between items-center mb-4">
                <div>
                    <h1 class="text-2xl font-bold mb-2">Ingestion Rules</h1>
                    <p class="text-gray-600">
                        Configure rules to filter data during ingestion. Rules
                        are applied after parsing but before database loading.
                    </p>
                </div>

                <!-- Rules Table -->
                <Card>
                    <template #content>
                        <DataTable
                            v-model:editingRows="editingRows"
                            :value="rules"
                            editMode="row"
                            dataKey="name"
                            :loading="loading"
                            stripedRows
                            responsiveLayout="scroll"
                            @row-edit-save="onRowEditSave"
                            @row-edit-cancel="onRowEditCancel"
                        >
                            <template #header>
                                <div class="flex justify-between items-center">
                                    <span class="text-lg font-semibold"
                                        >Rules Configuration</span
                                    >
                                    <div class="flex gap-2">
                                        <Button
                                            icon="pi pi-plus"
                                            label="Add Rule"
                                            severity="success"
                                            @click="addNewRule"
                                        />
                                        <Button
                                            icon="pi pi-play"
                                            label="Apply Rules"
                                            severity="primary"
                                            :loading="applyingRules"
                                            @click="applyRules"
                                        />
                                    </div>
                                </div>
                            </template>

                            <Column
                                field="name"
                                header="Rule Name"
                                style="min-width: 200px"
                            >
                                <template #body="{ data }">
                                    {{ data.name }}
                                </template>
                                <template #editor="{ data, field }">
                                    <InputText
                                        v-model="data[field]"
                                        placeholder="Enter rule name"
                                    />
                                </template>
                            </Column>

                            <Column
                                field="tables"
                                header="Table"
                                style="min-width: 150px"
                            >
                                <template #body="{ data }">
                                    <Tag
                                        :value="
                                            getTableDisplayName(data.tables[0])
                                        "
                                        :severity="
                                            getTableSeverity(data.tables[0])
                                        "
                                        class="text-xs"
                                    />
                                </template>
                                <template #editor="{ data, field }">
                                    <Select
                                        :model-value="data[field][0]"
                                        @update:model-value="
                                            (value) => {
                                                data[field] = [value]
                                                loadTableColumns(value)
                                            }
                                        "
                                        :options="tableOptions"
                                        optionLabel="label"
                                        optionValue="value"
                                        placeholder="Select table"
                                        class="w-full"
                                    />
                                </template>
                            </Column>

                            <Column
                                field="field"
                                header="Field"
                                style="min-width: 150px"
                            >
                                <template #body="{ data }">
                                    <code
                                        class="bg-gray-100 px-2 py-1 rounded text-sm"
                                        >{{ data.field }}</code
                                    >
                                </template>
                                <template #editor="{ data, field }">
                                    <Select
                                        v-model="data[field]"
                                        :options="
                                            getColumnOptions(data.tables[0])
                                        "
                                        optionLabel="label"
                                        optionValue="value"
                                        placeholder="Select field"
                                        :loading="loadingColumns"
                                        class="w-full"
                                        @focus="
                                            loadTableColumns(data.tables[0])
                                        "
                                    />
                                </template>
                            </Column>

                            <Column
                                field="not_"
                                header="Match"
                                :sortable="true"
                                style="width: 100px"
                            >
                                <template #body="{ data }">
                                    <Tag
                                        :value="data.not_ ? 'NOT' : 'Match'"
                                        :severity="
                                            data.not_ ? 'danger' : 'success'
                                        "
                                    />
                                </template>
                                <template #editor="{ data }">
                                    <Button
                                        :icon="
                                            data.not_
                                                ? 'pi pi-times'
                                                : 'pi pi-check'
                                        "
                                        :class="{
                                            'p-button-danger': data.not_,
                                            'p-button-success': !data.not_,
                                        }"
                                        size="small"
                                        @click="data.not_ = !data.not_"
                                        :title="
                                            data.not_
                                                ? 'Click to change to Match'
                                                : 'Click to change to NOT'
                                        "
                                    />
                                </template>
                            </Column>

                            <Column
                                field="regex"
                                header="Regex Pattern"
                                style="min-width: 200px"
                            >
                                <template #body="{ data }">
                                    <code
                                        class="bg-gray-100 px-2 py-1 rounded text-sm font-mono"
                                        >{{ data.regex }}</code
                                    >
                                </template>
                                <template #editor="{ data, field }">
                                    <InputText
                                        v-model="data[field]"
                                        placeholder="Regular expression"
                                    />
                                </template>
                            </Column>

                            <Column
                                field="enabled"
                                header="Status"
                                style="min-width: 100px"
                            >
                                <template #body="{ data }">
                                    <Tag
                                        :value="
                                            data.enabled
                                                ? 'Enabled'
                                                : 'Disabled'
                                        "
                                        :severity="
                                            data.enabled
                                                ? 'success'
                                                : 'secondary'
                                        "
                                    />
                                </template>
                                <template #editor="{ data, field }">
                                    <ToggleButton
                                        v-model="data[field]"
                                        onLabel="Enabled"
                                        offLabel="Disabled"
                                        onIcon="pi pi-check"
                                        offIcon="pi pi-times"
                                    />
                                </template>
                            </Column>

                            <Column
                                :rowEditor="true"
                                style="width: 10%; min-width: 8rem"
                                bodyStyle="text-align:center"
                            >
                                <template #roweditoriniticon>
                                    <i class="pi pi-pencil"></i>
                                </template>
                                <template #roweditorsaveicon>
                                    <i class="pi pi-check"></i>
                                </template>
                                <template #roweditorcancelicon>
                                    <i class="pi pi-times"></i>
                                </template>
                            </Column>

                            <Column
                                header="Actions"
                                style="width: 15%; min-width: 12rem"
                                bodyStyle="text-align:center"
                            >
                                <template #body="{ data }">
                                    <div class="flex gap-1 justify-center">
                                        <Button
                                            icon="pi pi-filter"
                                            severity="success"
                                            outlined
                                            size="small"
                                            v-tooltip="
                                                'Apply this rule to all assigned sources'
                                            "
                                            :loading="
                                                applyingRule === data.name
                                            "
                                            @click="applyRule(data.name)"
                                        />
                                        <Button
                                            icon="pi pi-filter-slash"
                                            severity="warn"
                                            outlined
                                            size="small"
                                            v-tooltip="
                                                'Unapply this rule from all assigned sources'
                                            "
                                            :loading="
                                                unapplyingRule === data.name
                                            "
                                            @click="unapplyRule(data.name)"
                                        />
                                        <Button
                                            icon="pi pi-trash"
                                            severity="danger"
                                            outlined
                                            size="small"
                                            v-tooltip="'Delete this rule'"
                                            @click="
                                                deleteRule(rules.indexOf(data))
                                            "
                                        />
                                    </div>
                                </template>
                            </Column>
                        </DataTable>
                    </template>
                </Card>

                <!-- Source Rule Assignments Section -->
                <Card class="mb-6">
                    <template #content>
                        <DataTable
                            v-model:editingRows="editingRows"
                            :value="sourceAssignments"
                            editMode="row"
                            dataKey="id"
                            :loading="loading"
                            stripedRows
                            responsiveLayout="scroll"
                            @row-edit-save="onAssignmentRowEditSave"
                            @row-edit-cancel="onAssignmentRowEditCancel"
                        >
                            <template #header>
                                <div class="flex justify-between items-center">
                                    <span class="text-lg font-semibold"
                                        >Source Rule Assignments</span
                                    >
                                    <div class="flex gap-2">
                                        <Button
                                            icon="pi pi-plus"
                                            label="Add Assignment"
                                            severity="success"
                                            @click="addNewAssignment"
                                        />
                                        <Button
                                            icon="pi pi-play"
                                            label="Apply Assignments"
                                            severity="primary"
                                            :loading="applyingAllAssignments"
                                            @click="applyAssignments"
                                        />
                                    </div>
                                </div>
                            </template>

                            <Column
                                field="source_name"
                                header="Source Name"
                                style="min-width: 200px"
                            >
                                <template #body="{ data }">
                                    {{ data.source_name }}
                                </template>
                                <template #editor="{ data, field }">
                                    <Select
                                        v-model="data[field]"
                                        :options="sourceOptions"
                                        optionLabel="label"
                                        optionValue="value"
                                        placeholder="Select source"
                                    />
                                </template>
                            </Column>

                            <Column
                                field="assignment_name"
                                header="Assignment Name"
                                style="min-width: 250px"
                            >
                                <template #body="{ data }">
                                    {{ data.assignment_name }}
                                </template>
                                <template #editor="{ data, field }">
                                    <InputText
                                        v-model="data[field]"
                                        placeholder="Enter assignment name"
                                    />
                                </template>
                            </Column>

                            <Column
                                field="assigned_rules"
                                header="Assigned Rules"
                                style="min-width: 300px"
                            >
                                <template #body="{ data }">
                                    <div
                                        v-if="
                                            data.assigned_rules &&
                                            data.assigned_rules.length > 0
                                        "
                                        class="flex flex-wrap gap-1"
                                    >
                                        <Tag
                                            v-for="rule in data.assigned_rules"
                                            :key="rule"
                                            :value="rule"
                                            severity="info"
                                            class="text-xs"
                                        />
                                    </div>
                                    <span v-else class="text-gray-400"
                                        >No rules assigned</span
                                    >
                                </template>
                                <template #editor="{ data, field }">
                                    <MultiSelect
                                        v-model="data[field]"
                                        display="chip"
                                        :options="ruleOptions"
                                        optionLabel="label"
                                        optionValue="value"
                                        placeholder="Select rules"
                                        filter=""
                                        multiple
                                        showClear
                                    />
                                </template>
                            </Column>

                            <Column
                                field="filter_stats"
                                header="Filtered by Rules"
                                style="min-width: 150px"
                            >
                                <template #body="{ data }">
                                    <div class="flex flex-column gap-1">
                                        <!-- Show progress bar when assignment is being applied -->
                                        <div
                                            v-if="applyingAssignments[data.id]"
                                            class="assignment-progress"
                                        >
                                            <div
                                                class="text-sm text-blue-600 font-medium mb-1"
                                            >
                                                Applying assignment...
                                            </div>
                                            <ProgressBar
                                                mode="indeterminate"
                                                style="height: 8px"
                                            />
                                        </div>

                                        <!-- Loading filter stats -->
                                        <div
                                            v-else-if="
                                                loadingFilterStats[
                                                    `${data.source_name}-${data.id}`
                                                ]
                                            "
                                            class="filter-stats-loading"
                                        >
                                            <div
                                                class="text-sm text-gray-600 font-medium mb-1"
                                            >
                                                Loading stats...
                                            </div>
                                            <ProgressBar
                                                mode="indeterminate"
                                                style="height: 6px"
                                            />
                                        </div>

                                        <!-- Show filter stats if available -->
                                        <div
                                            v-else-if="
                                                data.filter_stats &&
                                                data.filter_stats
                                                    .rule_filtered_count !==
                                                    null
                                            "
                                        >
                                            <div
                                                v-if="
                                                    data.filter_stats
                                                        .rule_filtered_count ===
                                                    0
                                                "
                                                class="text-green-600 font-semibold"
                                            >
                                                No records filtered
                                            </div>
                                            <div
                                                v-else
                                                class="text-blue-600 font-semibold"
                                            >
                                                {{
                                                    data.filter_stats
                                                        .rule_filtered_count
                                                }}
                                            </div>
                                        </div>

                                        <!-- Unknown state -->
                                        <div
                                            v-else
                                            class="text-gray-500 text-sm"
                                        >
                                            Unknown
                                        </div>
                                    </div>
                                </template>
                            </Column>

                            <Column
                                field="rule_mode"
                                header="Source Mode"
                                style="min-width: 120px"
                            >
                                <template #body="{ data }">
                                    <div class="flex items-center gap-2">
                                        <Tag
                                            :value="
                                                getSourceRuleMode(
                                                    data.source_name
                                                )
                                            "
                                            :severity="
                                                getSourceRuleMode(
                                                    data.source_name
                                                ) === 'whitelist'
                                                    ? 'success'
                                                    : 'danger'
                                            "
                                        />
                                        <i
                                            class="pi pi-lock text-gray-400 text-xs"
                                            v-tooltip="
                                                'Mode is inherited from source configuration and cannot be edited here'
                                            "
                                        ></i>
                                    </div>
                                </template>
                            </Column>

                            <Column
                                field="enabled"
                                header="Status"
                                style="min-width: 100px"
                            >
                                <template #body="{ data }">
                                    <Tag
                                        :value="
                                            data.enabled
                                                ? 'Enabled'
                                                : 'Disabled'
                                        "
                                        :severity="
                                            data.enabled
                                                ? 'success'
                                                : 'secondary'
                                        "
                                    />
                                </template>
                                <template #editor="{ data, field }">
                                    <ToggleButton
                                        v-model="data[field]"
                                        onLabel="Enabled"
                                        offLabel="Disabled"
                                        onIcon="pi pi-check"
                                        offIcon="pi pi-times"
                                    />
                                </template>
                            </Column>

                            <Column
                                :rowEditor="true"
                                style="width: 10%; min-width: 8rem"
                                bodyStyle="text-align:center"
                            >
                                <template #roweditoriniticon>
                                    <i class="pi pi-pencil"></i>
                                </template>
                                <template #roweditorsaveicon>
                                    <i class="pi pi-check"></i>
                                </template>
                                <template #roweditorcancelicon>
                                    <i class="pi pi-times"></i>
                                </template>
                            </Column>

                            <Column
                                header="Actions"
                                style="width: 25%; min-width: 20rem"
                                bodyStyle="text-align:center"
                            >
                                <template #body="{ data }">
                                    <div class="flex gap-1 justify-center">
                                        <Button
                                            icon="pi pi-play"
                                            severity="success"
                                            outlined
                                            size="small"
                                            v-tooltip="
                                                !data.enabled
                                                    ? 'Assignment is disabled - enable it first to apply'
                                                    : 'Apply this assignment'
                                            "
                                            @click="
                                                applyAssignmentToTables(data.id)
                                            "
                                            :loading="
                                                applyingAssignments[data.id]
                                            "
                                            :disabled="
                                                !data.enabled ||
                                                applyingSourceRules !== null ||
                                                unapplyingSourceRules !==
                                                    null ||
                                                applyingSourceRule !== null ||
                                                unapplyingSourceRule !== null ||
                                                applyingAssignments[data.id]
                                            "
                                        />

                                        <Button
                                            icon="pi pi-filter-slash"
                                            severity="warn"
                                            outlined
                                            size="small"
                                            v-tooltip="
                                                'Unapply this assignment'
                                            "
                                            :loading="
                                                unapplyingSourceRule ===
                                                `${data.source_name}-${data.id}`
                                            "
                                            :disabled="
                                                applyingSourceRules !== null ||
                                                unapplyingSourceRules !==
                                                    null ||
                                                applyingSourceRule !== null ||
                                                unapplyingSourceRule !== null
                                            "
                                            @click="
                                                unapplyAssignment(
                                                    data.id,
                                                    data.source_name
                                                )
                                            "
                                        />
                                        <Button
                                            icon="pi pi-trash"
                                            severity="danger"
                                            outlined
                                            size="small"
                                            v-tooltip="'Delete this assignment'"
                                            @click="
                                                deleteAssignment(
                                                    sourceAssignments.indexOf(
                                                        data
                                                    )
                                                )
                                            "
                                        />
                                    </div>
                                </template>
                            </Column>
                        </DataTable>
                    </template>
                </Card>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue"
import { useToast } from "primevue/usetoast"
import Button from "primevue/button"
import Card from "primevue/card"
import Checkbox from "primevue/checkbox"
import Column from "primevue/column"
import DataTable from "primevue/datatable"
import InputText from "primevue/inputtext"
import MultiSelect from "primevue/multiselect"
import ProgressBar from "primevue/progressbar"
import Select from "primevue/select"
import Tag from "primevue/tag"
import ToggleButton from "primevue/togglebutton"

const toast = useToast()

// Types
interface IngestionRule {
    name: string
    tables: string[]
    field: string
    regex: string
    enabled: boolean
    not_?: boolean // If true, inverts the regex match (NOT matching the pattern)
}

interface SourceRuleAssignment {
    id: string
    assignment_name: string
    source_name: string
    rule_mode: "whitelist" | "blacklist"
    assigned_rules: string[]
    enabled: boolean
    filter_stats?: {
        filter_stats: Record<string, number>
        passed: number
        all_not_passed: number
        total: number
        rule_filtered_count?: number
    }
    isNew?: boolean // Flag for new assignments
}

interface Source {
    name: string
    enabled: boolean
    rule_mode?: "whitelist" | "blacklist"
}

// Atomic function to normalize assigned_rules to always be an array
const normalizeAssignedRules = (assignment: any): any => {
    if (!assignment.assigned_rules) {
        return { ...assignment, assigned_rules: [] }
    }

    if (typeof assignment.assigned_rules === "string") {
        return { ...assignment, assigned_rules: [assignment.assigned_rules] }
    }

    if (Array.isArray(assignment.assigned_rules)) {
        return assignment
    }

    // Fallback for any other type
    return { ...assignment, assigned_rules: [] }
}

// Reactive state for rules and source assignments
const rules = ref<IngestionRule[]>([])
const sourceAssignments = ref<SourceRuleAssignment[]>([])
const sources = ref<Source[]>([])

const editingRows = ref([])
const loading = ref(false)
const hasChanges = ref(false)
const validating = ref(false)
const applyingRules = ref(false)
const applyingAllAssignments = ref(false)
const applyingRule = ref<string | null>(null)
const unapplyingRule = ref<string | null>(null)
const applyingSourceRules = ref<string | null>(null)
const unapplyingSourceRules = ref<string | null>(null)
const applyingSourceRule = ref<string | null>(null)
const unapplyingSourceRule = ref<string | null>(null)
const validationErrors = ref<string[]>([])

// Filter statistics state
const loadingFilterStats = ref<Record<string, boolean>>({})
const filterStats = ref<Record<string, any>>({})

// Assignment application progress tracking
const applyingAssignments = ref<Record<string, boolean>>({})

// Column options for field selection
const columnOptions = ref<Record<string, { label: string; value: string }[]>>(
    {}
)
const loadingColumns = ref(false)

const sourceOptions = computed(() =>
    sources.value.map((source) => ({
        label: source.name,
        value: source.name,
    }))
)

const ruleOptions = computed(() =>
    rules.value.map((rule) => ({
        label: rule.name,
        value: rule.name,
    }))
)

const tableOptions = computed(() => [
    { label: "M3U Channels", value: "m3u_channels" },
    { label: "EPG Channels", value: "epg_channels" },
    { label: "Programs", value: "programs" },
])

// Atomic function to get rule_mode from sources data
const getSourceRuleMode = (sourceName: string): string => {
    const source = sources.value.find((s) => s.name === sourceName)
    return source?.rule_mode || "blacklist" // Default to blacklist if not found
}

// Load configuration from API
let loadingConfiguration = false
const loadConfiguration = async (): Promise<void> => {
    // Prevent multiple simultaneous calls
    if (loadingConfiguration) {
        console.log("loadConfiguration already in progress, skipping")
        return
    }

    loadingConfiguration = true
    try {
        console.log(`Fetching /api/rules...`)
        const response = await fetch("/api/rules")
        console.log(
            `Response status: ${response.status} ${response.statusText}`
        )

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`)
        }

        const data = await response.json()
        console.log(`API response data:`, data)

        if (data.rules && data.source_assignments) {
            console.log(`loadConfiguration: Starting to update assignments`)
            console.log(
                `Current assignments count: ${sourceAssignments.value.length}`
            )
            console.log(
                `Current assignments with filter_stats: ${sourceAssignments.value.filter((a) => a.filter_stats).length}`
            )

            rules.value = data.rules

            // Preserve existing filter_stats when updating assignments
            const existingFilterStats = new Map()
            sourceAssignments.value.forEach((assignment) => {
                if (assignment.filter_stats) {
                    console.log(
                        `Preserving filter_stats for ${assignment.source_name}: ${assignment.filter_stats.rule_filtered_count}`
                    )
                    existingFilterStats.set(
                        assignment.source_name,
                        assignment.filter_stats
                    )
                }
            })

            console.log(
                `Preserved filter_stats for ${existingFilterStats.size} assignments`
            )

            // Update assignments and restore filter stats
            sourceAssignments.value = data.source_assignments.map(
                (assignment) => {
                    // First normalize assigned_rules to always be an array
                    const normalizedAssignment =
                        normalizeAssignedRules(assignment)

                    const existingStats = existingFilterStats.get(
                        normalizedAssignment.source_name
                    )
                    if (existingStats) {
                        console.log(
                            `Restoring filter_stats for ${normalizedAssignment.source_name}: ${existingStats.rule_filtered_count}`
                        )
                        return {
                            ...normalizedAssignment,
                            filter_stats: existingStats,
                        }
                    } else {
                        console.log(
                            `No existing filter_stats for ${normalizedAssignment.source_name}`
                        )
                        return normalizedAssignment
                    }
                }
            )

            console.log(
                `Updated assignments. Count with filter_stats: ${sourceAssignments.value.filter((a) => a.filter_stats).length}`
            )

            hasChanges.value = false
            validationErrors.value = []

            // Load filter statistics only for assignments that don't have them yet
            const assignmentsNeedingStats = sourceAssignments.value.filter(
                (a) => !a.filter_stats
            )
            console.log(
                `Found ${assignmentsNeedingStats.length} assignments needing filter stats`
            )

            if (assignmentsNeedingStats.length > 0) {
                await loadFilterStatsForAssignments(assignmentsNeedingStats)
            }

            console.log(
                `Filter stats loading completed. Final count with filter_stats: ${sourceAssignments.value.filter((a) => a.filter_stats).length}`
            )
        }
    } catch (error) {
        console.error("Error loading configuration:", error)
        console.error("Error details:", {
            message: error.message,
            stack: error.stack,
            name: error.name,
        })
        toast.add({
            severity: "error",
            summary: "Error",
            detail: "Failed to load rules configuration",
            life: 3000,
        })
    } finally {
        loadingConfiguration = false
    }
}

// Load sources from API
const loadSources = async (): Promise<void> => {
    try {
        const response = await fetch("/api/sources")
        const data = await response.json()
        sources.value = data || []
    } catch (error) {
        console.error("Error loading sources:", error)
    }
}

// Load column names for a specific table
const loadTableColumns = async (tableName: string): Promise<void> => {
    if (columnOptions.value[tableName]) {
        return // Already loaded
    }

    loadingColumns.value = true
    try {
        const response = await fetch(`/api/tables/${tableName}/columns`)
        const data = await response.json()

        if (data.success && data.data) {
            columnOptions.value[tableName] = data.data.map(
                (column: string) => ({
                    label: column,
                    value: column,
                })
            )
        }
    } catch (error) {
        console.error(`Error loading columns for table ${tableName}:`, error)
        toast.add({
            severity: "error",
            summary: "Error",
            detail: `Failed to load columns for ${tableName}`,
            life: 3000,
        })
    } finally {
        loadingColumns.value = false
    }
}

// Get column options for a specific table
const getColumnOptions = (
    tableName: string
): { label: string; value: string }[] => {
    return columnOptions.value[tableName] || []
}

// save functions for rules and assignments
const saveRules = async (): Promise<void> => {
    try {
        const response = await fetch("/api/rules/save", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(rules.value),
        })

        const data = await response.json()
        if (data.success) {
            toast.add({
                severity: "success",
                summary: "Success",
                detail: data.message || "Rules saved successfully",
                life: 3000,
            })
        } else {
            toast.add({
                severity: "error",
                summary: "Error",
                detail: data.errors?.[0] || "Failed to save rules",
                life: 5000,
            })
        }
    } catch (error) {
        console.error("Error saving rules:", error)
        toast.add({
            severity: "error",
            summary: "Error",
            detail: "Failed to save rules",
            life: 3000,
        })
    }
}

const saveAssignments = async (): Promise<void> => {
    try {
        const response = await fetch("/api/assignments/save", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(sourceAssignments.value),
        })

        const data = await response.json()
        if (data.success) {
            toast.add({
                severity: "success",
                summary: "Success",
                detail: data.message || "Assignments saved successfully",
                life: 3000,
            })
        } else {
            toast.add({
                severity: "error",
                summary: "Error",
                detail: data.errors?.[0] || "Failed to save assignments",
                life: 5000,
            })
        }
    } catch (error) {
        console.error("Error saving assignments:", error)
        toast.add({
            severity: "error",
            summary: "Error",
            detail: "Failed to save assignments",
            life: 3000,
        })
    }
}

// Rule management functions
const addNewRule = async (): Promise<void> => {
    const defaultTable = "m3u_channels"
    const newRule: IngestionRule = {
        name: `Rule ${rules.value.length + 1}`,
        tables: [defaultTable], // Still array for backend compatibility but will use single selection in UI
        field: "name",
        regex: ".*",
        not_: false, // Default to normal matching (not inverse)
        enabled: true,
    }

    // Load columns for the default table
    await loadTableColumns(defaultTable)

    rules.value.push(newRule)
    hasChanges.value = true

    // Save rules immediately using atomic save function
    await saveRules()
}

const deleteRule = async (index: number): Promise<void> => {
    const ruleName = rules.value[index].name
    rules.value.splice(index, 1)

    // Remove rule from all source assignments
    sourceAssignments.value.forEach((assignment) => {
        if (
            Array.isArray(assignment.assigned_rules) &&
            assignment.assigned_rules.includes(ruleName)
        ) {
            assignment.assigned_rules = assignment.assigned_rules.filter(
                (rule) => rule !== ruleName
            )
        }
    })

    hasChanges.value = true

    // Save rules immediately after deletion
    await saveRules()

    // Also save assignments since we modified assigned_rules
    await saveAssignments()
}

const onRuleEditSave = async (event: any): Promise<void> => {
    try {
        hasChanges.value = true

        // Save rules immediately when a rule is edited
        await saveRules()

        toast.add({
            severity: "success",
            summary: "Rule Updated",
            detail: "Rule has been saved successfully",
            life: 3000,
        })
    } catch (error) {
        console.error("Error saving rule:", error)
        toast.add({
            severity: "error",
            summary: "Save Failed",
            detail: "Failed to save rule changes",
            life: 3000,
        })
    }
}

const onRuleEditCancel = (): void => {
    // No changes needed for cancel
}

// Utility function to generate ID from assignment name
const generateIdFromName = (name: string): string => {
    return name
        .toLowerCase()
        .replace(/[^a-z0-9\s]/g, "") // Remove special characters
        .replace(/\s+/g, "_") // Replace spaces with underscores
        .replace(/_{2,}/g, "_") // Replace multiple underscores with single
        .replace(/^_|_$/g, "") // Remove leading/trailing underscores
}

// Function to ensure unique ID
const ensureUniqueId = (baseId: string): string => {
    let id = baseId
    let counter = 1

    while (sourceAssignments.value.some((assignment) => assignment.id === id)) {
        id = `${baseId}_${counter}`
        counter++
    }

    return id
}

// Function to update assignment ID when name changes
const updateAssignmentId = (assignment: any): void => {
    if (assignment.assignment_name && assignment.assignment_name.trim()) {
        const baseId = generateIdFromName(assignment.assignment_name.trim())
        assignment.id = ensureUniqueId(baseId)
    }
}

// Source assignment management functions
const addNewAssignment = (): void => {
    const newAssignment: SourceRuleAssignment = {
        id: "", // Will be generated when assignment_name is entered
        assignment_name: "",
        source_name: "",
        rule_mode: "blacklist", // Default to blacklist mode (start with all, filter out)
        assigned_rules: [],
        enabled: true,
        isNew: true, // Flag to indicate this is a new assignment
    }
    sourceAssignments.value.push(newAssignment)
    hasChanges.value = true

    // Put the new assignment in edit mode immediately
    editingRows.value = [newAssignment]

    // Don't save immediately - let user fill out required fields first
    // Saving will happen when user finishes editing via onAssignmentRowEditSave
}

const deleteAssignment = async (index: number): Promise<void> => {
    sourceAssignments.value.splice(index, 1)
    hasChanges.value = true

    // Save assignments immediately after deletion
    await saveAssignments()
}

const onAssignmentEditSave = async (event: any): Promise<void> => {
    try {
        const assignment = event.newData

        // Validate required fields
        if (!assignment.assignment_name || !assignment.assignment_name.trim()) {
            toast.add({
                severity: "error",
                summary: "Validation Error",
                detail: "Assignment name is required",
                life: 3000,
            })
            return
        }

        if (!assignment.source_name || !assignment.source_name.trim()) {
            toast.add({
                severity: "error",
                summary: "Validation Error",
                detail: "Source name is required",
                life: 3000,
            })
            return
        }

        // Generate ID if not present or empty, or if name changed
        if (!assignment.id || !assignment.id.trim()) {
            updateAssignmentId(assignment)
            console.log("Generated ID for assignment:", assignment.id)
        }

        // Ensure ID was generated successfully
        if (!assignment.id || !assignment.id.trim()) {
            toast.add({
                severity: "error",
                summary: "ID Generation Error",
                detail: "Failed to generate assignment ID",
                life: 3000,
            })
            return
        }

        // Use atomic normalization function to ensure assigned_rules is always an array
        assignment.assigned_rules =
            normalizeAssignedRules(assignment).assigned_rules
        console.log("Normalized assigned_rules:", assignment.assigned_rules)

        // Remove the isNew flag if present
        delete assignment.isNew

        // Save assignments immediately when an assignment is edited
        await saveAssignmentsOnly()

        toast.add({
            severity: "success",
            summary: "Assignment Updated",
            detail: "Assignment has been saved successfully",
            life: 3000,
        })
    } catch (error) {
        console.error("Error saving assignment:", error)
        toast.add({
            severity: "error",
            summary: "Save Failed",
            detail: "Failed to save assignment changes",
            life: 3000,
        })
    }
}

// Row editing functions
const onRowEditSave = async (event: any): Promise<void> => {
    try {
        console.log("onRowEditSave called with event:", event)
        console.log("Original data:", event.data)
        console.log("New data:", event.newData)

        // Update the rules array with the edited data
        const index = event.index
        if (index !== undefined && index >= 0 && index < rules.value.length) {
            rules.value[index] = { ...event.newData }
            console.log(
                "Updated rules array:",
                JSON.stringify(rules.value, null, 2)
            )
        }

        // Save rules immediately when a rule is edited
        await saveRules()

        toast.add({
            severity: "success",
            summary: "Rule Updated",
            detail: "Rule has been saved successfully",
            life: 3000,
        })
    } catch (error) {
        console.error("Error saving rule:", error)
        toast.add({
            severity: "error",
            summary: "Save Failed",
            detail: "Failed to save rule changes",
            life: 3000,
        })
    }
}

const onRowEditCancel = (): void => {
    // Reload configuration to revert changes
    loadConfiguration()
}

// Assignment row editing functions
const onAssignmentRowEditSave = async (event: any): Promise<void> => {
    try {
        console.log("onAssignmentRowEditSave called with event:", event)
        console.log("Original data:", event.data)
        console.log("New data:", event.newData)

        const assignment = { ...event.newData }

        // Validate required fields
        if (!assignment.assignment_name || !assignment.assignment_name.trim()) {
            toast.add({
                severity: "error",
                summary: "Validation Error",
                detail: "Assignment name is required",
                life: 3000,
            })
            return
        }

        if (!assignment.source_name || !assignment.source_name.trim()) {
            toast.add({
                severity: "error",
                summary: "Validation Error",
                detail: "Source name is required",
                life: 3000,
            })
            return
        }

        // Generate ID if not present or empty
        if (!assignment.id || !assignment.id.trim()) {
            updateAssignmentId(assignment)
            console.log("Generated ID for assignment:", assignment.id)
        }

        // Ensure ID was generated successfully
        if (!assignment.id || !assignment.id.trim()) {
            toast.add({
                severity: "error",
                summary: "ID Generation Error",
                detail: "Failed to generate assignment ID",
                life: 3000,
            })
            return
        }

        // Use atomic normalization function to ensure assigned_rules is always an array
        assignment.assigned_rules =
            normalizeAssignedRules(assignment).assigned_rules
        console.log("Normalized assigned_rules:", assignment.assigned_rules)

        // Remove the isNew flag if present
        delete assignment.isNew

        // Update the assignments array with the processed data
        const index = event.index
        if (
            index !== undefined &&
            index >= 0 &&
            index < sourceAssignments.value.length
        ) {
            sourceAssignments.value[index] = assignment
        }

        await saveAssignments()

        toast.add({
            severity: "success",
            summary: "Assignment Updated",
            detail: "Assignment has been saved successfully",
            life: 3000,
        })
    } catch (error) {
        console.error("Error saving assignment:", error)
        toast.add({
            severity: "error",
            summary: "Save Failed",
            detail: "Failed to save assignment changes",
            life: 3000,
        })
    }
}

const onAssignmentRowEditCancel = (): void => {
    // Reload configuration to revert changes
    loadConfiguration()
}

// Preload column data for existing rules
const preloadColumnData = async (): Promise<void> => {
    const uniqueTables = new Set<string>()
    rules.value.forEach((rule) => {
        if (rule.tables && rule.tables.length > 0) {
            uniqueTables.add(rule.tables[0])
        }
    })

    // Load columns for all unique tables
    await Promise.all(
        Array.from(uniqueTables).map((table) => loadTableColumns(table))
    )
}

// Apply rules to database records
const applyRules = async (): Promise<void> => {
    try {
        applyingRules.value = true

        // Apply rules to all tables
        const tables = ["m3u_channels", "epg_channels", "programs"]
        const results = []

        for (const table of tables) {
            console.log(`Applying rules to ${table}...`)

            const response = await fetch("/api/rules/apply", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    table_name: table,
                    // source_name is optional - omitting applies to all sources
                }),
            })

            const data = await response.json()

            if (!response.ok) {
                throw new Error(
                    data.detail || `Failed to apply rules to ${table}`
                )
            }

            results.push({
                table: table,
                ...data.results,
            })
        }

        // Calculate totals
        const totals = results.reduce(
            (acc, result) => ({
                processed: acc.processed + (result.processed || 0),
                filtered: acc.filtered + (result.filtered || 0),
                passed: acc.passed + (result.passed || 0),
            }),
            { processed: 0, filtered: 0, passed: 0 }
        )

        console.log("Rule application results:", results)
        console.log("Totals:", totals)

        toast.add({
            severity: "success",
            summary: "Rules Applied Successfully",
            detail: `Processed ${totals.processed} records: ${totals.passed} passed, ${totals.filtered} filtered`,
            life: 5000,
        })
    } catch (error) {
        console.error("Error applying rules:", error)
        toast.add({
            severity: "error",
            summary: "Rule Application Failed",
            detail:
                error instanceof Error
                    ? error.message
                    : "Failed to apply rules",
            life: 5000,
        })
    } finally {
        applyingRules.value = false
    }
}

// Apply assignments to database records
const applyAssignments = async (): Promise<void> => {
    try {
        applyingAllAssignments.value = true

        // Get all assignments to apply
        const assignments = sourceAssignments.value.filter(
            (assignment) => assignment.id
        )

        if (assignments.length === 0) {
            toast.add({
                severity: "warning",
                summary: "No Assignments Found",
                detail: "No assignments available to apply",
                life: 3000,
            })
            return
        }

        // Apply assignments to all tables
        const tables = ["m3u_channels", "epg_channels", "programs"]
        const results = []
        let totalProcessed = 0
        let totalFiltered = 0
        let totalPassed = 0

        for (const assignment of assignments) {
            console.log(
                `Applying assignment '${assignment.id}' (${assignment.source_name} -> ${assignment.assigned_rules})...`
            )

            for (const table of tables) {
                try {
                    const response = await fetch("/api/assignments/apply", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                        },
                        body: JSON.stringify({
                            assignment_id: assignment.id,
                            table_name: table,
                        }),
                    })

                    const data = await response.json()

                    if (!response.ok) {
                        throw new Error(
                            data.detail ||
                                `Failed to apply assignment '${assignment.id}' to ${table}`
                        )
                    }

                    // Accumulate results
                    if (data.results) {
                        totalProcessed += data.results.processed || 0
                        totalFiltered += data.results.filtered || 0
                        totalPassed += data.results.passed || 0
                    }

                    results.push({
                        assignment_id: assignment.id,
                        table: table,
                        source_name: assignment.source_name,
                        rule_name: assignment.assigned_rules,
                        ...data.results,
                    })
                } catch (error) {
                    console.error(
                        `Error applying assignment '${assignment.id}' to ${table}:`,
                        error
                    )
                    // Continue with other assignments/tables instead of failing completely
                }
            }
        }

        console.log("Assignment application results:", results)
        console.log("Totals:", {
            processed: totalProcessed,
            filtered: totalFiltered,
            passed: totalPassed,
        })

        toast.add({
            severity: "success",
            summary: "Assignments Applied Successfully",
            detail: `Applied ${assignments.length} assignments across ${tables.length} tables. Processed ${totalProcessed} records: ${totalPassed} passed, ${totalFiltered} filtered`,
            life: 5000,
        })

        // Refresh filter statistics after applying assignments
        await loadAllFilterStats()
    } catch (error) {
        console.error("Error applying assignments:", error)
        toast.add({
            severity: "error",
            summary: "Assignment Application Failed",
            detail:
                error instanceof Error
                    ? error.message
                    : "Failed to apply assignments",
            life: 5000,
        })
    } finally {
        applyingAllAssignments.value = false
    }
}

// Apply a single rule to all assigned sources
const applyRule = async (ruleName: string): Promise<void> => {
    try {
        applyingRule.value = ruleName

        // Get sources assigned to this rule
        const assignedSources = sourceAssignments.value
            .filter((assignment) => assignment.assigned_rules === ruleName)
            .map((assignment) => assignment.source_name)

        if (assignedSources.length === 0) {
            toast.add({
                severity: "warning",
                summary: "No Sources Assigned",
                detail: `Rule '${ruleName}' is not assigned to any sources`,
                life: 3000,
            })
            return
        }

        // Get the rule details to determine applicable tables
        const rule = rules.value.find((r) => r.name === ruleName)
        if (!rule) {
            throw new Error(`Rule '${ruleName}' not found`)
        }

        const tables = rule.tables || [
            "m3u_channels",
            "epg_channels",
            "programs",
        ]
        const results = []

        // Apply rule to each assigned source and applicable table
        for (const sourceName of assignedSources) {
            for (const tableName of tables) {
                console.log(
                    `Applying rule '${ruleName}' to ${tableName} for source ${sourceName}...`
                )

                const response = await fetch("/api/rules/apply/single", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        rule_name: ruleName,
                        table_name: tableName,
                        source_name: sourceName,
                    }),
                })

                const data = await response.json()

                if (!response.ok) {
                    throw new Error(
                        data.detail ||
                            `Failed to apply rule '${ruleName}' to ${tableName} for ${sourceName}`
                    )
                }

                results.push({
                    rule: ruleName,
                    table: tableName,
                    source: sourceName,
                    ...data.results,
                })
            }
        }

        // Calculate totals
        const totals = results.reduce(
            (acc, result) => ({
                processed: acc.processed + (result.processed || 0),
                filtered: acc.filtered + (result.filtered || 0),
                passed: acc.passed + (result.passed || 0),
            }),
            { processed: 0, filtered: 0, passed: 0 }
        )

        console.log(`Rule '${ruleName}' application results:`, results)
        console.log("Totals:", totals)

        toast.add({
            severity: "success",
            summary: "Rule Applied Successfully",
            detail: `Rule '${ruleName}' applied to ${assignedSources.length} sources: ${totals.passed} passed, ${totals.filtered} filtered`,
            life: 5000,
        })
    } catch (error) {
        console.error(`Error applying rule '${ruleName}':`, error)
        toast.add({
            severity: "error",
            summary: "Rule Application Failed",
            detail:
                error instanceof Error
                    ? error.message
                    : `Failed to apply rule '${ruleName}'`,
            life: 5000,
        })
    } finally {
        applyingRule.value = null
    }
}

// Unapply a single rule from all assigned sources
const unapplyRule = async (ruleName: string): Promise<void> => {
    try {
        unapplyingRule.value = ruleName

        // Get sources assigned to this rule
        const assignedSources = sourceAssignments.value
            .filter((assignment) => assignment.assigned_rules === ruleName)
            .map((assignment) => assignment.source_name)

        if (assignedSources.length === 0) {
            toast.add({
                severity: "warning",
                summary: "No Sources Assigned",
                detail: `Rule '${ruleName}' is not assigned to any sources`,
                life: 3000,
            })
            return
        }

        // Get the rule details to determine applicable tables
        const rule = rules.value.find((r) => r.name === ruleName)
        if (!rule) {
            throw new Error(`Rule '${ruleName}' not found`)
        }

        const tables = rule.tables || [
            "m3u_channels",
            "epg_channels",
            "programs",
        ]
        const results = []

        // Unapply rule from each assigned source and applicable table
        for (const sourceName of assignedSources) {
            for (const tableName of tables) {
                console.log(
                    `Unapplying rule '${ruleName}' from ${tableName} for source ${sourceName}...`
                )

                const response = await fetch("/api/rules/unapply", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        table_name: tableName,
                        source_name: sourceName,
                        rule_names: [ruleName],
                    }),
                })

                const data = await response.json()

                if (!response.ok) {
                    throw new Error(
                        data.detail ||
                            `Failed to unapply rule '${ruleName}' from ${tableName} for ${sourceName}`
                    )
                }

                results.push({
                    rule: ruleName,
                    table: tableName,
                    source: sourceName,
                    ...data.results,
                })
            }
        }

        // Calculate totals
        const totalRecords = results.reduce(
            (acc, result) => acc + (result.processed || 0),
            0
        )

        console.log(`Rule '${ruleName}' unapplication results:`, results)

        toast.add({
            severity: "success",
            summary: "Rule Unapplied Successfully",
            detail: `Rule '${ruleName}' unapplied from ${assignedSources.length} sources (${totalRecords} records restored)`,
            life: 5000,
        })
    } catch (error) {
        console.error(`Error unapplying rule '${ruleName}':`, error)
        toast.add({
            severity: "error",
            summary: "Rule Unapplication Failed",
            detail:
                error instanceof Error
                    ? error.message
                    : `Failed to unapply rule '${ruleName}'`,
            life: 5000,
        })
    } finally {
        unapplyingRule.value = null
    }
}

// Apply all assigned rules to a specific source
const applySourceRules = async (sourceName: string): Promise<void> => {
    try {
        applyingSourceRules.value = sourceName

        console.log(`Applying all rules to source ${sourceName}...`)

        const response = await fetch("/api/rules/apply/source", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                source_name: sourceName,
                // table_names is optional - will apply to all tables by default
            }),
        })

        const data = await response.json()

        if (!response.ok) {
            throw new Error(
                data.detail || `Failed to apply rules to source ${sourceName}`
            )
        }

        console.log(
            `Source rules application results for ${sourceName}:`,
            data.results
        )

        // Calculate totals from the results
        const totals = data.results.tables
            ? Object.values(data.results.tables).reduce(
                  (acc: any, result: any) => ({
                      processed: acc.processed + (result.processed || 0),
                      filtered: acc.filtered + (result.filtered || 0),
                      passed: acc.passed + (result.passed || 0),
                  }),
                  { processed: 0, filtered: 0, passed: 0 }
              )
            : data.results

        toast.add({
            severity: "success",
            summary: "Source Rules Applied",
            detail: `All rules applied to source '${sourceName}': ${totals.passed} passed, ${totals.filtered} filtered`,
            life: 5000,
        })
    } catch (error) {
        console.error(`Error applying rules to source '${sourceName}':`, error)
        toast.add({
            severity: "error",
            summary: "Source Rule Application Failed",
            detail:
                error instanceof Error
                    ? error.message
                    : `Failed to apply rules to source '${sourceName}'`,
            life: 5000,
        })
    } finally {
        applyingSourceRules.value = null
    }
}

// Unapply all rules from a specific source
const unapplySourceRules = async (sourceName: string): Promise<void> => {
    try {
        unapplyingSourceRules.value = sourceName

        const tables = ["m3u_channels", "epg_channels", "programs"]
        const results = []

        // Unapply rules from each table for this source
        for (const tableName of tables) {
            console.log(
                `Unapplying all rules from ${tableName} for source ${sourceName}...`
            )

            const response = await fetch("/api/rules/unapply", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    table_name: tableName,
                    source_name: sourceName,
                    // rule_names is optional - omitting unapplies all rules
                }),
            })

            const data = await response.json()

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                        `Failed to unapply rules from ${tableName} for ${sourceName}`
                )
            }

            results.push({
                table: tableName,
                source: sourceName,
                ...data.results,
            })
        }

        // Calculate totals
        const totalRecords = results.reduce(
            (acc, result) => acc + (result.processed || 0),
            0
        )

        console.log(
            `Source rules unapplication results for ${sourceName}:`,
            results
        )

        toast.add({
            severity: "success",
            summary: "Source Rules Unapplied",
            detail: `All rules unapplied from source '${sourceName}' (${totalRecords} records restored)`,
            life: 5000,
        })
    } catch (error) {
        console.error(
            `Error unapplying rules from source '${sourceName}':`,
            error
        )
        toast.add({
            severity: "error",
            summary: "Source Rule Unapplication Failed",
            detail:
                error instanceof Error
                    ? error.message
                    : `Failed to unapply rules from source '${sourceName}'`,
            life: 5000,
        })
    } finally {
        unapplyingSourceRules.value = null
    }
}

// Apply an assignment to all relevant tables based on its rules
const applyAssignmentToTables = async (assignmentId: string): Promise<void> => {
    try {
        // Set loading state
        applyingAssignments.value[assignmentId] = true

        // Find the assignment
        const assignment = sourceAssignments.value.find(
            (a) => a.id === assignmentId
        )
        if (!assignment) {
            console.error(`Assignment '${assignmentId}' not found`)
            toast.add({
                severity: "error",
                summary: "Assignment Not Found",
                detail: `Assignment '${assignmentId}' not found`,
                life: 3000,
            })
            return
        }

        console.log(
            `Applying assignment '${assignmentId}' to all relevant tables...`
        )

        // Determine which tables to apply to based on the rules in the assignment
        const tablesToApply = new Set<string>()
        for (const ruleName of assignment.assigned_rules) {
            const rule = rules.value.find((r) => r.name === ruleName)
            if (rule && rule.tables) {
                rule.tables.forEach((table) => tablesToApply.add(table))
            }
        }

        if (tablesToApply.size === 0) {
            console.warn(`No tables found for assignment '${assignmentId}'`)
            return
        }

        console.log(
            `Will apply assignment '${assignmentId}' to tables: ${Array.from(tablesToApply).join(", ")}`
        )

        // Apply the assignment to each relevant table
        const applyPromises = Array.from(tablesToApply).map((tableName) =>
            applyAssignment(assignmentId, tableName)
        )

        await Promise.all(applyPromises)

        // Refresh filter statistics after successful application
        console.log(
            `Refreshing filter statistics for assignment '${assignmentId}'...`
        )
        await fetchFilterStatsForAssignment(
            assignmentId,
            assignment.source_name
        )

        toast.add({
            severity: "success",
            summary: "Assignment Applied",
            detail: `Assignment '${assignment.assignment_name}' applied to ${tablesToApply.size} table(s)`,
            life: 5000,
        })
    } catch (error) {
        console.error(`Error applying assignment '${assignmentId}':`, error)
        toast.add({
            severity: "error",
            summary: "Assignment Application Failed",
            detail:
                error instanceof Error
                    ? error.message
                    : `Failed to apply assignment '${assignmentId}'`,
            life: 5000,
        })
    } finally {
        // Clear loading state
        applyingAssignments.value[assignmentId] = false
    }
}

// Apply a specific assignment by ID (new multi-assignment architecture)
const applyAssignment = async (
    assignmentId: string,
    tableName: string
): Promise<void> => {
    try {
        const assignmentKey = `${assignmentId}-${tableName}`
        applyingSourceRule.value = assignmentKey

        console.log(
            `Applying assignment '${assignmentId}' to table '${tableName}'...`
        )

        const response = await fetch("/api/assignments/apply", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                assignment_id: assignmentId,
                table_name: tableName,
            }),
        })

        const data = await response.json()

        if (!response.ok) {
            throw new Error(
                data.detail ||
                    `Failed to apply assignment '${assignmentId}' to table '${tableName}'`
            )
        }

        console.log(
            `Assignment application results for '${assignmentId}' on '${tableName}':`,
            data.results
        )

        const totals =
            data.results && typeof data.results === "object"
                ? {
                      passed: data.results.passed || 0,
                      filtered: data.results.filtered || 0,
                  }
                : data.results

        toast.add({
            severity: "success",
            summary: "Assignment Applied",
            detail: `Assignment '${assignmentId}' applied to table '${tableName}': ${totals.passed} passed, ${totals.filtered} filtered`,
            life: 5000,
        })

        // Refresh filter statistics for all rules in this assignment
        const assignment = sourceAssignments.value.find(
            (a) => a.assignment_id === assignmentId
        )
        if (assignment) {
            console.log(
                `Refreshing filter stats for assignment: ${assignmentId}`
            )
            for (const ruleName of assignment.assigned_rules) {
                await fetchFilterStatsForRule(assignment.source_name, ruleName)
            }
        }
    } catch (error) {
        console.error(
            `Error applying assignment '${assignmentId}' to table '${tableName}':`,
            error
        )
        toast.add({
            severity: "error",
            summary: "Assignment Application Failed",
            detail:
                error instanceof Error
                    ? error.message
                    : `Failed to apply assignment '${assignmentId}' to table '${tableName}'`,
            life: 5000,
        })
    } finally {
        applyingSourceRule.value = null
    }
}

// Apply a specific rule to a specific source (legacy method)
const applySourceRule = async (
    sourceName: string,
    ruleName: string
): Promise<void> => {
    try {
        const ruleKey = `${sourceName}-${ruleName}`
        applyingSourceRule.value = ruleKey

        console.log(`Applying rule '${ruleName}' to source '${sourceName}'...`)

        // Find the rule configuration to get the table name
        const rule = rules.value.find((r) => r.name === ruleName)
        if (!rule || !rule.tables || rule.tables.length === 0) {
            throw new Error(
                `Rule '${ruleName}' not found or has no tables configured`
            )
        }

        // Use the first table from the rule configuration
        const tableName = rule.tables[0]
        console.log(
            `Applying rule '${ruleName}' to table '${tableName}' for source '${sourceName}'...`
        )

        const response = await fetch("/api/rules/apply/single", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                rule_name: ruleName,
                table_name: tableName,
                source_name: sourceName,
            }),
        })

        const data = await response.json()

        if (!response.ok) {
            throw new Error(
                data.detail ||
                    `Failed to apply rule '${ruleName}' to source '${sourceName}'`
            )
        }

        console.log(
            `Single rule application results for '${ruleName}' on '${sourceName}':`,
            data.results
        )

        // Calculate totals from the results
        const totals = data.results.tables
            ? Object.values(data.results.tables).reduce(
                  (acc: any, result: any) => ({
                      processed: acc.processed + (result.processed || 0),
                      filtered: acc.filtered + (result.filtered || 0),
                      passed: acc.passed + (result.passed || 0),
                  }),
                  { processed: 0, filtered: 0, passed: 0 }
              )
            : data.results

        toast.add({
            severity: "success",
            summary: "Rule Applied",
            detail: `Rule '${ruleName}' applied to source '${sourceName}': ${totals.passed} passed, ${totals.filtered} filtered`,
            life: 5000,
        })
    } catch (error) {
        console.error(
            `Error applying rule '${ruleName}' to source '${sourceName}':`,
            error
        )
        toast.add({
            severity: "error",
            summary: "Rule Application Failed",
            detail:
                error instanceof Error
                    ? error.message
                    : `Failed to apply rule '${ruleName}' to source '${sourceName}'`,
            life: 5000,
        })
    } finally {
        applyingSourceRule.value = null
    }
}

// Unapply a specific rule from a specific source (most granular control)
const unapplySourceRule = async (
    sourceName: string,
    ruleName: string
): Promise<void> => {
    try {
        const ruleKey = `${sourceName}-${ruleName}`
        unapplyingSourceRule.value = ruleKey

        const tables = ["m3u_channels", "epg_channels", "programs"]
        const results = []

        // Unapply the specific rule from each table for this source
        for (const tableName of tables) {
            console.log(
                `Unapplying rule '${ruleName}' from ${tableName} for source '${sourceName}'...`
            )

            const response = await fetch("/api/rules/unapply", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    table_name: tableName,
                    source_name: sourceName,
                    rule_names: [ruleName], // Specify the single rule to unapply
                }),
            })

            const data = await response.json()

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                        `Failed to unapply rule '${ruleName}' from ${tableName} for '${sourceName}'`
                )
            }

            results.push({
                table: tableName,
                source: sourceName,
                rule: ruleName,
                ...data.results,
            })
        }

        // Calculate totals
        const totalRecords = results.reduce(
            (acc, result) => acc + (result.processed || 0),
            0
        )

        console.log(
            `Single rule unapplication results for '${ruleName}' on '${sourceName}':`,
            results
        )

        toast.add({
            severity: "success",
            summary: "Rule Unapplied",
            detail: `Rule '${ruleName}' unapplied from source '${sourceName}' (${totalRecords} records restored)`,
            life: 5000,
        })
    } catch (error) {
        console.error(
            `Error unapplying rule '${ruleName}' from source '${sourceName}':`,
            error
        )
        toast.add({
            severity: "error",
            summary: "Rule Unapplication Failed",
            detail:
                error instanceof Error
                    ? error.message
                    : `Failed to unapply rule '${ruleName}' from source '${sourceName}'`,
            life: 5000,
        })
    } finally {
        unapplyingSourceRule.value = null
    }
}

// Unapply a specific assignment from relevant tables (atomic assignment control)
const unapplyAssignment = async (
    assignmentId: string,
    sourceName: string
): Promise<void> => {
    try {
        const assignmentKey = `${sourceName}-${assignmentId}`
        unapplyingSourceRule.value = assignmentKey

        console.log(
            `Unapplying assignment '${assignmentId}' from relevant tables...`
        )

        const response = await fetch("/api/assignments/unapply", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                assignment_id: assignmentId,
                // No table_name provided - backend will determine relevant tables
            }),
        })

        const data = await response.json()

        if (!response.ok) {
            throw new Error(
                data.detail || `Failed to unapply assignment '${assignmentId}'`
            )
        }

        console.log(`Assignment unapplication results for '${assignmentId}':`, {
            relevant_tables: data.relevant_tables,
            processed_tables: data.processed_tables,
            results: data.results,
            table_results: data.table_results,
        })

        toast.add({
            severity: "success",
            summary: "Assignment Unapplied",
            detail: `Assignment '${assignmentId}' unapplied from ${data.processed_tables?.length || 0} relevant tables (${data.results?.restored || 0} records restored)`,
            life: 5000,
        })

        // Refresh filter statistics after unapplying
        await loadAllFilterStats()
    } catch (error) {
        console.error(`Error unapplying assignment '${assignmentId}':`, error)
        toast.add({
            severity: "error",
            summary: "Assignment Unapplication Failed",
            detail:
                error instanceof Error
                    ? error.message
                    : `Failed to unapply assignment '${assignmentId}'`,
            life: 5000,
        })
    } finally {
        unapplyingSourceRule.value = null
    }
}

// Lifecycle hooks
onMounted(async () => {
    await Promise.all([loadConfiguration(), loadSources()])
    // Preload column data after configuration is loaded
    await preloadColumnData()
})

const getTableDisplayName = (table: string): string => {
    const tableMap: Record<string, string> = {
        m3u_channels: "M3U Channels",
        epg_channels: "EPG Channels",
        programs: "Programs",
    }
    return tableMap[table] || table
}

const getTableSeverity = (table: string): string => {
    const severityMap: Record<string, string> = {
        m3u_channels: "success",
        epg_channels: "info",
        programs: "warning",
    }
    return severityMap[table] || "secondary"
}

// Fetch filter statistics for a specific assignment
const fetchFilterStatsForAssignment = async (
    assignmentId: string,
    sourceName: string
): Promise<void> => {
    if (!assignmentId || !sourceName) return

    try {
        const key = `${sourceName}-${assignmentId}`
        loadingFilterStats.value[key] = true

        // Find the assignment to get the correct tables
        const assignment = sourceAssignments.value.find(
            (a) => a.id === assignmentId && a.source_name === sourceName
        )
        if (!assignment) {
            console.error(
                `Assignment '${assignmentId}' not found for source '${sourceName}'`
            )
            return
        }

        // Get the first rule to determine the table
        const firstRuleName = Array.isArray(assignment.assigned_rules)
            ? assignment.assigned_rules[0]
            : assignment.assigned_rules
        const rule = rules.value.find((r) => r.name === firstRuleName)
        if (!rule || !rule.tables || rule.tables.length === 0) {
            console.error(
                `Rule '${firstRuleName}' not found or has no tables configured`
            )
            return
        }

        // Use the first table configured for this rule
        const tableName = rule.tables[0]
        console.log(
            `Fetching filter stats for assignment '${assignmentId}' from table '${tableName}'`
        )

        // Fetch filter stats using the assignment ID (not individual rule names)
        const response = await fetch(
            `/api/tables/${tableName}/filtered_counts/${sourceName}/${assignmentId}`
        )
        const data = await response.json()

        if (data.success) {
            console.log(
                `API SUCCESS for ${sourceName}-${assignmentId}: filtered_count=${data.data.filtered_count}`
            )
            filterStats.value[key] = data.data

            // Update the assignment with filter stats
            const newFilterStats = {
                filter_stats: { [assignmentId]: data.data.filtered_count },
                passed: data.data.passed,
                all_not_passed: data.data.all_not_passed,
                total: data.data.total,
                rule_filtered_count: data.data.filtered_count,
                has_been_run: data.data.has_been_run,
            }
            console.log(
                `Setting filter_stats for ${sourceName}-${assignmentId}: rule_filtered_count=${newFilterStats.rule_filtered_count}, has_been_run=${newFilterStats.has_been_run}`
            )
            assignment.filter_stats = newFilterStats
            console.log(
                `Assignment updated. Current filter_stats.rule_filtered_count: ${assignment.filter_stats.rule_filtered_count}`
            )
        } else {
            console.log(
                `API FAILED for ${sourceName}-${assignmentId}: ${JSON.stringify(data)}`
            )
        }
    } catch (error) {
        console.error(
            `Error fetching filter stats for ${sourceName} with assignment ${assignmentId}:`,
            error
        )
    } finally {
        const key = `${sourceName}-${assignmentId}`
        loadingFilterStats.value[key] = false
    }
}

// Load filter statistics for specific assignments
const loadFilterStatsForAssignments = async (
    assignments: any[]
): Promise<void> => {
    console.log(
        `loadFilterStatsForAssignments: Starting with ${assignments.length} assignments`
    )

    const validAssignments = assignments.filter(
        (assignment) =>
            assignment.id && assignment.source_name && assignment.assigned_rules
    )

    console.log(
        `Found ${validAssignments.length} valid assignments to load stats for`
    )

    const promises = validAssignments.map((assignment) => {
        console.log(
            `Will fetch stats for assignment: ${assignment.id} (${assignment.source_name})`
        )
        return fetchFilterStatsForAssignment(
            assignment.id,
            assignment.source_name
        )
    })

    console.log(`Starting ${promises.length} parallel API calls...`)
    await Promise.all(promises)
    console.log(
        `All API calls completed. Assignments with filter_stats: ${sourceAssignments.value.filter((a) => a.filter_stats).length}`
    )
}

// Load filter statistics for all assignments
const loadAllFilterStats = async (): Promise<void> => {
    console.log(
        `loadAllFilterStats: Starting with ${sourceAssignments.value.length} assignments`
    )
    await loadFilterStatsForAssignments(sourceAssignments.value)
}

// Check if a specific assignment is currently being applied
const isAssignmentBeingApplied = (
    sourceName: string,
    assignmentId: string
): boolean => {
    const assignmentKey = `${sourceName}-${assignmentId}`
    return applyingSourceRule.value === assignmentKey
}

// Clean up - functions already defined above
</script>

<style scoped>
.rules-container {
    padding: 1rem;
    max-width: 1400px;
    margin: 0 auto;
}

.header-section {
    margin-bottom: 2rem;
}

.status-card {
    border: 1px solid #e5e7eb;
    border-radius: 8px;
}

.status-card :deep(.p-card-content) {
    padding: 1rem;
}

.log-content {
    border-top: 1px solid #e5e7eb;
    padding-top: 1rem;
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .rules-container {
        padding: 0.5rem;
    }

    .header-section .flex {
        flex-direction: column;
        gap: 1rem;
    }

    .grid {
        grid-template-columns: 1fr;
    }
}
</style>
