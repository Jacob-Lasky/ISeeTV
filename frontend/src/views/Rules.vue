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
                                            icon="pi pi-play"
                                            severity="success"
                                            outlined
                                            size="small"
                                            v-tooltip="'Apply this rule to all assigned sources'"
                                            :loading="applyingRule === data.name"
                                            @click="applyRule(data.name)"
                                        />
                                        <Button
                                            icon="pi pi-stop"
                                            severity="warning"
                                            outlined
                                            size="small"
                                            v-tooltip="'Unapply this rule from all assigned sources'"
                                            :loading="unapplyingRule === data.name"
                                            @click="unapplyRule(data.name)"
                                        />
                                        <Button
                                            icon="pi pi-trash"
                                            severity="danger"
                                            outlined
                                            size="small"
                                            v-tooltip="'Delete this rule'"
                                            @click="deleteRule(rules.indexOf(data))"
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
                                header="Actions"
                                style="width: 25%; min-width: 20rem"
                                bodyStyle="text-align:center"
                            >
                                <template #body="{ data }">
                                    <div class="flex flex-col gap-2">
                                        <!-- Source-level actions -->
                                        <div class="flex gap-1 justify-center">
                                            <Button
                                                icon="pi pi-play"
                                                severity="success"
                                                outlined
                                                size="small"
                                                v-tooltip="'Apply all assigned rules to this source'"
                                                :loading="applyingSourceRules === data.source_name"
                                                :disabled="applyingSourceRules !== null || unapplyingSourceRules !== null || applyingSourceRule !== null || unapplyingSourceRule !== null"
                                                @click="applySourceRules(data.source_name)"
                                            />
                                            <Button
                                                icon="pi pi-stop"
                                                severity="warning"
                                                outlined
                                                size="small"
                                                v-tooltip="'Unapply all rules from this source'"
                                                :loading="unapplyingSourceRules === data.source_name"
                                                :disabled="applyingSourceRules !== null || unapplyingSourceRules !== null || applyingSourceRule !== null || unapplyingSourceRule !== null"
                                                @click="unapplySourceRules(data.source_name)"
                                            />
                                            <Button
                                                icon="pi pi-trash"
                                                severity="danger"
                                                outlined
                                                size="small"
                                                v-tooltip="'Delete this assignment'"
                                                @click="
                                                    deleteAssignment(
                                                        sourceAssignments.indexOf(data)
                                                    )
                                                "
                                            />
                                        </div>
                                        <!-- Per-rule actions -->
                                        <div v-if="data.assigned_rules && data.assigned_rules.length > 0" class="flex flex-wrap gap-1 justify-center">
                                            <div v-for="ruleName in data.assigned_rules" :key="`${data.source_name}-${ruleName}`" class="flex gap-1">
                                                <Button
                                                    icon="pi pi-filter"
                                                    severity="info"
                                                    text
                                                    size="small"
                                                    :v-tooltip="`Apply rule '${ruleName}' to source '${data.source_name}'`"
                                                    :loading="applyingSourceRule === `${data.source_name}-${ruleName}`"
                                                    :disabled="applyingSourceRules !== null || unapplyingSourceRules !== null || applyingSourceRule !== null || unapplyingSourceRule !== null"
                                                    @click="applySourceRule(data.source_name, ruleName)"
                                                />
                                                <Button
                                                    icon="pi pi-filter-slash"
                                                    severity="help"
                                                    text
                                                    size="small"
                                                    :v-tooltip="`Unapply rule '${ruleName}' from source '${data.source_name}'`"
                                                    :loading="unapplyingSourceRule === `${data.source_name}-${ruleName}`"
                                                    :disabled="applyingSourceRules !== null || unapplyingSourceRules !== null || applyingSourceRule !== null || unapplyingSourceRule !== null"
                                                    @click="unapplySourceRule(data.source_name, ruleName)"
                                                />
                                            </div>
                                        </div>
                                    </div>
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
const applyingRules = ref(false)
const applyingRule = ref<string | null>(null)
const unapplyingRule = ref<string | null>(null)
const applyingSourceRules = ref<string | null>(null)
const unapplyingSourceRules = ref<string | null>(null)
const applyingSourceRule = ref<string | null>(null)
const unapplyingSourceRule = ref<string | null>(null)
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
                throw new Error(data.detail || `Failed to apply rules to ${table}`)
            }
            
            results.push({
                table: table,
                ...data.results
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
            detail: error instanceof Error ? error.message : "Failed to apply rules",
            life: 5000,
        })
    } finally {
        applyingRules.value = false
    }
}

