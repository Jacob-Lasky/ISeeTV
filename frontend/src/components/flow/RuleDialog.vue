<template>
    <Dialog
        v-model:visible="visible"
        :header="isEditing ? 'Edit Rule' : 'Create New Rule'"
        :modal="true"
        :closable="true"
        :draggable="false"
        :resizable="false"
        class="rule-dialog"
        style="width: 500px"
    >
        <div class="rule-form">
            <div class="field">
                <label for="rule-name">Rule Name</label>
                <InputText
                    id="rule-name"
                    v-model="formData.name"
                    placeholder="Enter rule name"
                    class="w-full"
                    :class="{ 'p-invalid': errors.name }"
                />
                <small v-if="errors.name" class="p-error">{{
                    errors.name
                }}</small>
            </div>

            <div class="field">
                <label for="rule-table">Table</label>
                <Select
                    id="rule-table"
                    v-model="formData.tables[0]"
                    :options="tableOptions"
                    option-label="label"
                    option-value="value"
                    placeholder="Select table"
                    class="w-full"
                    :class="{ 'p-invalid': errors.table }"
                    @update:model-value="onTableChange"
                />
                <small v-if="errors.table" class="p-error">{{
                    errors.table
                }}</small>
            </div>

            <div class="field">
                <label for="rule-field">Field</label>
                <Select
                    id="rule-field"
                    v-model="formData.field"
                    :options="fieldOptions"
                    option-label="label"
                    option-value="value"
                    placeholder="Select field"
                    class="w-full"
                    :class="{ 'p-invalid': errors.field }"
                    :loading="loadingFields"
                    @focus="() => loadTableColumns()"
                />
                <small v-if="errors.field" class="p-error">{{
                    errors.field
                }}</small>
            </div>

            <div class="field">
                <label for="rule-regex">Pattern (Regex)</label>
                <InputText
                    id="rule-regex"
                    v-model="formData.regex"
                    placeholder="Enter regex pattern"
                    class="w-full"
                    :class="{ 'p-invalid': errors.regex }"
                />
                <small v-if="errors.regex" class="p-error">{{
                    errors.regex
                }}</small>
            </div>

            <div class="field">
                <div class="flex align-items-center">
                    <Checkbox
                        id="rule-not"
                        v-model="formData.not_"
                        :binary="true"
                    />
                    <label for="rule-not" class="ml-2"
                        >Inverse match (NOT)</label
                    >
                </div>
                <small class="text-muted"
                    >When checked, rule will match records that do NOT match the
                    pattern</small
                >
            </div>

            <div class="field">
                <div class="flex align-items-center">
                    <Checkbox
                        id="rule-enabled"
                        v-model="formData.enabled"
                        :binary="true"
                    />
                    <label for="rule-enabled" class="ml-2">Enabled</label>
                </div>
            </div>
        </div>

        <template #footer>
            <div class="flex justify-content-end gap-2">
                <Button
                    label="Cancel"
                    severity="secondary"
                    @click="closeDialog"
                />
                <Button
                    :label="isEditing ? 'Update' : 'Create'"
                    severity="primary"
                    :loading="saving"
                    @click="saveRule"
                />
            </div>
        </template>
    </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue"
import Dialog from "primevue/dialog"
import InputText from "primevue/inputtext"
import Select from "primevue/select"
import Checkbox from "primevue/checkbox"
import Button from "primevue/button"
import { useToast } from "primevue/usetoast"
import type { IngestionRule } from "@/types/types"

// Props and emits
interface Props {
    visible: boolean
    rule?: IngestionRule | null
    isEditing?: boolean
}

interface Emits {
    (e: "update:visible", value: boolean): void
    (e: "rule-saved", rule: IngestionRule): void
}

const props = withDefaults(defineProps<Props>(), {
    rule: null,
    isEditing: false,
})

const emit = defineEmits<Emits>()

// Composables
const toast = useToast()

// Reactive state
const saving = ref(false)
const loadingFields = ref(false)
const fieldOptions = ref<{ label: string; value: string }[]>([])
const columnOptionsCache = ref<
    Record<string, { label: string; value: string }[]>
>({})

// Form data
const formData = ref<IngestionRule>({
    name: "",
    tables: ["m3u_channels"],
    field: "",
    regex: ".*",
    not_: false,
    enabled: true,
})

// Form validation
const errors = ref<Record<string, string>>({})

// Table options
const tableOptions = [
    { label: "M3U Channels", value: "m3u_channels" },
    { label: "EPG Channels", value: "epg_channels" },
    { label: "Programs", value: "programs" },
]

// Computed properties
const visible = computed({
    get: () => props.visible,
    set: (value: boolean) => emit("update:visible", value),
})

