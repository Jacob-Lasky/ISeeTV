<template>
    <div class="rule-node-wrapper">
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

        <!-- Bottom Toolbar for View Data -->
        <NodeToolbar :is-visible="data.toolbarVisible" position="bottom">
            <div class="toolbar-buttons">
                <Button
                    icon="pi pi-table"
                    size="medium"
                    severity="help"
                    text
                    @click="handleViewData"
                    v-tooltip.bottom="'View data for this node'"
                />
            </div>
        </NodeToolbar>

        <div class="rule-node" :class="{ disabled: !data.enabled }">
            <div class="node-header">
                <i class="pi pi-filter"></i>
                <span class="node-title">{{ data.label }}</span>
                <ToggleSwitch
                    v-model="data.enabled"
                    class="ml-auto"
                    @change="onEnabledChange"
                />
            </div>

            <div class="node-body">
                <div class="rule-info">
                    <!-- Valid Tables -->
                    <div
                        class="rule-tables"
                        v-if="data.validation?.validSourceTables"
                    >
                        <span class="tables-label">Tables:</span>
                        <div class="table-tags">
                            <span
                                v-for="table in data.validation
                                    .validSourceTables"
                                :key="table"
                                class="table-tag"
                                :style="{
                                    backgroundColor: getTableColor(table),
                                }"
                            >
                                {{ table }}
                            </span>
                        </div>
                    </div>

                    <!-- Field and Pattern -->
                    <div class="rule-details">
                        <div class="detail-row">
                            <span class="detail-label">Field:</span>
                            <span class="field">{{ data.field }}</span>
                        </div>
                    </div>
                </div>

                <!-- Statistics Display -->
                <div v-if="data.stats" class="stats-section">
                    <div class="stat-row">
                        <div class="stat-item passed">
                            <span class="stat-label">{{ matchLabel }}:</span>
                            <span class="stat-value">{{
                                formatNumber(data.stats.passed)
                            }}</span>
                        </div>
                        <div class="stat-item caught">
                            <span class="stat-label">{{ noMatchLabel }}:</span>
                            <span class="stat-value">{{
                                formatNumber(data.stats.caught)
                            }}</span>
                        </div>
                    </div>
                </div>

                <!-- Execution Status -->
                <div v-if="data.isExecuting" class="execution-status">
                    <i class="pi pi-spin pi-spinner"></i>
                    <span>Filtering...</span>
                </div>

                <!-- Debug Info -->
                <!-- <div class="debug-info">
                <div class="debug-line">
                    <strong>Table:</strong> {{ data.table || 'undefined' }}
                </div>
                <div class="debug-line">
                    <strong>Color:</strong> {{ getTableColor(data.table) }}
                </div>
                <div class="debug-line">
                    <strong>Node ID:</strong> {{ id }}
                </div>
            </div> -->
            </div>

            <!-- Input Handle -->
            <Handle
                id="input"
                type="target"
                :position="inputHandlePosition"
                class="input-handle"
                :style="inputHandleStyle"
            />

            <!-- Output Handles -->
            <Handle
                id="passed"
                type="source"
                :position="passedHandlePosition"
                :style="passedHandleStyle"
                class="output-handle passed-handle"
            />
            <div v-if="isSelected" :class="passedLabelClass">
                {{ matchLabel }}
            </div>

            <Handle
                id="caught"
                type="source"
                :position="caughtHandlePosition"
                :style="caughtHandleStyle"
                class="output-handle caught-handle"
            />
            <div v-if="isSelected" :class="caughtLabelClass">
                {{ noMatchLabel }}
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, inject, ref } from "vue"
import { Handle, Position, useNode } from "@vue-flow/core"
import { NodeToolbar } from "@vue-flow/node-toolbar"
import ToggleSwitch from "primevue/toggleswitch"
import Tag from "primevue/tag"
import Button from "primevue/button"
import { useRouter } from "vue-router"
import type { RuleNodeData } from "@/types/flow-types"
import { useNodeExecution } from "@/composables/useNodeExecution"