// Apply a single rule to all assigned sources
const applyRule = async (ruleName: string): Promise<void> => {
    try {
        applyingRule.value = ruleName
        
        // Get sources assigned to this rule
        const assignedSources = sourceAssignments.value
            .filter(assignment => assignment.assigned_rules.includes(ruleName))
            .map(assignment => assignment.source_name)
        
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
        const rule = rules.value.find(r => r.name === ruleName)
        if (!rule) {
            throw new Error(`Rule '${ruleName}' not found`)
        }
        
        const tables = rule.tables || ["m3u_channels", "epg_channels", "programs"]
        const results = []
        
        // Apply rule to each assigned source and applicable table
        for (const sourceName of assignedSources) {
            for (const tableName of tables) {
                console.log(`Applying rule '${ruleName}' to ${tableName} for source ${sourceName}...`)
                
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
                    throw new Error(data.detail || `Failed to apply rule '${ruleName}' to ${tableName} for ${sourceName}`)
                }
                
                results.push({
                    rule: ruleName,
                    table: tableName,
                    source: sourceName,
                    ...data.results
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
            detail: error instanceof Error ? error.message : `Failed to apply rule '${ruleName}'`,
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
            .filter(assignment => assignment.assigned_rules.includes(ruleName))
            .map(assignment => assignment.source_name)
        
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
        const rule = rules.value.find(r => r.name === ruleName)
        if (!rule) {
            throw new Error(`Rule '${ruleName}' not found`)
        }
        
        const tables = rule.tables || ["m3u_channels", "epg_channels", "programs"]
        const results = []
        
        // Unapply rule from each assigned source and applicable table
        for (const sourceName of assignedSources) {
            for (const tableName of tables) {
                console.log(`Unapplying rule '${ruleName}' from ${tableName} for source ${sourceName}...`)
                
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
                    throw new Error(data.detail || `Failed to unapply rule '${ruleName}' from ${tableName} for ${sourceName}`)
                }
                
                results.push({
                    rule: ruleName,
                    table: tableName,
                    source: sourceName,
                    ...data.results
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
            detail: error instanceof Error ? error.message : `Failed to unapply rule '${ruleName}'`,
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
            throw new Error(data.detail || `Failed to apply rules to source ${sourceName}`)
        }
        
        console.log(`Source rules application results for ${sourceName}:`, data.results)
        
        // Calculate totals from the results
        const totals = data.results.tables ? 
            Object.values(data.results.tables).reduce(
                (acc: any, result: any) => ({
                    processed: acc.processed + (result.processed || 0),
                    filtered: acc.filtered + (result.filtered || 0),
                    passed: acc.passed + (result.passed || 0),
                }),
                { processed: 0, filtered: 0, passed: 0 }
            ) : data.results
        
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
            detail: error instanceof Error ? error.message : `Failed to apply rules to source '${sourceName}'`,
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
            console.log(`Unapplying all rules from ${tableName} for source ${sourceName}...`)
            
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
                throw new Error(data.detail || `Failed to unapply rules from ${tableName} for ${sourceName}`)
            }
            
            results.push({
                table: tableName,
                source: sourceName,
                ...data.results
            })
        }
        
        // Calculate totals
        const totalRecords = results.reduce(
            (acc, result) => acc + (result.processed || 0),
            0
        )
        
        console.log(`Source rules unapplication results for ${sourceName}:`, results)
        
        toast.add({
            severity: "success",
            summary: "Source Rules Unapplied",
            detail: `All rules unapplied from source '${sourceName}' (${totalRecords} records restored)`,
            life: 5000,
        })
        
    } catch (error) {
        console.error(`Error unapplying rules from source '${sourceName}':`, error)
        toast.add({
            severity: "error",
            summary: "Source Rule Unapplication Failed",
            detail: error instanceof Error ? error.message : `Failed to unapply rules from source '${sourceName}'`,
            life: 5000,
        })
    } finally {
        unapplyingSourceRules.value = null
    }
}

// Apply a specific rule to a specific source (most granular control)
const applySourceRule = async (sourceName: string, ruleName: string): Promise<void> => {
    try {
        const ruleKey = `${sourceName}-${ruleName}`
        applyingSourceRule.value = ruleKey
        
        console.log(`Applying rule '${ruleName}' to source '${sourceName}'...`)
        
        const response = await fetch("/api/rules/apply/single", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                rule_name: ruleName,
                source_name: sourceName,
                // table_names is optional - will apply to all tables by default
            }),
        })
        
        const data = await response.json()
        
        if (!response.ok) {
            throw new Error(data.detail || `Failed to apply rule '${ruleName}' to source '${sourceName}'`)
        }
        
        console.log(`Single rule application results for '${ruleName}' on '${sourceName}':`, data.results)
        
        // Calculate totals from the results
        const totals = data.results.tables ? 
            Object.values(data.results.tables).reduce(
                (acc: any, result: any) => ({
                    processed: acc.processed + (result.processed || 0),
                    filtered: acc.filtered + (result.filtered || 0),
                    passed: acc.passed + (result.passed || 0),
                }),
                { processed: 0, filtered: 0, passed: 0 }
            ) : data.results
        
        toast.add({
            severity: "success",
            summary: "Rule Applied",
            detail: `Rule '${ruleName}' applied to source '${sourceName}': ${totals.passed} passed, ${totals.filtered} filtered`,
            life: 5000,
        })
        
    } catch (error) {
        console.error(`Error applying rule '${ruleName}' to source '${sourceName}':`, error)
        toast.add({
            severity: "error",
            summary: "Rule Application Failed",
            detail: error instanceof Error ? error.message : `Failed to apply rule '${ruleName}' to source '${sourceName}'`,
            life: 5000,
        })
    } finally {
        applyingSourceRule.value = null
    }
}

