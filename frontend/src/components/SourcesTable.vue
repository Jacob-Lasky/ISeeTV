<template>
    <div>
        <ConfirmDialog />
        <DataTable
            v-model:editingRows="editingRows"
            :value="sources"
            :loading="loading"
            responsiveLayout="scroll"
            stripedRows
            showGridlines
            :rows="10"
            editMode="row"
            dataKey="name"
            :pt="{
                table: { style: 'width: 100%; min-width: 70rem' },
                column: {
                    bodycell: ({ state }) => ({
                        style:
                            state['d_editing'] &&
                            'padding-top: 0.75rem; padding-bottom: 0.75rem',
                    }),
                },
            }"
            @row-edit-save="onRowEditSave"
        >
            <Column field="name" header="Name" sortable>
                <template #editor="{ data, field }">
                    <InputText v-model="data[field]" fluid />
                </template>
            </Column>
            <Column field="enabled" header="Enabled" sortable>
                <template #editor="{ data, field }">
                    <Select
                        v-model="data[field]"
                        :options="[true, false]"
                        fluid
                    />
                </template>
                <template #body="{ data }">
                    <Tag
                        :severity="data.enabled ? 'success' : 'danger'"
                        :value="data.enabled ? 'Yes' : 'No'"
                    />
                </template>
            </Column>
            <Column
                field="m3u_url"
                header="M3U URL"
                sortable
                style="min-width: 8rem; max-width: none"
                bodyStyle="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space;"
            >
                <template #editor="{ data, field }">
                    <InputText
                        v-model="data[field]"
                        fluid
                        style="min-width: 160px"
                    />
                </template>
            </Column>
            <Column
                field="epg_url"
                header="EPG URL"
                sortable
                style="min-width: 8rem; max-width: none"
                bodyStyle="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space;"
            >
                <template #editor="{ data, field }">
                    <InputText
                        v-model="data[field]"
                        fluid
                        style="min-width: 160px"
                    />
                </template>
            </Column>
            <Column field="number_of_connections" header="Connections" sortable>
                <template #editor="{ data, field }">
                    <InputNumber v-model="data[field]" fluid />
                </template>
            </Column>
            <Column field="refresh_every_hours" header="Refresh (h)" sortable>
                <template #editor="{ data, field }">
                    <InputNumber v-model="data[field]" fluid />
                </template>
            </Column>
            <Column field="subscription_expires" header="Expires" sortable>
                <template #editor="{ data, field }">
                    <DatePicker
                        v-model="data[field]"
                        showIcon
                        dateFormat="yy-mm-dd"
                    />
                </template>
                <template #body="{ data }">
                    {{ formatDate(data.subscription_expires) }}
                </template>
            </Column>
            <Column field="source_timezone" header="Timezone" sortable>
                <template #editor="{ data, field }">
                    <Select
                        v-model="data[field]"
                        :options="timezoneOptions"
                        optionLabel="label"
                        optionValue="value"
                        placeholder="Select timezone"
                        filter
                        fluid
                    />
                </template>
            </Column>
            <Column
                :rowEditor="true"
                style="width: 10%; min-width: 8rem"
                bodyStyle="text-align: center"
            />
            <Column header="" style="width: 10%; min-width: 2rem">
                <template #body="{ data, index }">
                    <Button
                        icon="pi pi-trash"
                        severity="danger"
                        text
                        rounded
                        @click="deleteSource(index)"
                    />
                </template>
            </Column>
        </DataTable>
        <br />
        <Button
            label="New Source"
            icon="pi pi-plus"
            class="mt-4"
            @click="showNewSourceModal = true"
        />

        <!-- New Source Modal -->
        <div v-if="showNewSourceModal" class="modal-overlay">
            <div class="modal">
                <h3>New Source</h3>
                <form @submit.prevent="saveNewSource">
                    <div class="form-row">
                        <label>Name:</label>
                        <InputText v-model="newSource.name" required fluid />
                    </div>
                    <div class="form-row">
                        <label>Enabled:</label>
                        <Select
                            v-model="newSource.enabled"
                            :options="[true, false]"
                            fluid
                        />
                    </div>
                    <div class="form-row">
                        <label>M3U URL:</label>
                        <InputText v-model="newSource.m3u_url" required fluid />
                    </div>
                    <div class="form-row">
                        <label>EPG URL:</label>
                        <InputText v-model="newSource.epg_url" fluid />
                    </div>
                    <div class="form-row">
                        <label>Connections:</label>
                        <InputNumber
                            v-model="newSource.number_of_connections"
                            :min="1"
                            required
                            fluid
                        />
                    </div>
                    <div class="form-row">
                        <label>Refresh (h):</label>
                        <InputNumber
                            v-model="newSource.refresh_every_hours"
                            :min="1"
                            required
                            fluid
                        />
                    </div>
                    <div class="form-row">
                        <label>Expires:</label>
                        <DatePicker
                            v-model="newSource.subscription_expires"
                            showIcon
                            dateFormat="yy-mm-dd"
                        />
                    </div>
                    <div class="form-row">
                        <label>Timezone:</label>
                        <Select
                            v-model="newSource.source_timezone"
                            :options="timezoneOptions"
                            optionLabel="label"
                            optionValue="value"
                            placeholder="Select timezone"
                            fluid
                        />
                    </div>
                    <div class="modal-actions">
                        <Button
                            label="Cancel"
                            class="p-button-text"
                            type="button"
                            @click="showNewSourceModal = false"
                        />
                        <Button label="Save" icon="pi pi-check" type="submit" />
                    </div>
                </form>
            </div>
        </div>

        <p v-if="error" class="error">{{ error }}</p>
        <p v-if="saveSuccess" class="success">{{ saveSuccess }}</p>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue"
