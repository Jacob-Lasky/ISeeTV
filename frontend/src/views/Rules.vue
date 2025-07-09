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
                                            icon="pi pi-file"
                                            label="View Logs"
                                            severity="secondary"
                                            outlined
                                            @click="viewLogs"
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
                                style="width: 5%; min-width: 4rem"
                                bodyStyle="text-align:center"
                            >
                                <template #body="{ data }">
                                    <Button
                                        icon="pi pi-trash"
                                        severity="danger"
                                        outlined
                                        size="small"
                                        @click="deleteRule(rules.indexOf(data))"
                                    />
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
                            dataKey="source_name"
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
                                field="rule_mode"
                                header="Mode"
                                style="min-width: 120px"
                            >
                                <template #body="{ data }">
                                    <Tag
                                        :value="data.rule_mode"
                                        :severity="
                                            data.rule_mode === 'whitelist'
                                                ? 'success'
                                                : 'danger'
                                        "
                                    />
                                </template>
                                <template #editor="{ data, field }">
                                    <Select
                                        v-model="data[field]"
                                        :options="[
                                            {
                                                label: 'Whitelist',
                                                value: 'whitelist',
                                            },
                                            {
                                                label: 'Blacklist',
                                                value: 'blacklist',
                                            },
                                        ]"
                                        optionLabel="label"
                                        optionValue="value"
                                        placeholder="Select mode"
                                    />
                                </template>
                            </Column>

                            <Column
                                field="assigned_rules"
                                header="Assigned Rules"
                                style="min-width: 300px"
                            >
                                <template #body="{ data }">
                                    <div class="flex flex-wrap gap-1">
                                        <Tag
                                            v-for="ruleName in data.assigned_rules"
                                            :key="ruleName"
                                            :value="ruleName"
                                            severity="info"
                                        />
                                    </div>
                                </template>
                                <template #editor="{ data, field }">
                                    <MultiSelect
                                        v-model="data[field]"
                                        :options="ruleOptions"
                                        optionLabel="label"
                                        optionValue="value"
                                        placeholder="Select rules"
                                        :maxSelectedLabels="3"
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
                                style="width: 5%; min-width: 4rem"
                                bodyStyle="text-align:center"
                            >
                                <template #body="{ data }">
                                    <Button
                                        icon="pi pi-trash"
                                        severity="danger"
                                        outlined
                                        size="small"
                                        @click="
                                            deleteAssignment(
                                                sourceAssignments.indexOf(data)
                                            )
                                        "
                                    />
                                </template>
                            </Column>
                        </DataTable>
                    </template>
                </Card>
                <div v-if="selectedLogContent" class="log-content">
                    <h3 class="text-lg font-semibold mb-2">
                        {{ selectedLogFile?.filename }}
                    </h3>
                    <DataTable
                        :value="selectedLogContent"
                        :paginator="true"
                        :rows="10"
                        responsiveLayout="scroll"
                    >
                        <Column field="reason" header="Rejection Reason" />
                        <Column field="rejected_by" header="Rule" />
                        <Column field="table_name" header="Table" />
                        <Column field="source_name" header="Source" />
                        <Column field="rejected_at" header="Rejected At">
                            <template #body="{ data }">
                                {{ formatDate(data.rejected_at) }}
                            </template>
                        </Column>
                    </DataTable>
                </div>
            </div>
        </div>
    </div>

    <!-- Logs Dialog -->
    <Dialog
        v-model:visible="showLogsDialog"
        modal
        header="Ingestion Rules Logs"
        :style="{ width: '80vw' }"
        :maximizable="true"
    >
        <div class="logs-content">
            <div class="mb-4">
                <h4 class="text-lg font-semibold mb-2">Available Log Files</h4>
                <div class="flex flex-wrap gap-2">
                    <Button
                        v-for="logFile in logFiles"
                        :key="logFile"
                        :label="logFile"
                        severity="secondary"
                        outlined
                        size="small"
                        @click="viewLogFile(logFile)"
                    />
                </div>
            </div>

            <div v-if="selectedLogContent" class="mt-4">
                <h4 class="text-lg font-semibold mb-2">
                    {{ selectedLogFile }}
                </h4>
                <pre
                    class="bg-gray-100 p-4 rounded text-sm overflow-auto max-h-96"
                    >{{ selectedLogContent }}</pre
                >
            </div>
        </div>
    </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import { useToast } from "primevue/usetoast"
