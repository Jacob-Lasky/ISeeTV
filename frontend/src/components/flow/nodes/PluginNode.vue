<template>
    <div class="plugin-node-wrapper">
        <!-- Node Toolbar -->
        <NodeToolbar
            :is-visible="data.toolbarVisible"
            :position="data.toolbarPosition || 'top'"
        >
            <div class="toolbar-buttons">
                <Button
                    icon="pi pi-step-forward"
                    size="small"
                    severity="secondary"
                    text
                    :loading="isExecuting"
                    @click="handleExecuteToHere"
                    v-tooltip.top="'Run flow up to this node'"
                />
                <Button
                    icon="pi pi-play-circle"
                    size="small"
                    severity="info"
                    text
                    :loading="isExecuting"
                    @click="handleExecuteThisNode"
                    v-tooltip.top="'Run this node only'"
                />
                <Button
                    icon="pi pi-fast-forward"
                    size="small"
                    severity="success"
                    text
                    :loading="isExecuting"
                    @click="handleExecuteFromHere"
                    v-tooltip.top="'Run flow from this node'"
                />
            </div>
        </NodeToolbar>

        <div class="plugin-node" :class="{ disabled: !data.enabled }">
            <div class="node-header">
                <i class="pi pi-cog"></i>
                <span class="node-title">{{ data.label }}</span>
                <ToggleSwitch
                    v-model="data.enabled"
                    class="ml-auto"
                    @change="onEnabledChange"
                />
            </div>

            <div class="node-body">
                <div class="plugin-info">
                    <div class="plugin-name">{{ data.pluginName }}</div>
                    <div class="plugin-type">
                        <Tag
                            :value="data.pluginType"
                            severity="secondary"
                            class="text-xs"
                        />
                    </div>
                </div>

                <!-- Parameters Display -->
                <div
                    v-if="
                        data.parameters &&
                        Object.keys(data.parameters).length > 0
                    "
                    class="parameters-section"
                >
                    <div class="parameters-header">Parameters</div>
                    <div class="parameters-list">
                        <div
                            v-for="(value, key) in data.parameters"
                            :key="key"
                            class="parameter-item"
                        >
                            <span class="param-key"
                                >{{ formatParameterKey(key) }}:</span
                            >
                            <span class="param-value">{{
                                formatParameterValue(value)
                            }}</span>
                        </div>
                    </div>
                </div>

                <!-- Statistics Display -->
                <div v-if="data.stats" class="stats-section">
                    <div class="stat-row">
                        <div class="stat-item passed">
                            <span class="stat-label">Passed:</span>
                            <span class="stat-value">{{
                                formatNumber(data.stats.passed)
                            }}</span>
                        </div>
                        <div class="stat-item caught">
                            <span class="stat-label">Caught:</span>
                            <span class="stat-value">{{
                                formatNumber(data.stats.caught)
                            }}</span>
                        </div>
                    </div>
                </div>

                <!-- Execution Status -->
                <div v-if="data.isExecuting" class="execution-status">
                    <i class="pi pi-spin pi-spinner"></i>
                    <span>Processing...</span>
                </div>
            </div>

            <!-- Input Handle -->
            <Handle
                id="input"
                type="target"
                :position="Position.Left"
                class="input-handle"
            />

            <!-- Output Handles - Always visible -->
            <Handle
                id="passed"
                type="source"
                :position="Position.Right"
                :style="{ top: '40%' }"
                class="output-handle passed-handle"
            />
            <div v-if="isSelected" class="handle-label passed-label">
                passed
            </div>

            <Handle
                id="caught"
                type="source"
                :position="Position.Right"
                :style="{ top: '70%' }"
                class="output-handle caught-handle"
            />
            <div v-if="isSelected" class="handle-label caught-label">
                caught
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, inject } from "vue"
import { Handle, Position, useNode } from "@vue-flow/core"
import { NodeToolbar } from "@vue-flow/node-toolbar"
import ToggleSwitch from "primevue/toggleswitch"
import Tag from "primevue/tag"
import Button from "primevue/button"
import type { PluginNodeData } from "@/types/flow-types"
import { useNodeExecution } from "@/composables/useNodeExecution"

// Props - Define all Vue Flow props to prevent warnings
interface Props {
    id: string
    data: PluginNodeData
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

// Define emits for both Vue Flow event listeners and custom component events
const emit = defineEmits<{
    updateNodeInternals: [nodeId: string]
    enabledChange: [enabled: boolean]
}>()

// Get node information and selection state
const { node } = useNode()
const selectedNodeId = inject<any>("selectedNodeId")
const flowContext = inject<any>("flowContext")
const layoutDirection = inject<any>("layoutDirection", ref("LR"))

// Node execution functionality
const {
    executeSingleNode,
    executeFlowToNode,
    executeFlowFromNode,
    isExecuting,
} = useNodeExecution()

// Check if this node is selected
const isSelected = computed(() => {
    return selectedNodeId?.value === node.id
})

// Event handlers
const onEnabledChange = (enabled: boolean) => {
    emit("enabledChange", enabled)
}

// Utility functions
const formatNumber = (num: number): string => {
    return new Intl.NumberFormat().format(num)
}

const formatParameterKey = (key: string): string => {
    return key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())
}

