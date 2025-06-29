<template>
    <Dialog
        v-model:visible="dialogVisible"
        header="Settings"
        :modal="true"
        :closable="false"
        :closeOnEscape="true"
        class="settings-dialog"
    >
        <template #header>
            <h2>Settings</h2>
        </template>
        <div v-if="error" class="error">
            <Message severity="error" :closable="false">{{ error }}</Message>
        </div>
        <div class="settings-content">
            <table class="settings-table">
                <tbody>
                    <tr>
                        <td class="label">User Timezone</td>
                        <td class="value">
                            <div v-if="loading" class="skeleton-row">
                                <Skeleton width="100%" height="2.5rem" />
                            </div>
                            <Select
                                v-else
                                v-model="editableSettings.user_timezone"
                                :options="timezoneOptions"
                                optionLabel="label"
                                optionValue="value"
                                placeholder="Select timezone"
                                filter
                                inputClass="settings-input right-align"
                                style="width: 100%"
                            />
                        </td>
                    </tr>
                    <tr>
                        <td class="label">Program Cache Days</td>
                        <td class="value">
                            <div v-if="loading" class="skeleton-row">
                                <Skeleton width="100%" height="2.5rem" />
                            </div>
                            <InputNumber
                                v-else
                                v-model="editableSettings.program_cache_days"
                                inputClass="settings-input right-align"
                                :min="1"
                            />
                        </td>
                    </tr>
                    <tr>
                        <td class="label">Theme</td>
                        <td class="value">
                            <div v-if="loading" class="skeleton-row">
                                <Skeleton width="100%" height="2.5rem" />
                            </div>
                            <Select
                                v-else
                                v-model="editableSettings.theme"
                                :options="themeOptions"
                                optionLabel="label"
                                optionValue="value"
                                placeholder="Select theme"
                                inputClass="settings-input right-align"
                                style="width: 100%"
                                @change="
                                    themeStore.setTheme(editableSettings.theme)
                                "
                            />
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- Dialog Footer with Actions -->
        <template #footer>
            <div class="dialog-footer">
                <Button
                    label="Cancel"
                    icon="pi pi-times"
                    severity="secondary"
                    text
                    @click="tryClose"
                />
                <Button
                    label="Save"
                    icon="pi pi-check"
                    :loading="saving"
                    severity="success"
                    @click="saveSettings"
                />
            </div>
        </template>
    </Dialog>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed } from "vue"
import { useConfirm } from "primevue/useconfirm"
import { apiGet, apiPost } from "../utils/apiUtils"

// Import PrimeVue components
import Dialog from "primevue/dialog"
import Button from "primevue/button"
import InputNumber from "primevue/inputnumber"
import Select from "primevue/select"
import Skeleton from "primevue/skeleton"
import Message from "primevue/message"

// Import utilities and stores
import { timezoneOptions } from "../utils/timezones"
import { useThemeStore, type ThemeMode } from "../stores/themeStore"

// Define interface for settings structure
interface AppSettings {
    user_timezone: string
    program_cache_days: number
    theme: ThemeMode
    [key: string]: string | number | boolean // Allow for additional properties
}

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits(["update:visible"])

// Initialize theme store and confirm service
const themeStore = useThemeStore()
const confirm = useConfirm()

// State management
const loading = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)
const settings = ref<AppSettings | null>(null)
const editableSettings = ref<AppSettings>({
    user_timezone: "UTC",
    program_cache_days: 7,
    theme: themeStore.theme as ThemeMode,
})

// Computed property for dialog visibility with two-way binding
const dialogVisible = computed({
    get: () => props.visible,
    set: (value) => emit("update:visible", value),
})

const themeOptions = [
    { label: "Light", value: "light" },
    { label: "Dark", value: "dark" },
    { label: "System", value: "system" },
]

function close() {
    dialogVisible.value = false
}

function tryClose() {
    if (hasUnsavedChanges.value) {
        confirm.require({
            message: "Discard unsaved changes?",
            header: "Confirmation",
            icon: "pi pi-exclamation-triangle",
            acceptClass: "p-button-danger",
            accept: () => {
                fetchSettings()
                close()
            },
            reject: () => {
                // Stay on the dialog
            },
        })
    } else {
        close()
    }
}