// Unapply a specific rule from a specific source (most granular control)
const unapplySourceRule = async (sourceName: string, ruleName: string): Promise<void> => {
    try {
        const ruleKey = `${sourceName}-${ruleName}`
        unapplyingSourceRule.value = ruleKey
        
        const tables = ["m3u_channels", "epg_channels", "programs"]
        const results = []
        
        // Unapply the specific rule from each table for this source
        for (const tableName of tables) {
            console.log(`Unapplying rule '${ruleName}' from ${tableName} for source '${sourceName}'...`)
            
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
                throw new Error(data.detail || `Failed to unapply rule '${ruleName}' from ${tableName} for '${sourceName}'`)
            }
            
            results.push({
                table: tableName,
                source: sourceName,
                rule: ruleName,
                ...data.results
            })
        }
        
        // Calculate totals
        const totalRecords = results.reduce(
            (acc, result) => acc + (result.processed || 0),
            0
        )
        
        console.log(`Single rule unapplication results for '${ruleName}' on '${sourceName}':`, results)
        
        toast.add({
            severity: "success",
            summary: "Rule Unapplied",
            detail: `Rule '${ruleName}' unapplied from source '${sourceName}' (${totalRecords} records restored)`,
            life: 5000,
        })
        
    } catch (error) {
        console.error(`Error unapplying rule '${ruleName}' from source '${sourceName}':`, error)
        toast.add({
            severity: "error",
            summary: "Rule Unapplication Failed",
            detail: error instanceof Error ? error.message : `Failed to unapply rule '${ruleName}' from source '${sourceName}'`,
            life: 5000,
        })
    } finally {
        unapplyingSourceRule.value = null
    }
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