import DataTable from "primevue/datatable"
import Column from "primevue/column"
import InputText from "primevue/inputtext"
import InputNumber from "primevue/inputnumber"
import Select from "primevue/select"
import Tag from "primevue/tag"
import type { Source } from "../../types"
import Button from "primevue/button"
import ConfirmDialog from "primevue/confirmdialog"
import { useConfirm } from "primevue/useconfirm"
import DatePicker from "primevue/datepicker"
import { timezoneOptions } from "../utils/timezones"

// Modal state and new source object
const showNewSourceModal = ref(false)
const newSource = ref({
    name: "",
    enabled: true,
    m3u_url: "",
    epg_url: "",
    number_of_connections: 1,
    refresh_every_hours: 24,
    subscription_expires: "",
    source_timezone: "",
})

function resetNewSource() {
    newSource.value = {
        name: "",
        enabled: true,
        m3u_url: "",
        epg_url: "",
        number_of_connections: 1,
        refresh_every_hours: 24,
        subscription_expires: "",
        source_timezone: "",
    }
}

async function saveNewSource() {
    try {
        sources.value.push({ ...newSource.value })
        const response = await fetch("/api/sources", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(sources.value),
        })
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const result = await response.json()
        saveSuccess.value = result.message || "Source added successfully"
        showNewSourceModal.value = false
        resetNewSource()
        setTimeout(() => {
            saveSuccess.value = ""
        }, 3000)
    } catch (err) {
        error.value = `Failed to save sources: ${err instanceof Error ? err.message : String(err)}`
        setTimeout(() => {
            error.value = ""
        }, 5000)
    }
}

const sources = ref<Source[]>([])
const loading = ref(true)
const error = ref("")
const saveSuccess = ref("")
const editingRows = ref<Source[]>([])
const confirm = useConfirm()

function formatDate(date: string | Date) {
    if (!date) return ""
    const d = typeof date === "string" ? new Date(date) : date
    if (isNaN(d.getTime())) return ""
    const yyyy = d.getFullYear()
    const mm = String(d.getMonth() + 1).padStart(2, "0")
    const dd = String(d.getDate()).padStart(2, "0")
    return `${yyyy}-${mm}-${dd}`
}

onMounted(async () => {
    try {
        const res = await fetch("/api/sources")
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        sources.value = await res.json()
    } catch (err) {
        error.value = `Failed to load sources: ${err instanceof Error ? err.message : String(err)}`
    } finally {
        loading.value = false
    }
})

const deleteSource = async (index: number) => {
    confirm.require({
        message: "Are you sure you want to delete this source?",
        header: "Delete Confirmation",
        icon: "pi pi-exclamation-triangle",
        acceptClass: "p-button-danger",
        accept: async () => {
            try {
                const updated = [...sources.value]
                updated.splice(index, 1)

                const response = await fetch("/api/sources", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(updated),
                })

                if (!response.ok) throw new Error(`HTTP ${response.status}`)

                sources.value = updated
                saveSuccess.value = "Source deleted successfully"
            } catch (err) {
                error.value = `Failed to delete source: ${err instanceof Error ? err.message : String(err)}`
            }
        },
        reject: () => {
            // User rejected the confirmation, do nothing
        },
    })
}

const onRowEditSave = async (event: {
    data: Source
    newData: Source
    index: number
}) => {
    try {
        // Update the local data
        const { newData, index } = event
        sources.value[index] = newData

        // Send the updated sources to the backend
        const response = await fetch("/api/sources", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(sources.value),
        })

        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`)
        }

        const result = await response.json()
        saveSuccess.value = result.message || "Source updated successfully"

        // Clear success message after 3 seconds
        setTimeout(() => {
            saveSuccess.value = ""
        }, 3000)
    } catch (err) {
        error.value = `Failed to update source: ${err instanceof Error ? err.message : String(err)}`

        // Clear error message after 5 seconds
        setTimeout(() => {
            error.value = ""
        }, 5000)
    }
}
</script>

<style scoped>
.error {
    color: red;
    margin-top: 1rem;
}

.success {
    color: green;
    margin-top: 1rem;
}
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
    padding: 2rem;
    border-radius: 8px;
    min-width: 350px;
    max-width: 90vw;
    box-shadow: 0 2px 16px rgba(0, 0, 0, 0.2);
}
.form-row {
    margin-bottom: 1rem;
    display: flex;
    flex-direction: column;
}
.form-row label {
    font-weight: bold;
    margin-bottom: 0.3rem;
}
.modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
}

.error {
    color: red;
    margin-top: 1rem;
}

.success {
    color: green;
    margin-top: 1rem;
}
</style>
