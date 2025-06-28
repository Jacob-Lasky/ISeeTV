<template>
    <div>
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

        <!-- New Source Dialog -->
        <Dialog
            v-model:visible="showNewSourceModal"
            header="New Source"
            :modal="true"
            :closable="false"
            :closeOnEscape="true"
            class="new-source-dialog"
        >
            <form @submit.prevent="saveNewSource">
                <div class="form-grid">
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
                        <label>Subscription Expires:</label>
                        <DatePicker
                            v-model="newSource.subscription_expires"
                            dateFormat="yy-mm-dd"
                            showIcon
                            fluid
                        />
                    </div>
                    <div class="form-row">
                        <label>Source Timezone:</label>
                        <Select
                            v-model="newSource.source_timezone"
                            :options="timezoneOptions"
                            optionLabel="label"
                            optionValue="value"
                            placeholder="Select timezone"
                            fluid
                        />
                    </div>
                </div>
            </form>
            <template #footer>
                <div class="dialog-footer">
                    <Button
                        label="Cancel"
                        icon="pi pi-times"
                        severity="secondary"
                        text
                        @click="showNewSourceModal = false"
                    />
                    <Button
                        label="Save"
                        icon="pi pi-check"
                        severity="success"
                        @click="saveNewSource"
                    />
                </div>
            </template>
        </Dialog>

        <!-- Delete Confirmation Dialog -->
        <Dialog
            v-model:visible="showDeleteDialog"
            header="Delete Confirmation"
            :modal="true"
            :closable="false"
            :closeOnEscape="true"
            class="delete-dialog"
        >
            <div class="confirmation-content">
                <i
                    class="pi pi-exclamation-triangle mr-3"
                    style="font-size: 2rem; color: var(--orange-500)"
                ></i>
                <span>Are you sure you want to delete this source?</span>
            </div>
            <template #footer>
                <div class="dialog-footer">
                    <Button
                        label="No"
                        icon="pi pi-times"
                        text
                        class="p-button-secondary"
                        @click="showDeleteDialog = false"
                    />
                    <Button
                        label="Yes"
                        icon="pi pi-check"
                        severity="danger"
                        @click="confirmDelete"
                    />
                </div>
            </template>
        </Dialog>

        <p v-if="error" class="error">{{ error }}</p>
        <p v-if="saveSuccess" class="success">{{ saveSuccess }}</p>
    </div>
</template>

<script setup lang="ts">
import { apiGet, apiPost } from "../utils/apiUtils"
import { ref, onMounted } from "vue"
import DataTable from "primevue/datatable"
import Column from "primevue/column"
import InputText from "primevue/inputtext"
import InputNumber from "primevue/inputnumber"
import Button from "primevue/button"
import Select from "primevue/select"
import DatePicker from "primevue/datepicker"
import Tag from "primevue/tag"
import Dialog from "primevue/dialog"
import { timezoneOptions } from "../utils/timezones"

// Modal state and new source object
const showNewSourceModal = ref(false)
const showDeleteDialog = ref(false)
const sourceToDeleteIndex = ref<number | null>(null)

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

const saveNewSource = async () => {
    try {
        // Add the new source to the sources array
        const updatedSources = [...sources.value, newSource.value]

        // Send the updated sources to the backend
        await apiPost("/api/sources", updatedSources, {
            successMessage: "New source added successfully",
            errorPrefix: "Failed to add source",
        })

        // Update local sources and reset form
        sources.value = updatedSources
        resetNewSource()
        showNewSourceModal.value = false
    } catch (err) {
        error.value = `Failed to add source: ${err instanceof Error ? err.message : String(err)}`

        // Clear error message after 5 seconds
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
        sources.value = await apiGet("/api/sources", {
            showSuccessToast: true,
            errorPrefix: "Failed to load sources",
        })
    } catch (err) {
        error.value = `Failed to load sources: ${err instanceof Error ? err.message : String(err)}`
    } finally {
        loading.value = false
    }
})

// Show delete confirmation dialog
const deleteSource = (index: number) => {
    sourceToDeleteIndex.value = index
    showDeleteDialog.value = true
}

// Handle delete confirmation
const confirmDelete = async () => {
    try {
        if (sourceToDeleteIndex.value === null) return

        const index = sourceToDeleteIndex.value
        const updated = [...sources.value]
        updated.splice(index, 1)

        await apiPost("/api/sources", updated, {
            successMessage: "Source deleted successfully",
            errorPrefix: "Failed to delete source",
        })

        sources.value = updated
        showDeleteDialog.value = false
        sourceToDeleteIndex.value = null
    } catch (err) {
        error.value = `Failed to delete source: ${err instanceof Error ? err.message : String(err)}`
        showDeleteDialog.value = false
    }
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
        await apiPost("/api/sources", sources.value, {
            successMessage: "Source updated successfully",
            errorPrefix: "Failed to update source",
        })
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
:deep(.new-source-dialog) {
    min-width: 400px;
    max-width: 90vw;
}

:deep(.new-source-dialog .p-dialog-header) {
    padding-bottom: 0.5rem;
}

:deep(.new-source-dialog .p-dialog-content) {
    padding: 0 1.5rem 1rem 1.5rem;
}

:deep(.delete-dialog) {
    width: 450px;
}

.confirmation-content {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    gap: 1rem;
    padding: 1rem 0;
}

.confirmation-content i {
    font-size: 2rem;
}
.form-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1rem;
    padding: 1rem 0;
}

@media (min-width: 768px) {
    .form-grid {
        grid-template-columns: 1fr 1fr;
    }
}

.form-row {
    margin-bottom: 0.5rem;
    display: flex;
    flex-direction: column;
}

.form-row label {
    font-weight: bold;
    margin-bottom: 0.3rem;
}

/* Dialog Footer */
.dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
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
