<template>
    <div>
        <h1>Flows</h1>
        <FlowEditor 
            :available-sources="sources"
            :available-rules="rules"
            :available-plugins="plugins"
        />
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue"
import FlowEditor from "@/components/flow/FlowEditor.vue"
import type { Source, IngestionRule } from "@/types/types"

// Reactive state
const sources = ref<Source[]>([])
const rules = ref<IngestionRule[]>([])
const plugins = ref<any[]>([]) // Add plugins if needed

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

// Load rules from API
const loadRules = async (): Promise<void> => {
    try {
        const response = await fetch("/api/rules")
        const data = await response.json()
        // Extract rules array from response object
        rules.value = data?.rules || []
    } catch (error) {
        console.error("Error loading rules:", error)
    }
}

// Load data on component mount
onMounted(async () => {
    await Promise.all([
        loadSources(),
        loadRules()
    ])
})
</script>

<style scoped>
h2 {
    margin-bottom: 1rem;
}
</style>