// Props - Define all Vue Flow props to prevent warnings
interface Props {
    id: string
    data: RuleNodeData
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
const router = useRouter()

// Check if this node is selected
const isSelected = computed(() => {
    return selectedNodeId?.value === node.id
})

// Inject layout direction from FlowEditor
const layoutDirection = inject<any>("layoutDirection", ref("LR"))

// Node execution functionality
const {
    executeSingleNode,
    executeFlowToNode,
    executeFlowFromNode,
    isExecuting,
} = useNodeExecution()

// Computed properties for layout direction awareness
const inputHandlePosition = computed(() => {
    return layoutDirection.value === "LR" ? Position.Left : Position.Top
})

const inputHandleStyle = computed(() => {
    const tableColor = getTableColor(props.data.table)
    return {
        backgroundColor: tableColor,
        borderColor: tableColor,
    }
})

const passedHandlePosition = computed(() => {
    return layoutDirection.value === "LR" ? Position.Right : Position.Bottom
})

const caughtHandlePosition = computed(() => {
    return layoutDirection.value === "LR" ? Position.Right : Position.Bottom
})

const passedHandleStyle = computed(() => {
    if (layoutDirection.value === "LR") {
        return { top: "40%" }
    } else {
        return { left: "30%" }
    }
})

const caughtHandleStyle = computed(() => {
    if (layoutDirection.value === "LR") {
        return { top: "70%" }
    } else {
        return { left: "70%" }
    }
})

const passedLabelClass = computed(() => {
    const baseClass = "handle-label passed-label"
    if (layoutDirection.value === "LR") {
        return `${baseClass} handle-label-horizontal`
    } else {
        return `${baseClass} handle-label-vertical`
    }
})

const caughtLabelClass = computed(() => {
    const baseClass = "handle-label caught-label"
    if (layoutDirection.value === "LR") {
        return `${baseClass} handle-label-horizontal`
    } else {
        return `${baseClass} handle-label-vertical`
    }
})

// Event handlers
const onEnabledChange = (enabled: boolean) => {
    emit("enabledChange", enabled)
}

// Utility functions
const formatNumber = (num: number): string => {
    return num.toLocaleString()
}

const getTableColor = (table: string): string => {
    const colors = {
        m3u_channels: "#3b82f6",
        epg_channels: "#eab308",
        programs: "#8b5cf6",
    }
    return colors[table as keyof typeof colors] || "#6b7280"
}

const truncatePattern = (pattern: string): string => {
    if (!pattern) return ""
    return pattern.length > 30 ? pattern.substring(0, 30) + "..." : pattern
}

// Custom label computed properties
const matchLabel = computed(() => {
    return props.data.labels?.match || "Passed"
})

const noMatchLabel = computed(() => {
    return props.data.labels?.noMatch || "Caught"
})

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

const handleViewData = () => {
    const sourceName = flowContext?.selectedSource?.value
    const tableName = props.data.table || "m3u_channels"
    
    if (!sourceName) {
        console.error("No source selected for viewing data")
        return
    }
    
    // Navigate to TableViewer with source and table parameters
    router.push({
        name: "TableViewer",
        params: {
            sourceName: sourceName,
            tableName: tableName
        }
    })
}
</script>

<style scoped>
.rule-node {
    background: var(--card-background);
    border: 2px solid var(--secondary-color);
    border-radius: 0.5rem;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    min-width: 14rem;
    padding: 0.75rem;
    position: relative;
    transition: box-shadow 0.2s;
}

.rule-node:hover {
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}

.rule-node.disabled {
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
    color: var(--secondary-color);
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

.rule-info {
    text-align: center;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.rule-name {
    font-weight: 600;
    color: var(--text-color);
    margin-bottom: 8px;
}

.rule-table {
    margin-bottom: 0.5rem;
}

.tables-label {
    font-size: 0.75rem;
    color: var(--text-color-secondary);
    margin-bottom: 4px;
    display: block;
}

.table-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
}

.table-tag {
    font-size: 0.7rem;
    color: white;
    padding: 2px 6px;
    border-radius: 4px;
    font-weight: 500;
}

.rule-details {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.detail-row {
    display: flex;
    align-items: center;
    gap: 6px;
}

.detail-label {
    font-size: 0.75rem;
    color: var(--text-color-secondary);
    min-width: 45px;
    font-weight: 500;
}

.field {
    font-size: 0.8rem;
    color: var(--primary-color);
    font-weight: 500;
}

.pattern {
    font-size: 0.75rem;
    color: var(--text-color);
    font-family: "Courier New", monospace;
    background: var(--surface-100);
    padding: 2px 4px;
    border-radius: 3px;
    max-width: 150px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.rule-pattern {
    font-size: 0.75rem;
    background: var(--hover-color);
    border-radius: 0.25rem;
    padding: 0.25rem 0.5rem;
}

.rule-pattern code {
    color: var(--text-color);
    font-family: monospace;
    opacity: 0.8;
}

.rule-table {
    display: flex;
    justify-content: center;
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
    gap: 8px;
    margin-top: 8px;
    padding: 4px 8px;
    background: rgba(var(--primary-500), 0.1);
    border-radius: 4px;
    font-size: 12px;
    color: rgb(var(--primary-500));
}

.debug-info {
    margin-top: 8px;
    padding: 6px;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 4px;
    font-size: 10px;
    color: #ccc;
}

.debug-line {
    margin-bottom: 2px;
}

.debug-line:last-child {
    margin-bottom: 0;
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
    background-color: #10b981;
    border-color: #10b981;
}

.passed-handle:hover {
    background-color: #10b981;
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

.handle-label-vertical {
    writing-mode: vertical-rl;
    text-orientation: mixed;
    transform: translateX(-50%);
    left: 50%;
    top: -1.5rem;
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

/* Edge styling for passed/caught connections */
:global(.vue-flow__edge.passed-edge .vue-flow__edge-path) {
    stroke: #22c55e; /* success green */
    stroke-width: 2px;
}

:global(.vue-flow__edge.caught-edge .vue-flow__edge-path) {
    stroke: #ef4444; /* warning amber */
    stroke-width: 2px;
}

:global(.vue-flow__edge.passed-edge .vue-flow__edge-text) {
    fill: #22c55e;
    font-weight: 500;
}

:global(.vue-flow__edge.caught-edge .vue-flow__edge-text) {
    fill: #ef4444;
    font-weight: 500;
}

/* Handle styling to match edge colors */
.passed-handle {
    background-color: #22c55e !important;
    border-color: #16a34a !important;
}

.caught-handle {
    background-color: #ef4444 !important;
    border-color: #ef4444 !important;
}
</style>