import Button from "primevue/button"
import Card from "primevue/card"
import Column from "primevue/column"
import DataTable from "primevue/datatable"
import Dialog from "primevue/dialog"
import InputText from "primevue/inputtext"
import Message from "primevue/message"
import MultiSelect from "primevue/multiselect"
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
}

interface SourceRuleAssignment {
    source_name: string
    rule_mode: "whitelist" | "blacklist"
    assigned_rules: string[]
    enabled: boolean
}

interface Source {
    name: string
    enabled: boolean
    rule_mode?: "whitelist" | "blacklist"
}

// Reactive state for rules and source assignments
const rules = ref<IngestionRule[]>([])
const sourceAssignments = ref<SourceRuleAssignment[]>([])
const sources = ref<Source[]>([])
const editingRows = ref([])
const loading = ref(false)
const hasChanges = ref(false)
const validating = ref(false)
const validationErrors = ref<string[]>([])
const showLogsDialog = ref(false)
const logFiles = ref<string[]>([])
const selectedLogFile = ref<string | null>(null)
const selectedLogContent = ref<string | null>(null)
const loadingLogs = ref(false)

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

// Load configuration from API
const loadConfiguration = async (): Promise<void> => {
    try {
        const response = await fetch("/api/rules")
        const data = await response.json()

        if (data.rules && data.source_assignments) {
            rules.value = data.rules
            sourceAssignments.value = data.source_assignments
            hasChanges.value = false
            validationErrors.value = []
        }
    } catch (error) {
        console.error("Error loading configuration:", error)
        toast.add({
            severity: "error",
            summary: "Error",
            detail: "Failed to load rules configuration",
            life: 3000,
        })
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
        console.log(
            "saveRules called with data:",
            JSON.stringify(rules.value, null, 2)
        )

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
        assignment.assigned_rules = assignment.assigned_rules.filter(
            (name) => name !== ruleName
        )
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

// Source assignment management functions
const addNewAssignment = (): void => {
    const newAssignment: SourceRuleAssignment = {
        source_name: "",
        rule_mode: "blacklist",
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
        // Save assignments immediately when an assignment is edited
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

// Log management functions
const loadLogFiles = async (): Promise<void> => {
    loadingLogs.value = true
    try {
        const response = await fetch("/api/rules/logs")
        const data = await response.json()

        if (data.success) {
            logFiles.value = data.data || []
        }
    } catch (error) {
        console.error("Error loading log files:", error)
        toast.add({
            severity: "error",
            summary: "Error",
            detail: "Failed to load log files",
            life: 3000,
        })
    } finally {
        loadingLogs.value = false
    }
}

const viewLogFile = async (filename: string): Promise<void> => {
    try {
        const response = await fetch(`/api/rules/logs/${filename}`)
        const data = await response.json()

        if (data.success) {
            selectedLogFile.value = filename
            selectedLogContent.value = JSON.stringify(data.data, null, 2)
        }
    } catch (error) {
        console.error("Error loading log file:", error)
        toast.add({
            severity: "error",
            summary: "Error",
            detail: "Failed to load log file",
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

        // Update the assignments array with the edited data
        const index = event.index
        if (
            index !== undefined &&
            index >= 0 &&
            index < sourceAssignments.value.length
        ) {
            sourceAssignments.value[index] = { ...event.newData }
            // Remove the isNew flag if it exists
            delete sourceAssignments.value[index].isNew
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

const viewLogs = (): void => {
    showLogsDialog.value = true
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

// Lifecycle hooks
onMounted(async () => {
    await Promise.all([loadConfiguration(), loadSources(), loadLogFiles()])
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

.logs-content {
    max-height: 70vh;
    overflow-y: auto;
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