const hasUnsavedChanges = computed(() => {
    if (!settings.value) return false
    return (
        settings.value.user_timezone !== editableSettings.value.user_timezone ||
        settings.value.program_cache_days !==
            editableSettings.value.program_cache_days ||
        settings.value.theme !== editableSettings.value.theme
    )
})

async function fetchSettings() {
    loading.value = true
    error.value = null
    try {
        const data = await apiGet("/api/settings", false, {
            showSuccessToast: true,
            errorPrefix: "Failed to load settings",
        })

        // If theme is not in settings, add it with the current theme from store
        if (!data.theme) {
            data.theme = themeStore.theme
        } else {
            // If theme is in settings and different from store, update the store
            if (data.theme !== themeStore.theme) {
                themeStore.setTheme(data.theme)
            }
        }

        settings.value = data
        editableSettings.value = { ...data }
    } catch (e: unknown) {
        error.value = e instanceof Error ? e.message : "Unknown error"
    } finally {
        loading.value = false
    }
}

async function saveSettings() {
    saving.value = true
    error.value = null
    try {
        // Update theme in the store if it has changed
        if (
            settings.value &&
            settings.value.theme !== editableSettings.value.theme
        ) {
            themeStore.setTheme(editableSettings.value.theme)
        }

        await apiPost("/api/settings", editableSettings.value, true, {
            successMessage: "Settings saved successfully",
            errorPrefix: "Failed to save settings",
        })

        await fetchSettings() // reload settings
        close()
    } catch (e: unknown) {
        error.value = e instanceof Error ? e.message : "Unknown error"
    } finally {
        saving.value = false
    }
}

onMounted(() => {
    if (props.visible) fetchSettings()
})

watch(
    () => props.visible,
    (val) => {
        if (val) fetchSettings()
    }
)
</script>

<style scoped>
/* Settings Dialog Styling */
:deep(.settings-dialog) {
    min-width: 400px;
    max-width: 90vw;
}

:deep(.settings-dialog .p-dialog-header) {
    padding-bottom: 0.5rem;
}

:deep(.settings-dialog .p-dialog-content) {
    padding: 0 1.5rem 1rem 1.5rem;
}

/* Skeleton Row Loading */
.skeleton-row {
    width: 100%;
    display: flex;
    align-items: center;
}

/* Error Message */
.error {
    padding: 1rem 0;
}

/* Settings Content */
.settings-content {
    padding: 1rem 0;
}

/* Settings Table */
.settings-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0 0.5rem;
    margin-bottom: 1rem;
}

.settings-table .label {
    text-align: left;
    font-weight: bold;
    padding-right: 1.5rem;
    vertical-align: middle;
    width: 60%;
}

.settings-table .value {
    text-align: right;
    vertical-align: middle;
    width: 40%;
}

/* Input Styling */
.settings-input {
    width: 100%;
    font-size: 1rem;
}

.right-align {
    text-align: right;
}

/* Dialog Footer */
.dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
}

/* Confirm Dialog Styling */
.confirm-dialog-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
    padding: 1rem 0;
    text-align: center;
}

/* PrimeVue Component Overrides */
:deep(.p-inputnumber-input) {
    text-align: right;
}

:deep(.p-dropdown) {
    width: 100%;
}

/* Responsive adjustments */
@media (max-width: 768px) {
    :deep(.settings-dialog) {
        width: 95vw;
        min-width: unset;
    }

    .settings-table {
        display: flex;
        flex-direction: column;
    }

    .settings-table tbody {
        display: flex;
        flex-direction: column;
        width: 100%;
    }

    .settings-table tr {
        display: flex;
        flex-direction: column;
        margin-bottom: 1rem;
        width: 100%;
    }

    .settings-table .label,
    .settings-table .value {
        width: 100%;
        text-align: left;
        padding: 0.25rem 0;
    }
}
</style>