// Methods - Define before watchers to avoid temporal dead zone
const loadTableColumns = async (tableName?: string) => {
    try {
        const table =
            tableName || (formData.value.tables && formData.value.tables[0])
        if (!table) {
            console.warn("No table specified for loading columns")
            return
        }

        // Use cached options if available
        if (columnOptionsCache.value[table]) {
            fieldOptions.value = columnOptionsCache.value[table]
            return
        }

        loadingFields.value = true
        const response = await fetch(`/api/metadata/tables/${table}`)

        if (!response.ok) {
            throw new Error(`Failed to fetch columns: ${response.statusText}`)
        }

        const result = await response.json()

        if (result.success && Array.isArray(result.data)) {
            const options = result.data.map((column: any) => ({
                label:
                    column.field.charAt(0).toUpperCase() +
                    column.field.slice(1).replace(/_/g, " "),
                value: column.field,
            }))

            fieldOptions.value = options
            columnOptionsCache.value[table] = options
        } else {
            console.warn("Invalid response format for table columns:", result)
        }
    } catch (error) {
        console.error("Failed to load table columns:", error)
        // Don't show toast on component initialization errors
        if (loadingFields.value) {
            toast.add({
                severity: "error",
                summary: "Load Failed",
                detail: "Failed to load table columns",
                life: 3000,
            })
        }
    } finally {
        loadingFields.value = false
    }
}

// Watch for rule changes to populate form
watch(
    () => props.rule,
    async (newRule) => {
        try {
            if (
                newRule &&
                typeof newRule === "object" &&
                Object.keys(newRule).length > 0 &&
                newRule.name // Ensure it's a valid rule object with a name
            ) {
                // Handle both 'table' (singular) and 'tables' (array) properties
                const tables =
                    newRule.tables ||
                    (newRule.table ? [newRule.table] : ["m3u_channels"])

                console.log("📋 Resolved tables:", tables)

                formData.value = {
                    name: newRule.name || "",
                    tables: Array.isArray(tables) ? [...tables] : [tables],
                    field: newRule.field || "",
                    regex: newRule.regex || newRule.pattern || ".*",
                    not_: Boolean(newRule.not_),
                    enabled: newRule.enabled !== false,
                }

                // Load field options for the current table first
                const table = tables[0] || "m3u_channels"
                await loadTableColumns(table)

                // Then set the field after columns are loaded
                if (newRule.field) {
                    formData.value.field = newRule.field
                }
            } else {
                // Reset form for new rule
                formData.value = {
                    name: "",
                    tables: ["m3u_channels"],
                    field: "",
                    regex: ".*",
                    not_: false,
                    enabled: true,
                }
                await loadTableColumns("m3u_channels")
            }

            // Clear errors
            errors.value = {}
        } catch (error) {
            // Set safe defaults
            formData.value = {
                name: "",
                tables: ["m3u_channels"],
                field: "",
                regex: ".*",
                not_: false,
                enabled: true,
            }
            errors.value = {}
        }
    },
    { immediate: true }
)

// Methods
const onTableChange = (tableName: string) => {
    if (typeof tableName === "string") {
        formData.value.tables = [tableName]
        formData.value.field = "" // Reset field selection
        loadTableColumns(tableName)
    }
}

const validateForm = (): boolean => {
    errors.value = {}

    if (!formData.value.name.trim()) {
        errors.value.name = "Rule name is required"
    }

    if (!formData.value.tables.length || !formData.value.tables[0]) {
        errors.value.table = "Table selection is required"
    }

    if (!formData.value.field.trim()) {
        errors.value.field = "Field selection is required"
    }

    if (!formData.value.regex.trim()) {
        errors.value.regex = "Pattern is required"
    } else {
        // Validate regex pattern
        try {
            new RegExp(formData.value.regex)
        } catch (e) {
            errors.value.regex = "Invalid regex pattern"
        }
    }

    return Object.keys(errors.value).length === 0
}

const saveRule = async () => {
    if (!validateForm()) {
        return
    }

    try {
        saving.value = true

        // Create rule object
        console.log("Form data before save:", formData.value)
        const rule: IngestionRule = {
            name: formData.value.name.trim(),
            tables:
                formData.value.tables &&
                formData.value.tables.length > 0 &&
                formData.value.tables[0]
                    ? [formData.value.tables[0]]
                    : ["m3u_channels"], // Fallback to default table
            field: formData.value.field,
            regex: formData.value.regex,
            not_: formData.value.not_,
            enabled: formData.value.enabled,
        }
        console.log("Rule object being saved:", rule)

        // Emit rule to parent FlowEditor which handles the complete rules array save
        emit("rule-saved", rule)
        closeDialog()
    } catch (error) {
        console.error("Save rule error:", error)
        toast.add({
            severity: "error",
            summary: "Save Failed",
            detail: `Failed to ${props.isEditing ? "update" : "create"} rule`,
            life: 3000,
        })
    } finally {
        saving.value = false
    }
}

const closeDialog = () => {
    visible.value = false
    errors.value = {}
}
</script>

<style scoped>
.rule-dialog {
    max-width: 90vw;
}

.rule-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.field {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.field label {
    font-weight: 600;
    color: var(--text-color);
    margin-bottom: 0.25rem;
    display: block;
}

/* Ensure labels are visible in dark mode */
:deep(.p-dialog) .field label {
    color: var(--text-color) !important;
}

/* Dark mode specific overrides */
@media (prefers-color-scheme: dark) {
    .field label {
        color: #ffffff !important;
    }
}

.text-muted {
    color: var(--text-color-secondary);
    font-size: 0.875rem;
}

.w-full {
    width: 100%;
}
</style>
