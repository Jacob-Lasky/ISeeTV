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
                table: { style: 'min-width: 50rem' },
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
                style="min-width: 8rem; max-width: 200px"
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
                style="min-width: 8rem; max-width: 200px"
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
                    <InputText v-model="data[field]" fluid />
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
            @click="addNewSource"
        />

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
import type { Source } from "../../types" // if you have a shared TS interface
import Button from "primevue/button"
import { nextTick } from "vue"
import ConfirmDialog from "primevue/confirmdialog"
import { useConfirm } from "primevue/useconfirm"

const sources = ref<Source[]>([])
const loading = ref(true)
const error = ref("")
const saveSuccess = ref("")
const editingRows = ref<Source[]>([])
const confirm = useConfirm()
const timezoneOptions = Intl.supportedValuesOf("timeZone").map((tz) => ({
    label: tz,
    value: tz,
}))

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

const addNewSource = async () => {
    const newSource = {
        name: "",
        enabled: true,
        m3u_url: "",
        epg_url: "",
        number_of_connections: 1,
        refresh_every_hours: 24,
        subscription_expires: "",
        source_timezone: "",
    }

    sources.value.push(newSource)

    await nextTick()
    document
        .querySelector("table")
        ?.scrollIntoView({ behavior: "smooth", block: "end" })

    // Edit the newly added row
    editingRows.value = [newSource]
}

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
</style>