const formatParameterValue = (value: any): string => {
    if (typeof value === "boolean") {
        return value ? "Yes" : "No"
    }
    if (typeof value === "number") {
        return value.toString()
    }
    if (typeof value === "string") {
        return value.length > 20 ? `${value.substring(0, 20)}...` : value
    }
    return String(value)
}

// Toolbar action handlers
const handleExecuteToHere = async () => {
    if (!flowContext?.selectedSource?.value) {
        console.error("No source selected for flow execution")
        return
    }

    const flowData = {
        nodes: flowContext.nodes.value,
        edges: flowContext.edges.value,
        layout: flowContext.getDirection(),
        source: flowContext.selectedSource.value,
    }

    await executeFlowToNode({
        source: flowContext.selectedSource.value,
        nodeId: props.id,
        flowData,
        tableName: props.data.table || "m3u_channels",
        limit: 100,
    })
}

const handleExecuteThisNode = async () => {
    if (!flowContext?.selectedSource?.value) {
        console.error("No source selected for flow execution")
        return
    }

    const flowData = {
        nodes: flowContext.nodes.value,
        edges: flowContext.edges.value,
        layout: flowContext.getDirection(),
        source: flowContext.selectedSource.value,
    }

    await executeSingleNode({
        source: flowContext.selectedSource.value,
        nodeId: props.id,
        flowData,
        tableName: props.data.table || "m3u_channels",
        limit: 100,
    })
}

const handleExecuteFromHere = async () => {
    if (!flowContext?.selectedSource?.value) {
        console.error("No source selected for flow execution")
        return
    }

    const flowData = {
        nodes: flowContext.nodes.value,
        edges: flowContext.edges.value,
        layout: flowContext.getDirection(),
        source: flowContext.selectedSource.value,
    }

    await executeFlowFromNode({
        source: flowContext.selectedSource.value,
        nodeId: props.id,
        flowData,
        tableName: props.data.table || "m3u_channels",
        limit: 100,
    })
}
</script>

<style scoped>
.plugin-node {
    background: var(--card-background);
    border: 2px solid #a855f7;
    border-radius: 0.5rem;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    min-width: 16rem;
    padding: 0.75rem;
    position: relative;
    transition: box-shadow 0.2s;
}

.plugin-node:hover {
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}

.plugin-node.disabled {
    background: var(--hover-color);
    border-color: var(--border-color);
    opacity: 0.7;
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
    color: #a855f7;
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

.plugin-info {
    text-align: center;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.plugin-name {
    font-weight: 500;
    color: var(--text-color);
    font-size: 0.875rem;
}

.plugin-type {
    display: flex;
    justify-content: center;
}

.parameters-section {
    background: var(--card-background);
    border-radius: 0.25rem;
    padding: 0.5rem;
    border: 1px solid var(--border-color);
}

.parameters-header {
    font-size: 0.75rem;
    font-weight: 500;
    color: #a855f7;
    margin-bottom: 0.25rem;
}

.parameters-list {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.parameter-item {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
}

.param-key {
    color: var(--text-color);
    font-weight: 500;
    opacity: 0.7;
}

.param-value {
    color: var(--text-color-secondary);
    font-size: 0.8rem;
    word-break: break-all;
}

.stats-section {
    background: var(--card-background);
    border-radius: 0.25rem;
    padding: 0.5rem;
    border: 1px solid var(--border-color);
}

.stat-row {
    display: flex;
    justify-content: space-between;
    gap: 0.5rem;
}

.stat-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    font-size: 0.75rem;
}

.stat-item.passed .stat-value {
    color: var(--primary-color);
    font-weight: 500;
}

.stat-item.caught .stat-value {
    color: #ef4444;
    font-weight: 500;
}

.stat-label {
    color: var(--text-color);
    opacity: 0.7;
}

.execution-status {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.75rem;
    color: #a855f7;
    background: var(--hover-color);
    border-radius: 0.25rem;
    padding: 0.25rem 0.5rem;
}

.input-handle {
    background: var(--border-color);
    border: 2px solid var(--card-background);
    width: 0.75rem;
    height: 0.75rem;
}

.input-handle:hover {
    background: var(--text-color);
    opacity: 0.8;
}

.output-handle {
    border: 2px solid var(--card-background);
    width: 0.75rem;
    height: 0.75rem;
}

.passed-handle {
    background: var(--primary-color);
}

.passed-handle:hover {
    background: var(--primary-color);
    opacity: 0.8;
}

.caught-handle {
    background-color: #ef4444;
    border-color: #ef4444;
}

.caught-handle:hover {
    background-color: #ef4444;
    opacity: 0.8;
}

.handle-label {
    @apply absolute right-0 text-xs font-medium pointer-events-none;
    @apply bg-white px-1 rounded shadow-sm border;
    transform: translateX(100%);
}

.passed-label {
    background-color: #10b981;
    color: white;
    padding: 0.125rem 0.375rem;
    border-radius: 0.25rem;
    font-size: 0.75rem;
    font-weight: 500;
    position: absolute;
    right: 1.5rem;
    top: 35%;
    white-space: nowrap;
    pointer-events: none;
    z-index: 10;
}

.caught-label {
    background-color: #ef4444;
    color: white;
    padding: 0.125rem 0.375rem;
    border-radius: 0.25rem;
    font-size: 0.75rem;
    font-weight: 500;
    position: absolute;
    right: 1.5rem;
    top: 65%;
    white-space: nowrap;
    pointer-events: none;
    z-index: 10;
}
</style>
