<template>
    <div class="stream-node" :class="streamTypeClass">
        <div class="node-header">
            <i :class="streamIcon"></i>
            <span class="node-title">{{ data.label }}</span>
        </div>

        <div class="node-body">
            <div class="stream-info">
                <div class="stream-type">
                    <Tag
                        :value="data.streamType.toUpperCase()"
                        :severity="streamSeverity"
                        class="text-xs font-bold"
                    />
                </div>
                <div v-if="data.description" class="stream-description">
                    {{ data.description }}
                </div>
            </div>

            <!-- Statistics Display -->
            <div v-if="data.stats" class="stats-section">
                <div class="total-records">
                    <span class="stat-label">Total Records:</span>
                    <span class="stat-value">{{
                        formatNumber(data.stats.processed)
                    }}</span>
                </div>
                <div v-if="data.lastExecuted" class="last-executed">
                    <span class="stat-label">Last Updated:</span>
                    <span class="stat-value">{{
                        formatTime(data.lastExecuted)
                    }}</span>
                </div>
            </div>

            <!-- Execution Status -->
            <div v-if="data.isExecuting" class="execution-status">
                <i class="pi pi-spin pi-spinner"></i>
                <span>Receiving...</span>
            </div>
        </div>

        <!-- Input Handle -->
        <Handle
            id="input"
            type="target"
            :position="Position.Left"
            class="input-handle"
        />
    </div>
</template>

<script setup lang="ts">
import { computed } from "vue"
import { Handle, Position } from "@vue-flow/core"
import Tag from "primevue/tag"
import type { StreamNodeData } from "@/types/flow-types"

// Props - Define all Vue Flow props to prevent warnings
interface Props {
    id: string
    data: StreamNodeData
    // Vue Flow internal props
    type?: string
    events?: any
    selected?: boolean
    resizing?: boolean
    dragging?: boolean
    connectable?: boolean
    position?: { x: number; y: number }
    dimensions?: { width: number; height: number }
    isValidTargetPos?: boolean
    isValidSourcePos?: boolean
    parent?: string
    parentNodeId?: string
    zIndex?: number
    targetPosition?: string
    sourcePosition?: string
    label?: string
    dragHandle?: string
}

const props = defineProps<Props>()

// Define emits for Vue Flow event listeners
const emit = defineEmits<{
    updateNodeInternals: [nodeId: string]
}>()

// Computed properties
const streamTypeClass = computed(() => {
    return props.data.streamType === "accepted"
        ? "accepted-stream"
        : "rejected-stream"
})

const streamIcon = computed(() => {
    return props.data.streamType === "accepted"
        ? "pi pi-check-circle"
        : "pi pi-times-circle"
})

const streamSeverity = computed(() => {
    return props.data.streamType === "accepted" ? "success" : "danger"
})

// Utility functions
const formatNumber = (num: number): string => {
    return new Intl.NumberFormat().format(num)
}

const formatTime = (date: Date): string => {
    return new Intl.DateTimeFormat("en-US", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
    }).format(date)
}
</script>

<style scoped>
.stream-node {
    border: 2px solid;
    border-radius: 0.5rem;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    min-width: 12rem;
    padding: 0.75rem;
    position: relative;
    transition: box-shadow 0.2s;
    background: var(--card-background);
}

.stream-node:hover {
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}

.accepted-stream {
    border-color: var(--primary-color);
}

.rejected-stream {
    border-color: #ef4444;
}

.node-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
    padding-bottom: 0.5rem;
}

.accepted-stream .node-header {
    border-bottom: 1px solid var(--border-color);
}

.rejected-stream .node-header {
    border-bottom: 1px solid var(--border-color);
}

.accepted-stream .node-header i {
    color: var(--primary-color);
    font-size: 1.125rem;
}

.rejected-stream .node-header i {
    color: #ef4444;
    font-size: 1.125rem;
}

.accepted-stream .node-title {
    font-weight: 600;
    color: var(--text-color);
    font-size: 0.875rem;
}

.rejected-stream .node-title {
    font-weight: 600;
    color: var(--text-color);
    font-size: 0.875rem;
}

.node-body {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.stream-info {
    text-align: center;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.stream-type {
    display: flex;
    justify-content: center;
}

.stream-description {
    font-size: 0.75rem;
    color: var(--text-color);
    opacity: 0.7;
    font-style: italic;
}

.stats-section {
    background: var(--card-background);
    border-radius: 0.25rem;
    padding: 0.5rem;
    border: 1px solid var(--border-color);
}

.accepted-stream .stats-section {
    border-color: var(--border-color);
}

.rejected-stream .stats-section {
    border-color: var(--border-color);
}

.total-records,
.last-executed {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
}

.stat-label {
    color: var(--text-color);
    opacity: 0.7;
}

.accepted-stream .stat-value {
    font-weight: 500;
    color: var(--primary-color);
}

.rejected-stream .stat-value {
    font-weight: 500;
    color: #ef4444;
}

.execution-status {
    @apply flex items-center gap-1 text-xs rounded px-2 py-1;
}

.accepted-stream .execution-status {
    @apply text-green-600 bg-green-100;
}

.rejected-stream .execution-status {
    @apply text-red-600 bg-red-100;
}

.input-handle {
    @apply bg-gray-500 border-2 border-white w-3 h-3;
}

.input-handle:hover {
    @apply bg-gray-600 opacity-80;
}
</style>
