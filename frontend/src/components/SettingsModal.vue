<template>
    <div class="modal-overlay" @click.self="tryClose">
        <div v-if="showDiscardDialog" class="discard-dialog-overlay">
            <div class="discard-dialog">
                <p>Discard changes?</p>
                <div class="dialog-actions">
                    <button class="discard-btn" @click="discardChanges">
                        Discard
                    </button>
                    <button
                        class="cancel-btn"
                        @click="showDiscardDialog = false"
                    >
                        Cancel
                    </button>
                </div>
            </div>
        </div>
        <div class="modal">
            <header>
                <h2>Settings</h2>
                <button class="close-btn" @click="tryClose">&times;</button>
            </header>
            <section v-if="loading" class="loading">Loading...</section>
            <section v-else-if="error" class="error">{{ error }}</section>
            <section v-else class="settings-content">
                <table class="settings-table">
                    <tbody>
                        <tr>
                            <td class="label">User Timezone</td>
                            <td class="value">
                                <Select
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
                                <InputNumber
                                    v-model="
                                        editableSettings.program_cache_days
                                    "
                                    inputClass="settings-input right-align"
                                    :min="1"
                                />
                            </td>
                        </tr>
                        <tr>
                            <td class="label">Theme</td>
                            <td class="value">
                                <Select
                                    v-model="editableSettings.theme"
                                    :options="themeOptions"
                                    optionLabel="label"
                                    optionValue="value"
                                    placeholder="Select theme"
                                    inputClass="settings-input right-align"
                                    style="width: 100%"
                                />
                            </td>
                        </tr>
                    </tbody>
                </table>
                <div class="actions">
                    <button
                        class="save-btn"
                        :disabled="saving"
                        @click="saveSettings"
                    >
                        {{ saving ? "Saving..." : "Save" }}
                    </button>
                </div>
            </section>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed } from "vue"
import InputNumber from "primevue/inputnumber"
import Select from "primevue/select"
import { timezoneOptions } from "../utils/timezones"

const props = defineProps<{ open: boolean }>()
const emit = defineEmits(["close"])

const settings = ref<any>(null)
const editableSettings = ref<any>({})
const loading = ref(false)
const error = ref<string | null>(null)
const saving = ref(false)

const themeOptions = [
    { label: "Light", value: "light" },
    { label: "Dark", value: "dark" },
    { label: "System", value: "system" },
]

function close() {
    emit("close")
}

function tryClose() {
    if (hasUnsavedChanges.value) {
        showDiscardDialog.value = true
    } else {
        close()
    }
}

function discardChanges() {
    showDiscardDialog.value = false
    close()
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

const showDiscardDialog = ref(false)

async function fetchSettings() {
    loading.value = true
    error.value = null
    try {
        const res = await fetch("/api/settings")
        if (!res.ok) throw new Error("Failed to fetch settings")
        const data = await res.json()
        settings.value = data
        editableSettings.value = { ...data }
    } catch (e: any) {
        error.value = e.message || "Unknown error"
    } finally {
        loading.value = false
    }
}

async function saveSettings() {
    saving.value = true
    error.value = null
    try {
        const res = await fetch("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(editableSettings.value),
        })
        if (!res.ok) throw new Error("Failed to save settings")
        await fetchSettings() // reload settings
        // Optionally show a success message here
        close()
    } catch (e: any) {
        error.value = e.message || "Unknown error"
    } finally {
        saving.value = false
    }
}

onMounted(() => {
    if (props.open) fetchSettings()
})

watch(
    () => props.open,
    (val) => {
        if (val) fetchSettings()
    }
)
</script>

<style scoped>
.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0, 0, 0, 0.4);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}
.modal {
    background: #fff;
    border-radius: 8px;
    padding: 2rem;
    min-width: 350px;
    max-width: 90vw;
    box-shadow: 0 2px 16px rgba(0, 0, 0, 0.2);
    position: relative;
}
.close-btn {
    background: none;
    border: none;
    font-size: 2rem;
    position: absolute;
    top: 1rem;
    right: 1rem;
    cursor: pointer;
}
.loading,
.error {
    padding: 1rem;
    text-align: center;
}
.settings-content {
    padding: 1rem 0;
}
.settings-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0 0.5rem;
    margin-bottom: 1.5rem;
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
.settings-input {
    width: 80%;
    font-size: 1rem;
    padding: 0.3rem 0.6rem;
    border: 1px solid #ccc;
    border-radius: 4px;
}
.right-align {
    text-align: right;
}
.actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 1rem;
}
.save-btn {
    background: #42b983;
    color: #fff;
    border: none;
    padding: 0.5rem 1.5rem;
    border-radius: 4px;
    font-size: 1rem;
    cursor: pointer;
    transition: background 0.2s;
}
.save-btn:disabled {
    background: #b3e0cd;
    cursor: not-allowed;
}
.save-btn:hover:not(:disabled) {
    background: #36996f;
}
.discard-dialog-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0, 0, 0, 0.35);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 2000;
}
.discard-dialog {
    background: #fff;
    padding: 2rem 2.5rem;
    border-radius: 8px;
    box-shadow: 0 2px 16px rgba(0, 0, 0, 0.2);
    text-align: center;
    min-width: 260px;
}
.dialog-actions {
    margin-top: 1.5rem;
    display: flex;
    justify-content: center;
    gap: 1.5rem;
}
.discard-btn {
    background: #e74c3c;
    color: #fff;
    border: none;
    padding: 0.5rem 1.2rem;
    border-radius: 4px;
    font-weight: bold;
    cursor: pointer;
    transition: background 0.2s;
}
.discard-btn:hover {
    background: #c0392b;
}
.cancel-btn {
    background: #eee;
    color: #333;
    border: none;
    padding: 0.5rem 1.2rem;
    border-radius: 4px;
    font-weight: bold;
    cursor: pointer;
    transition: background 0.2s;
}
.cancel-btn:hover {
    background: #ccc;
}
</style>
