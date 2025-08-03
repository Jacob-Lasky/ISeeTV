<template>
    <div class="source-node">
        <div class="node-header">
            <i class="pi pi-database"></i>
            <span class="node-title">{{ data.label }}</span>
        </div>

        <div class="node-body">
            <!-- Table Statistics Display -->
            <div class="stats-section">
                <!-- Individual table counts -->
                <template v-for="table in data.tables" :key="table.name">
                    <div
                        class="stat-item table-stat"
                        :style="{ borderLeftColor: getTableColor(table.name) }"
                    >
                        <span class="stat-label">{{ table.name }}:</span>
                        <span class="stat-value">{{
                            formatNumber(table.recordCount)
                        }}</span>
                    </div>
                </template>
            </div>

            <!-- Execution Status -->
            <div v-if="data.isExecuting" class="execution-status">
                <i class="pi pi-spin pi-spinner"></i>
                <span>Processing...</span>
            </div>
        </div>

        <!-- Output handles for each table -->
        <template v-for="(table, index) in data.tables" :key="table.name">
            <Handle
                :id="`table-${table.name}`"
                type="source"
                :position="Position.Right"
                :style="{
                    top: `${25 + index * 25}%`,
                    backgroundColor: getTableColor(table.name),
                    borderColor: getTableColor(table.name),
                }"
                class="output-handle table-handle"
            />
            <div
                v-if="isSelected"
                class="handle-label table-label"
                :style="{
                    top: `${25 + index * 25}%`,
                    backgroundColor: getTableColor(table.name),
                }"
            >
                {{ table.name }}
            </div>
        </template>
    </div>
</template>

<script setup lang="ts">
import { computed, inject } from "vue"
import { Handle, Position, useNode } from "@vue-flow/core"
import type { SourceNodeData } from "@/types/flow-types"

// Props
interface Props {
    data: SourceNodeData
}

const props = defineProps<Props>()

// Selection state for conditional label display
const selectedNodeId = inject<any>("selectedNodeId")
const { node } = useNode()

// Check if this node is selected
const isSelected = computed(() => {
    return selectedNodeId?.value === node.id
})

// Utility functions
const formatNumber = (num: number): string => {
    return new Intl.NumberFormat().format(num)
}

// Color coding for different table types
const getTableColor = (tableName: string): string => {
    const colorMap: Record<string, string> = {
        m3u_channels: "#3b82f6", // blue-500 - for M3U channel data
        epg_channels: "#eab308", // yellow-500 - for EPG channel data
        programs: "#8b5cf6", // violet-500 - for program guide data
        default: "#6b7280", // gray-500 - fallback color
    }
    return colorMap[tableName] || colorMap.default
}
</script>

<style scoped>
.source-node {
    background: var(--card-background);
    border: 2px solid var(--primary-color);
    border-radius: 0.5rem;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    min-width: 14rem;
    padding: 0.75rem;
    position: relative;
    transition: box-shadow 0.2s;
}

.source-node:hover {
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}

.node-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border-color);
}

.node-header i {
    color: var(--primary-color);
    font-size: 1.125rem;
}

.node-title {
    font-weight: 600;
    color: var(--text-color);
    font-size: 0.875rem;
}

.node-body {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.source-info {
    text-align: center;
}

.source-name {
    font-weight: 500;
    color: var(--text-color);
    font-size: 0.875rem;
}

.record-count {
    font-size: 0.75rem;
    color: var(--text-color);
    opacity: 0.7;
}

.stats-section {
    background: var(--card-background);
    border-radius: 0.25rem;
    padding: 0.5rem;
    border: 1px solid var(--border-color);
}

.stat-item {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
}

.table-stat {
    border-left: 3px solid;
    padding-left: 0.5rem;
    margin-left: -0.5rem;
    margin-top: 0.25rem;
}

.stat-label {
    color: var(--text-color);
    opacity: 0.7;
}

.stat-value {
    font-weight: 500;
    color: var(--primary-color);
}

.execution-status {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.75rem;
    color: var(--primary-color);
    background: var(--hover-color);
    border-radius: 0.25rem;
    padding: 0.25rem 0.5rem;
}

.output-handle {
    background: var(--primary-color);
    border: 2px solid var(--card-background);
    width: 0.75rem;
    height: 0.75rem;
}

.output-handle:hover {
    background: var(--primary-color);
    opacity: 0.8;
}

.table-handle {
    background: var(--primary-color);
}

.handle-label {
    @apply absolute right-0 text-xs font-medium pointer-events-none;
    @apply bg-white px-1 rounded shadow-sm border;
    transform: translateX(100%);
}

.table-label {
    @apply text-blue-700 border-blue-200;
}
</style>
