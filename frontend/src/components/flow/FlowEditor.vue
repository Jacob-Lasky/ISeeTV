<template>
    <div class="flow-editor" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
        <!-- Collapsible Sidebar -->
        <!-- Mobile backdrop -->
        <div
            v-if="!sidebarCollapsed"
            class="mobile-backdrop"
            :style="{
                position: 'fixed',
                top: '0',
                left: '0',
                width: '100vw',
                height: '100vh',
                background: 'var(--modal-overlay)',
                zIndex: '15',
                backdropFilter: 'blur(2px)',
            }"
            @click="toggleSidebar"
        ></div>

        <aside
            class="flow-sidebar"
            :class="{ collapsed: sidebarCollapsed }"
            :style="{
                position: 'fixed',
                left: '0',
                top: '0',
                width: '320px',
                height: '100vh',
                zIndex: '20',
                transform: sidebarCollapsed
                    ? 'translateX(-100%)'
                    : 'translateX(0)',
                transition: 'transform 0.3s ease',
                background: 'var(--card-background)',
                borderRight: '1px solid var(--border-color)',
                boxShadow: '2px 0 12px rgba(0, 0, 0, 0.25)',
                maxHeight: '100vh',
            }"
        >
            <!-- Sidebar Header -->
            <div class="sidebar-header">
                <h3 v-if="!sidebarCollapsed" class="sidebar-title">
                    Flow Tools
                </h3>
                <button
                    v-if="!sidebarCollapsed"
                    @click="toggleSidebar"
                    class="sidebar-close-btn"
                    title="Close sidebar"
                >
                    <i class="pi pi-times"></i>
                </button>
            </div>

            <!-- Sidebar Content -->
            <div v-if="!sidebarCollapsed" class="sidebar-content">
                <!-- Node Palette -->
                <div class="palette-section">
                    <h4 class="section-title">Node Palette</h4>
                    <p class="section-description">
                        Drag and drop to create workflows
                    </p>

                    <!-- Sources Section -->
                    <div class="palette-group">
                        <h5>Sources</h5>
                        <div v-if="loading.sources" class="loading-state">
                            <i class="pi pi-spin pi-spinner"></i>
                            <span>Loading sources...</span>
                        </div>
                        <div v-else-if="error.sources" class="error-state">
                            <i class="pi pi-exclamation-triangle"></i>
                            <span>{{ error.sources }}</span>
                            <button @click="fetchSources" class="retry-btn">
                                <i class="pi pi-refresh"></i> Retry
                            </button>
                        </div>
                        <div
                            v-else-if="availableSources.length === 0"
                            class="empty-state"
                        >
                            <i class="pi pi-info-circle"></i>
                            <span>No sources available</span>
                        </div>
                        <div
                            v-else
                            v-for="source in availableSources"
                            :key="source.name"
                            class="palette-node source-palette"
                            draggable="true"
                            @dragstart="onDragStart($event, 'source', source)"
                            :title="`${source.name} (${formatNumber(source.totalRecords)} records)`"
                        >
                            <div>
                                <i class="pi pi-database"></i>
                                <span>{{ source.name }}</span>
                            </div>
                            <small v-if="source.totalRecords"
                                >{{
                                    formatNumber(source.totalRecords)
                                }}
                                records</small
                            >
                        </div>
                    </div>

                    <!-- Rules Section -->
                    <div class="palette-group">
                        <h5>Rules</h5>
                        <div v-if="loading.rules" class="loading-state">
                            <i class="pi pi-spin pi-spinner"></i>
                            <span>Loading rules...</span>
                        </div>
                        <div v-else-if="error.rules" class="error-state">
                            <i class="pi pi-exclamation-triangle"></i>
                            <span>{{ error.rules }}</span>
                            <button @click="fetchRules" class="retry-btn">
                                <i class="pi pi-refresh"></i> Retry
                            </button>
                        </div>
                        <div
                            v-else-if="availableRules.length === 0"
                            class="empty-state"
                        >
                            <i class="pi pi-info-circle"></i>
                            <span>No rules available</span>
                        </div>
                        <div
                            v-else
                            v-for="rule in availableRules"
                            :key="rule.name || rule.id"
                            class="palette-node rule-palette"
                            draggable="true"
                            @dragstart="onDragStart($event, 'rule', rule)"
                            :title="
                                rule.description ||
                                `${rule.name} - ${rule.pattern}`
                            "
                        >
                            <div>
                                <i class="pi pi-filter"></i>
                                <span>{{ rule.name }}</span>
                            </div>
                            <small v-if="rule.table">{{ rule.table }}</small>
                        </div>
                    </div>

                    <!-- Plugins Section -->
                    <div class="palette-group">
                        <h5>Plugins</h5>
                        <div v-if="loading.plugins" class="loading-state">
                            <i class="pi pi-spin pi-spinner"></i>
                            <span>Loading plugins...</span>
                        </div>
                        <div v-else-if="error.plugins" class="error-state">
                            <i class="pi pi-exclamation-triangle"></i>
                            <span>{{ error.plugins }}</span>
                            <button @click="fetchPlugins" class="retry-btn">
                                <i class="pi pi-refresh"></i> Retry
                            </button>
                        </div>
                        <div
                            v-else-if="availablePlugins.length === 0"
                            class="empty-state"
                        >
                            <i class="pi pi-info-circle"></i>
                            <span>No plugins available</span>
                        </div>
                        <div
                            v-else
                            v-for="plugin in availablePlugins"
                            :key="plugin.name || plugin.type"
                            class="palette-node plugin-palette"
                            draggable="true"
                            @dragstart="onDragStart($event, 'plugin', plugin)"
                            :title="
                                plugin.description ||
                                `${plugin.name} v${plugin.version}`
                            "
                        >
                            <div>
                                <i class="pi pi-cog"></i>
                                <span>{{ plugin.name }}</span>
                            </div>
                            <small v-if="plugin.version"
                                >v{{ plugin.version }}</small
                            >
                        </div>
                    </div>

                    <!-- Streams Section -->
                    <div class="palette-group">
                        <h5>Streams</h5>
                        <div
                            class="palette-node stream-palette accepted"
                            draggable="true"
                            @dragstart="
                                onDragStart($event, 'stream', {
                                    type: 'accepted',
                                })
                            "
                        >
                            <i class="pi pi-check-circle"></i>
                            <span>Accepted</span>
                        </div>
                        <div
                            class="palette-node stream-palette rejected"
                            draggable="true"
                            @dragstart="
                                onDragStart($event, 'stream', {
                                    type: 'rejected',
                                })
                            "
                        >
                            <i class="pi pi-times-circle"></i>
                            <span>Rejected</span>
                        </div>
                    </div>
                </div>

                <!-- Flow Statistics -->
                <div v-if="flowStats" class="stats-section">
                    <h4 class="section-title">Flow Statistics</h4>
                    <div class="stats-grid">
                        <div class="stat-item">
                            <span class="stat-label">Nodes:</span>
                            <span class="stat-value">{{ nodes.length }}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Connections:</span>
                            <span class="stat-value">{{ edges.length }}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Processed:</span>
                            <span class="stat-value">{{
                                formatNumber(flowStats.totalProcessed)
                            }}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Accepted:</span>
                            <span class="stat-value">{{
                                formatNumber(flowStats.totalAccepted)
                            }}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Rejected:</span>
                            <span class="stat-value">{{
                                formatNumber(flowStats.totalRejected)
                            }}</span>
                        </div>
                    </div>
                </div>
            </div>
        </aside>

        <!-- Main Content Area -->
        <div class="flow-main">
            <!-- Toolbar -->
            <div class="flow-toolbar">
                <div class="toolbar-section">
                    <Button
                        v-if="sidebarCollapsed"
                        icon="pi pi-bars"
                        class="mobile-palette-toggle"
                        severity="secondary"
                        size="small"
                        @click="toggleSidebar"
                        aria-label="Show Node Palette"
                    />

                    <!-- Source Selection -->
                    <div class="source-selector">
                        <label for="source-select" class="source-label"
                            >Source:</label
                        >
                        <Select
                            id="source-select"
                            v-model="selectedSource"
                            :options="sourceOptions"
                            option-label="name"
                            option-value="name"
                            placeholder="Select source"
                            class="source-dropdown"
                            :disabled="loading.sources"
                        />
                    </div>

                    <Button
                        icon="pi pi-upload"
                        label="Load Flow"
                        severity="info"
                        size="small"
                        :loading="loading.flow"
                        :disabled="!selectedSource"
                        @click="loadFlow"
                        title="Load flow for selected source"
                    />
                    <Button
                        icon="pi pi-play"
                        label="Execute Flow"
                        severity="success"
                        size="small"
                        :loading="isExecuting"
                        :disabled="!isValidFlow"
                        @click="executeFlow"
                    />
                    <Button
                        icon="pi pi-save"
                        label="Save Flow"
                        severity="primary"
                        size="small"
                        :loading="saving"
                        :disabled="!selectedSource"
                        @click="saveFlow"
                        title="Save flow for selected source"
                    />
                    <Button
                        icon="pi pi-sitemap"
                        label="Auto Layout"
                        severity="info"
                        size="small"
                        :disabled="nodes.length === 0"
                        @click="applyAutoLayout"
                        title="Organize nodes automatically"
                    />
                    <Button
                        icon="pi pi-refresh"
                        label="Clear"
                        severity="secondary"
                        size="small"
                        @click="clearFlow"
                    />
                </div>
            </div>

            <!-- Flow Canvas -->
            <div class="flow-canvas">
                <VueFlow
                    v-model:nodes="nodes"
                    v-model:edges="edges"
                    :node-types="nodeTypes"
                    class="vue-flow"
                    @drop="onDrop"
                    @dragover="onDragOver"
                    @connect="onConnect"
                    @edge-update="onEdgeUpdate"
                    @node-click="onNodeClick"
                    @pane-click="onPaneClick"
                >
                    <!-- Core VueFlow functionality only -->
                    <!-- Background, Controls, and MiniMap require separate packages -->
                </VueFlow>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, markRaw, provide, watch } from "vue"
import { VueFlow, useVueFlow } from "@vue-flow/core"
import "@vue-flow/core/dist/style.css"
import Button from "primevue/button"
import Select from "primevue/select"
import { useToast } from "primevue/usetoast"

// Import node components
import SourceNode from "./nodes/SourceNode.vue"
import RuleNode from "./nodes/RuleNode.vue"
import PluginNode from "./nodes/PluginNode.vue"
import StreamNode from "./nodes/StreamNode.vue"

// Import types
import type {
    FlowNode,
    FlowEdge,
    FlowNodeType,
    SourceNodeData,
    RuleNodeData,
    PluginNodeData,
    StreamNodeData,
    ValidationResult,
} from "@/types/flow-types"
import type {
    Source,
    IngestionRule,
    BackendPlugin,
    RulesResponse,
    PluginsResponse,
} from "@/types/types"
import { BackendDataTransformer } from "@/types/types"
import { validateConnection } from "@/types/flow-types"
import { useLayout } from "@/composables/useLayout"

// Vue Flow composable
const { addNodes, addEdges, removeNodes, removeEdges, getConnectedEdges } =
    useVueFlow()

// Layout composable for auto-layout
const { layout, getDirection, setDirection } = useLayout()

// Toast for notifications
const toast = useToast()

// Reactive state
const nodes = ref<FlowNode[]>([])
const edges = ref<FlowEdge[]>([])
const isExecuting = ref(false)
const saving = ref(false)
const sidebarCollapsed = ref(false)
const draggedItem = ref<any>(null)
const selectedNodeId = ref<string | null>(null)

// Source selection and flow management
const selectedSource = ref<string | null>(null)
const sourceOptions = ref<Source[]>([])

// Provide selection state to node components
provide("selectedNodeId", selectedNodeId)

// Provide flow context for node execution
provide("flowContext", {
    selectedSource,
    nodes,
    edges,
    getDirection,
})

// Node types registration
const nodeTypes = {
    source: markRaw(SourceNode),
    rule: markRaw(RuleNode),
    plugin: markRaw(PluginNode),
    stream: markRaw(StreamNode),
}

// Real data from backend APIs
const availableSources = ref([])
const availableRules = ref([])
const availablePlugins = ref([])
const loading = ref({
    sources: false,
    rules: false,
    plugins: false,
    flow: false,
})
const error = ref({
    sources: null,
    rules: null,
    plugins: null,
})

// Computed properties
const isValidFlow = computed(() => {
    const hasSource = nodes.value.some((node) => node.type === "source")
    const hasStream = nodes.value.some((node) => node.type === "stream")
    return hasSource && hasStream && edges.value.length > 0
})

const flowStats = computed(() => {
    if (nodes.value.length === 0) return null

    const totalProcessed = nodes.value.reduce((sum, node) => {
        return sum + (node.data.stats?.processed || 0)
    }, 0)

    const acceptedNodes = nodes.value.filter(
        (node) =>
            node.type === "stream" &&
            (node.data as StreamNodeData).streamType === "accepted"
    )
    const rejectedNodes = nodes.value.filter(
        (node) =>
            node.type === "stream" &&
            (node.data as StreamNodeData).streamType === "rejected"
    )

    const totalAccepted = acceptedNodes.reduce((sum, node) => {
        return sum + (node.data.stats?.processed || 0)
    }, 0)

    const totalRejected = rejectedNodes.reduce((sum, node) => {
        return sum + (node.data.stats?.processed || 0)
    }, 0)

    return {
        totalProcessed,
        totalAccepted,
        totalRejected,
    }
})

// Event handlers
const onDragStart = (event: DragEvent, nodeType: string, data: any) => {
    if (!event.dataTransfer) return

    draggedItem.value = { nodeType, data }
    event.dataTransfer.setData(
        "application/vueflow",
        JSON.stringify({ nodeType, data })
    )
    event.dataTransfer.effectAllowed = "move"
}

const onDragOver = (event: DragEvent) => {
    event.preventDefault()
    if (event.dataTransfer) {
        event.dataTransfer.dropEffect = "move"
    }
}

const onDrop = (event: DragEvent) => {
    event.preventDefault()

    if (!draggedItem.value) return

    const { nodeType, data } = draggedItem.value
    const position = {
        x: event.offsetX - 100,
        y: event.offsetY - 50,
    }

    createNode(nodeType, data, position)
    draggedItem.value = null
}

const onConnect = (connection: any) => {
    console.log("Connection attempt:", {
        source: connection.source,
        target: connection.target,
        sourceHandle: connection.sourceHandle,
        targetHandle: connection.targetHandle,
    })

    // Find source and target nodes for validation
    const sourceNode = nodes.value.find((n) => n.id === connection.source)
    const targetNode = nodes.value.find((n) => n.id === connection.target)

    console.log("Source node:", {
        id: sourceNode?.id,
        type: sourceNode?.type,
        table: sourceNode?.data?.table,
        data: sourceNode?.data,
    })
    console.log("Target node:", {
        id: targetNode?.id,
        type: targetNode?.type,
        table: targetNode?.data?.table,
        data: targetNode?.data,
    })

    if (!sourceNode || !targetNode) {
        toast.add({
            severity: "error",
            summary: "Connection Failed",
            detail: "Could not find source or target node",
            life: 3000,
        })
        return
    }

    // Validate the connection
    const validationResult = validateConnection(
        sourceNode as FlowNode,
        targetNode as FlowNode,
        connection.sourceHandle,
        connection.targetHandle
    )

    console.log("Validation result:", validationResult)

    if (!validationResult.isValid) {
        toast.add({
            severity: "warn",
            summary: "Invalid Connection",
            detail: validationResult.reason || "This connection is not allowed",
            life: 4000,
        })
        return
    }

    // Determine edge CSS class based on source handle type
    let edgeClass = ""
    if (connection.sourceHandle === "passed") {
        edgeClass = "passed-edge"
    } else if (connection.sourceHandle === "caught") {
        edgeClass = "caught-edge"
    }

    const edge: FlowEdge = {
        id: `edge-${Date.now()}`,
        source: connection.source,
        target: connection.target,
        sourceHandle: connection.sourceHandle,
        targetHandle: connection.targetHandle,
        class: edgeClass,
        data: {
            pathType: connection.sourceHandle || "default",
            stats: { recordCount: 0, percentage: 0 },
        },
    }

    addEdges([edge])
}

const onEdgeUpdate = (oldEdge: FlowEdge, newConnection: any) => {
    removeEdges([oldEdge])
    onConnect(newConnection)
}

// Node selection handlers
const onNodeClick = (event: any) => {
    // Toggle selection: if clicking the same node, deselect it
    if (selectedNodeId.value === event.node.id) {
        selectedNodeId.value = null
    } else {
        selectedNodeId.value = event.node.id
    }
}

const onPaneClick = () => {
    // Deselect node when clicking on empty canvas
    selectedNodeId.value = null
}

// Node creation functions
const createNode = (
    nodeType: string,
    data: any,
    position: { x: number; y: number }
) => {
    const nodeId = `${nodeType}-${Date.now()}`

    let nodeData: any

    switch (nodeType) {
        case "source":
            nodeData = {
                label: `Source: ${data.name}`,
                sourceName: data.name,
                totalRecords: data.totalRecords,
                tables: [
                    {
                        name: "m3u_channels",
                        recordCount: 0,
                        description: "Channel data",
                    },
                    {
                        name: "epg_channels",
                        recordCount: 0,
                        description: "EPG channel data",
                    },
                    {
                        name: "programs",
                        recordCount: 0,
                        description: "Program guide data",
                    },
                ],
                stats: { processed: 0, passed: 0, caught: 0 },
            } as SourceNodeData
            break

        case "rule":
            const validTables = getValidTablesForRule(data)
            // Get table from multiple possible sources in order of preference
            let ruleTable = "unknown"
            if (
                data.tables &&
                Array.isArray(data.tables) &&
                data.tables.length > 0
            ) {
                // From backend rules.json format
                ruleTable = data.tables[0]
            } else if (
                validTables &&
                validTables.length > 0 &&
                validTables.length < 3 && // Not the fallback array
                !(
                    validTables.length === 3 &&
                    validTables.includes("m3u_channels") &&
                    validTables.includes("epg_channels") &&
                    validTables.includes("programs")
                )
            ) {
                // From computed valid tables (if not fallback)
                ruleTable = validTables[0]
            } else if (data.field) {
                // Infer from field name as fallback
                if (
                    data.field === "stream_mode" ||
                    data.field === "tvg_id" ||
                    data.field === "name" ||
                    data.field === "group" ||
                    data.field === "stream_url"
                ) {
                    ruleTable = "m3u_channels"
                } else if (
                    data.field === "title" ||
                    data.field === "description" ||
                    data.field === "start_time"
                ) {
                    ruleTable = "programs"
                } else if (
                    data.field === "channel_id" ||
                    data.field === "display_name"
                ) {
                    ruleTable = "epg_channels"
                }
            }

            console.log("Creating rule node:", {
                name: data.name,
                field: data.field,
                originalTables: data.tables,
                validTables: validTables,
                assignedTable: ruleTable,
            })

            nodeData = {
                label: data.name,
                ruleName: data.name,
                pattern: data.regex, // Use 'regex' field from rules.json
                field: data.field,
                table: ruleTable,
                enabled: true,
                stats: { processed: 0, passed: 0, caught: 0 },
                validation: {
                    validSourceTables: [ruleTable], // Use the actual assigned table
                },
            } as RuleNodeData
            break

        case "plugin":
            const validPluginTables = getValidTablesForPlugin(data)
            nodeData = {
                label: data.name,
                pluginName: data.name,
                pluginType: data.type,
                parameters: data.parameters,
                enabled: true,
                stats: { processed: 0, passed: 0, caught: 0 },
                validation: {
                    validSourceTables: validPluginTables,
                },
            } as PluginNodeData
            break

        case "stream":
            nodeData = {
                label: `${data.type.charAt(0).toUpperCase() + data.type.slice(1)} Stream`,
                streamType: data.type,
                description: `Records ${data.type} by the flow`,
                stats: { processed: 0, passed: 0, caught: 0 },
            } as StreamNodeData
            break

        default:
            return
    }

    const newNode: FlowNode = {
        id: nodeId,
        type: nodeType as FlowNodeType,
        position,
        data: nodeData,
    }

    addNodes([newNode])
}

// Table compatibility helper functions
const getValidTablesForRule = (ruleData: any): string[] => {
    // After transformation, the rule data has a single 'table' field instead of 'tables' array
    // We need to access the original backend data or reconstruct from the single table
    if (ruleData.table && ruleData.table !== "unknown") {
        return [ruleData.table]
    }
    // Fallback only if no table information is available
    return ["m3u_channels", "epg_channels", "programs"]
}

const getValidTablesForPlugin = (pluginData: any): string[] => {
    // For now, plugins can process all table types unless specified otherwise
    // This could be enhanced based on plugin type/configuration
    const pluginName = (pluginData.name || "").toLowerCase()

    // Channel program filter specifically works with channels and programs
    if (pluginName.includes("channel_program")) {
        return ["m3u_channels", "programs"]
    }

    // Default: allow all tables
    return ["m3u_channels", "epg_channels", "programs"]
}

// Flow operations
const executeFlow = async () => {
    if (!isValidFlow.value) {
        toast.add({
            severity: "warn",
            summary: "Invalid Flow",
            detail: "Flow must have at least one source, one stream, and connections between them.",
            life: 3000,
        })
        return
    }

    if (!selectedSource.value) {
        toast.add({
            severity: "warn",
            summary: "No Source Selected",
            detail: "Please select a source to execute the flow against.",
            life: 3000,
        })
        return
    }

    isExecuting.value = true

    try {
        // Convert visual flow to backend format
        const flowConfig = convertFlowToBackendFormat()

        // Execute flow on real data
        await executeFlowOnRealData(flowConfig)

        toast.add({
            severity: "success",
            summary: "Flow Executed",
            detail: "Flow has been executed successfully with real data!",
            life: 3000,
        })
    } catch (error) {
        console.error("Flow execution error:", error)
        toast.add({
            severity: "error",
            summary: "Execution Failed",
            detail:
                error instanceof Error
                    ? error.message
                    : "Failed to execute flow. Please check your configuration.",
            life: 5000,
        })
    } finally {
        isExecuting.value = false
    }
}

const saveFlow = async () => {
    if (!selectedSource.value) {
        toast.add({
            severity: "warn",
            summary: "No Source Selected",
            detail: "Please select a source before saving the flow.",
            life: 3000,
        })
        return
    }

    try {
        saving.value = true

        // Apply auto-layout to organize nodes before saving
        if (nodes.value.length > 0) {
            const layoutedNodes = layout(
                nodes.value,
                edges.value,
                getDirection()
            )
            nodes.value = layoutedNodes

            // Small delay to allow Vue Flow to update positions
            await new Promise((resolve) => setTimeout(resolve, 100))
        }

        // Prepare flow data for backend
        const flowData = {
            nodes: nodes.value,
            edges: edges.value,
            layout: getDirection(),
            source: selectedSource.value,
            timestamp: new Date().toISOString(),
        }

        // Send POST request to backend
        const response = await fetch(`/api/${selectedSource.value}/flows`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(flowData),
        })

        if (!response.ok) {
            throw new Error(`Failed to save flow: ${response.statusText}`)
        }

        toast.add({
            severity: "success",
            summary: "Flow Saved",
            detail: `Flow configuration saved for source '${selectedSource.value}' and auto-organized!`,
            life: 3000,
        })
    } catch (error) {
        console.error("Save flow error:", error)
        toast.add({
            severity: "error",
            summary: "Save Failed",
            detail: "Failed to save flow configuration.",
            life: 3000,
        })
    } finally {
        saving.value = false
    }
}

const loadFlow = async () => {
    if (!selectedSource.value) {
        toast.add({
            severity: "warn",
            summary: "No Source Selected",
            detail: "Please select a source before loading a flow.",
            life: 3000,
        })
        return
    }

    try {
        loading.value.flow = true

        // Fetch flow from backend
        const response = await fetch(`/api/${selectedSource.value}/flows`)

        if (!response.ok) {
            if (response.status === 404) {
                toast.add({
                    severity: "info",
                    summary: "No Flow Found",
                    detail: `No saved flow found for source '${selectedSource.value}'`,
                    life: 3000,
                })
                return
            }
            throw new Error(`Failed to load flow: ${response.statusText}`)
        }

        const flowData = await response.json()

        // Clear current flow
        nodes.value = []
        edges.value = []

        // Small delay to ensure Vue Flow is ready
        await new Promise((resolve) => setTimeout(resolve, 100))

        // Load nodes and edges
        if (flowData.nodes) {
            nodes.value = flowData.nodes
        }
        if (flowData.edges) {
            edges.value = flowData.edges
        }
        if (flowData.layout) {
            setDirection(flowData.layout)
        }

        toast.add({
            severity: "success",
            summary: "Flow Loaded",
            detail: `Flow configuration loaded for source '${selectedSource.value}'.`,
            life: 3000,
        })
    } catch (error) {
        console.error("Load flow error:", error)
        toast.add({
            severity: "error",
            summary: "Load Failed",
            detail: "Failed to load flow configuration.",
            life: 3000,
        })
    } finally {
        loading.value.flow = false
    }
}

/**
 * Apply auto-layout to organize nodes without saving
 */
const applyAutoLayout = async () => {
    if (nodes.value.length === 0) {
        toast.add({
            severity: "warn",
            summary: "No Nodes",
            detail: "Add some nodes to the flow before applying layout.",
            life: 3000,
        })
        return
    }

    try {
        const layoutedNodes = layout(nodes.value, edges.value, getDirection())
        nodes.value = layoutedNodes

        toast.add({
            severity: "success",
            summary: "Layout Applied",
            detail: `Nodes organized using ${getDirection() === "LR" ? "horizontal" : "vertical"} layout.`,
            life: 3000,
        })
    } catch (error) {
        console.error("Layout error:", error)
        toast.add({
            severity: "error",
            summary: "Layout Failed",
            detail: "Failed to apply auto-layout to nodes.",
            life: 3000,
        })
    }
}

/**
 * Toggle layout direction between horizontal (LR) and vertical (TB)
 */
const toggleLayoutDirection = () => {
    const newDirection = getDirection() === "LR" ? "TB" : "LR"
    setDirection(newDirection)

    // Apply new layout direction if there are nodes
    if (nodes.value.length > 0) {
        applyAutoLayout()
    } else {
        toast.add({
            severity: "info",
            summary: "Direction Changed",
            detail: `Layout direction set to ${newDirection === "LR" ? "horizontal" : "vertical"}. Add nodes to see the effect.`,
            life: 3000,
        })
    }
}

const clearFlow = () => {
    nodes.value = []
    edges.value = []

    toast.add({
        severity: "info",
        summary: "Flow Cleared",
        detail: "All nodes and connections have been removed.",
        life: 3000,
    })
}

// Flow conversion and execution functions
const convertFlowToBackendFormat = () => {
    // Convert visual flow nodes and edges to backend flow configuration format
    const flowConfig = {
        sources: [] as any[],
        rules: [] as any[],
        streams: [] as any[],
        connections: [] as any[],
    }

    // Process nodes
    nodes.value.forEach((node) => {
        switch (node.type) {
            case "source":
                flowConfig.sources.push({
                    id: node.id,
                    name: node.data.label,
                    type: node.data.type || "unknown",
                    url: node.data.url || "",
                    enabled: node.data.enabled !== false,
                })
                break
            case "rule":
                flowConfig.rules.push({
                    id: node.id,
                    name: node.data.label,
                    pattern: node.data.pattern || "",
                    table: node.data.table || "m3u_channels",
                    enabled: node.data.enabled !== false,
                    action: node.data.action || "filter",
                })
                break
            case "stream":
                flowConfig.streams.push({
                    id: node.id,
                    name: node.data.label,
                    enabled: node.data.enabled !== false,
                })
                break
        }
    })

    // Process edges as connections
    edges.value.forEach((edge) => {
        flowConfig.connections.push({
            from: edge.source,
            to: edge.target,
            type: edge.type || "default",
        })
    })

    return flowConfig
}

const executeFlowOnRealData = async (flowConfig: any) => {
    if (!selectedSource.value) {
        throw new Error("No source selected for execution")
    }

    // Determine table name based on flow configuration
    const tableNames = ["m3u_channels", "epg_channels", "programs"]
    const tableName =
        tableNames.find((table) =>
            flowConfig.rules.some((rule: any) => rule.table === table)
        ) || "m3u_channels"

    try {
        const response = await fetch(
            `/api/${selectedSource.value}/flows/execute?table_name=${tableName}&limit=500`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(flowConfig),
            }
        )

        if (!response.ok) {
            const errorData = await response
                .json()
                .catch(() => ({ detail: "Unknown error" }))
            throw new Error(
                errorData.detail ||
                    `HTTP ${response.status}: ${response.statusText}`
            )
        }

        const result = await response.json()

        if (!result.success) {
            throw new Error(result.message || "Flow execution failed")
        }

        // Update nodes with real execution results
        updateNodesWithExecutionResults(result.data)

        return result.data
    } catch (error) {
        console.error("Flow execution API error:", error)
        throw error
    }
}

const updateNodesWithExecutionResults = (executionData: any) => {
    const { execution_results } = executionData

    if (!execution_results) {
        console.warn("No execution results found in response")
        return
    }

    const { stats, accepted, rejected } = execution_results

    // Update all nodes with execution timestamp
    const executionTime = new Date()

    nodes.value.forEach((node) => {
        if (node.data.stats) {
            // Update with real execution data
            node.data.stats.processed = stats.total || 0
            node.data.stats.passed = stats.accepted || 0
            node.data.stats.caught = stats.rejected || 0
            node.data.lastExecuted = executionTime

            // Add tracing information if available
            if (stats.with_trace > 0) {
                node.data.stats.with_trace = stats.with_trace
            }
            if (stats.with_filter_reasons > 0) {
                node.data.stats.with_filter_reasons = stats.with_filter_reasons
            }
        }
    })

    // Store detailed results for potential inspection
    if (accepted?.length > 0 || rejected?.length > 0) {
        console.log("Flow execution results:", {
            accepted: accepted?.length || 0,
            rejected: rejected?.length || 0,
            sample_accepted: accepted?.slice(0, 3),
            sample_rejected: rejected?.slice(0, 3),
        })
    }
}

// Sidebar management
const toggleSidebar = () => {
    sidebarCollapsed.value = !sidebarCollapsed.value
}

// Utility functions
const formatNumber = (num: number): string => {
    return new Intl.NumberFormat().format(num)
}

// Data fetching functions
const fetchSources = async () => {
    loading.value.sources = true
    try {
        const response = await fetch("/api/sources")
        if (!response.ok) {
            throw new Error(`Failed to fetch sources: ${response.statusText}`)
        }
        const sources: Source[] = await response.json()

        // Transform backend data to frontend format using atomic transformer
        availableSources.value = sources.map((source) =>
            BackendDataTransformer.transformSource(source)
        )

        // Populate source options for dropdown
        sourceOptions.value = sources
    } catch (error) {
        console.error("Error fetching sources:", error)
        toast.add({
            severity: "error",
            summary: "Error",
            detail: "Failed to fetch sources from backend",
            life: 5000,
        })
    } finally {
        loading.value.sources = false
    }
}

const fetchRules = async () => {
    loading.value.rules = true
    try {
        const response = await fetch("/api/rules")
        if (!response.ok) {
            throw new Error(`Failed to fetch rules: ${response.statusText}`)
        }
        const data: RulesResponse = await response.json()

        // Transform backend data to frontend format using atomic transformer
        availableRules.value = data.rules.map((rule) =>
            BackendDataTransformer.transformRule(rule)
        )
    } catch (error) {
        console.error("Error fetching rules:", error)
        toast.add({
            severity: "error",
            summary: "Error",
            detail: "Failed to fetch rules from backend",
            life: 5000,
        })
        availableRules.value = []
    } finally {
        loading.value.rules = false
    }
}

const fetchPlugins = async () => {
    loading.value.plugins = true
    try {
        const response = await fetch("/api/plugins")
        if (!response.ok) {
            throw new Error(`Failed to fetch plugins: ${response.statusText}`)
        }
        const data: PluginsResponse = await response.json()

        // Transform backend data to frontend format using atomic transformer
        availablePlugins.value = Object.entries(data.plugins || {}).map(
            ([key, plugin]) =>
                BackendDataTransformer.transformPlugin(key, plugin)
        )
    } catch (error) {
        console.error("Error fetching plugins:", error)
        toast.add({
            severity: "error",
            summary: "Error",
            detail: "Failed to fetch plugins from backend",
            life: 5000,
        })
        availablePlugins.value = []
    } finally {
        loading.value.plugins = false
    }
}

// Load all data
const loadAllData = async () => {
    await Promise.all([fetchSources(), fetchRules(), fetchPlugins()])
}

// Auto-load flow when source changes
watch(selectedSource, async (newSource, oldSource) => {
    // Only auto-load if:
    // 1. A source is actually selected (not null)
    // 2. The source actually changed (not initial mount)
    // 3. We're not currently saving (to avoid conflicts)
    if (newSource && newSource !== oldSource && !saving.value) {
        try {
            const response = await fetch(`/api/${newSource}/flows`)
            if (response.ok) {
                const flowData = await response.json()

                // Clear existing flow
                nodes.value = []
                edges.value = []

                // Load the saved flow
                if (flowData.nodes) {
                    nodes.value = flowData.nodes
                }
                if (flowData.edges) {
                    edges.value = flowData.edges
                }

                // Apply layout if saved
                if (flowData.layout) {
                    await layout(nodes.value, edges.value, flowData.layout)
                }

                toast.add({
                    severity: "success",
                    summary: "Flow Loaded",
                    detail: `Automatically loaded saved flow for ${newSource}`,
                    life: 3000,
                })
            }
            // If no saved flow exists, that's fine - just start with empty flow
        } catch (error) {
            console.error("Error auto-loading flow:", error)
            // Don't show error toast for auto-load failures - it's not user-initiated
        }
    }
})

// Lifecycle
onMounted(async () => {
    // Load real data from backend
    await loadAllData()

    // Start with empty flow - let users build their own
    nodes.value = []
    edges.value = []
})
</script>

<style scoped>
.flow-editor {
    display: flex;
    height: 100vh;
    background: var(--surface-ground);
    color: var(--text-color);
}

/* Sidebar Styles */
.flow-sidebar {
    width: 320px;
    background: var(--surface-card);
    border-right: 1px solid var(--surface-border);
    display: flex;
    flex-direction: column;
    transition: width 0.3s ease;
    z-index: 10;
}

.flow-sidebar.collapsed {
    width: 48px;
}

.sidebar-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem;
    border-bottom: 1px solid var(--border-color);
    background: var(--card-background);
}

.sidebar-close-btn {
    background: none;
    border: none;
    color: var(--text-color);
    cursor: pointer;
    padding: 0.5rem;
    border-radius: 0.25rem;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background-color 0.2s;
}

.sidebar-close-btn:hover {
    background: var(--hover-color);
}

.sidebar-close-btn i {
    font-size: 1rem;
}

.sidebar-toggle {
    min-width: 32px;
    height: 32px;
}

.sidebar-title {
    margin: 0 0 0 0.75rem;
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--text-color);
}

.sidebar-content {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
}

/* Palette Section */
.palette-section {
    margin-bottom: 2rem;
}

.section-title {
    margin: 0 0 0.5rem 0;
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-color);
}

.section-description {
    margin: 0 0 1rem 0;
    font-size: 0.875rem;
    color: var(--text-color-secondary);
    line-height: 1.4;
}

.palette-group {
    margin-bottom: 1.5rem;
}

.palette-group h5 {
    margin: 0 0 0.75rem 0;
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text-color-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.palette-node {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
    padding: 8px 12px;
    margin: 4px 0;
    background: var(--surface-card);
    border: 1px solid var(--surface-border);
    border-radius: 6px;
    cursor: grab;
    transition: all 0.2s ease;
    font-size: 0.9rem;
    width: 100%;
    box-sizing: border-box;
}

.palette-node:hover {
    background: var(--surface-hover);
    border-color: var(--primary-color);
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.palette-node:active {
    cursor: grabbing;
    transform: translateY(0);
}

.palette-node > div:first-child {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
}

.palette-node small {
    color: var(--text-color-secondary);
    font-size: 0.75rem;
    margin-left: 24px;
    line-height: 1.2;
}

/* Loading, error, and empty states */
.loading-state,
.error-state,
.empty-state {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px;
    margin: 8px 0;
    border-radius: 6px;
    font-size: 0.85rem;
    text-align: center;
}

.loading-state {
    background: var(--surface-card);
    color: var(--text-color-secondary);
    border: 1px solid var(--surface-border);
}

.error-state {
    background: var(--red-50);
    color: var(--red-700);
    border: 1px solid var(--red-200);
    flex-direction: column;
    gap: 8px;
}

.empty-state {
    background: var(--surface-100);
    color: var(--text-color-secondary);
    border: 1px solid var(--surface-border);
}

.retry-btn {
    padding: 4px 8px;
    background: var(--red-600);
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.75rem;
    display: flex;
    align-items: center;
    gap: 4px;
    transition: background-color 0.2s ease;
}

.retry-btn:hover {
    background: var(--red-700);
}

/* Dark mode support for states */
:global(.p-dark) .loading-state {
    background: var(--surface-card) !important;
    color: var(--text-color-secondary) !important;
    border-color: var(--surface-border) !important;
}

:global(.p-dark) .error-state {
    background: rgba(239, 68, 68, 0.1) !important;
    color: var(--red-400) !important;
    border-color: var(--red-800) !important;
}

:global(.p-dark) .empty-state {
    background: var(--surface-section) !important;
    color: var(--text-color-secondary) !important;
    border-color: var(--surface-border) !important;
}

.palette-node i {
    font-size: 1rem;
    width: 16px;
    text-align: center;
}

/* Node type specific colors */
.source-palette {
    border-left: 4px solid #10b981;
}

.source-palette i {
    color: #10b981;
}

.rule-palette {
    border-left: 4px solid #3b82f6;
}

.rule-palette i {
    color: #3b82f6;
}

.plugin-palette {
    border-left: 4px solid #8b5cf6;
}

.plugin-palette i {
    color: #8b5cf6;
}

.stream-palette.accepted {
    border-left: 4px solid #10b981;
}

.stream-palette.accepted i {
    color: #10b981;
}

.stream-palette.rejected {
    border-left: 4px solid #ef4444;
}

.stream-palette.rejected i {
    color: #ef4444;
}

/* Stats Section */
.stats-section {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid var(--surface-border);
}

.stats-grid {
    display: grid;
    gap: 0.75rem;
}

.stat-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 0.75rem;
    background: var(--surface-section);
    border-radius: 6px;
    border: 1px solid var(--surface-border);
}

.stat-label {
    font-size: 0.875rem;
    color: var(--text-color-secondary);
    font-weight: 500;
}

.stat-value {
    font-size: 0.875rem;
    color: var(--text-color);
    font-weight: 600;
}

/* Main Content Area */
.flow-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.flow-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem;
    background: var(--surface-card);
    border-bottom: 1px solid var(--surface-border);
    gap: 0.5rem;
    flex-wrap: wrap;
}

.toolbar-section {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
}

.source-selector {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-right: 1rem;
}

.source-label {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-color);
    white-space: nowrap;
}

.source-dropdown {
    min-width: 150px;
}

.flow-canvas {
    flex: 1;
    position: relative;
    overflow: hidden;
}

.vue-flow {
    width: 100%;
    height: 100%;
    background: var(--surface-ground);
}

/* Dark mode specific adjustments */
:global(.p-dark) .vue-flow {
    background: var(--surface-ground);
}

:global(.p-dark) .palette-node {
    background: var(--surface-section) !important;
    color: var(--text-color) !important;
    border-color: var(--surface-border) !important;
}

:global(.p-dark) .palette-node:hover {
    background: var(--surface-hover) !important;
    border-color: var(--primary-color) !important;
}

:global(.p-dark) .flow-sidebar {
    background: var(--surface-card) !important;
    border-color: var(--surface-border) !important;
}

:global(.p-dark) .sidebar-header {
    background: var(--surface-section) !important;
    border-color: var(--surface-border) !important;
}

:global(.p-dark) .stat-item {
    background: var(--surface-section) !important;
    border-color: var(--surface-border) !important;
    color: var(--text-color) !important;
}

/* Force dark mode styles on mobile */
@media (max-width: 768px) {
    :global(.p-dark) .palette-node {
        background: var(--surface-section) !important;
        color: var(--text-color) !important;
    }

    :global(.p-dark) .palette-node:hover {
        background: var(--surface-hover) !important;
    }
}

/* Responsive Design */
@media (max-width: 1024px) {
    .flow-sidebar {
        width: 280px;
    }
}

.mobile-backdrop {
    display: none;
}

@media (max-width: 768px) {
    .flow-editor {
        position: relative;
        overflow: hidden;
        height: 100vh;
    }

    .mobile-backdrop {
        display: block;
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(0, 0, 0, 0.5);
        z-index: 15;
        backdrop-filter: blur(2px);
    }

    .flow-sidebar {
        position: fixed;
        left: 0;
        top: 0;
        height: 100vh;
        width: 280px;
        z-index: 20;
        transform: translateX(-100%);
        transition: transform 0.3s ease;
        box-shadow: 2px 0 12px rgba(0, 0, 0, 0.25);
        max-height: 100vh;
    }

    .flow-sidebar:not(.collapsed) {
        transform: translateX(0);
    }

    .flow-editor.sidebar-collapsed .flow-sidebar {
        transform: translateX(-100%);
    }

    .flow-editor.sidebar-collapsed .mobile-backdrop {
        display: none;
    }

    .sidebar-toggle {
        position: fixed;
        top: 1rem;
        left: 1rem;
        z-index: 25;
        background: var(--surface-card) !important;
        border: 1px solid var(--surface-border) !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    }

    .sidebar-content {
        height: calc(100vh - 80px);
        overflow-y: auto;
        -webkit-overflow-scrolling: touch;
        padding-bottom: 2rem;
    }

    .stats-section {
        margin-bottom: 2rem;
    }
}

@media (max-width: 640px) {
    .toolbar-section {
        flex-wrap: wrap;
        gap: 0.25rem;
    }

    .flow-toolbar {
        padding: 0.75rem;
    }

    .stats-grid {
        grid-template-columns: 1fr;
        gap: 0.5rem;
    }

    .stat-item {
        padding: 0.375rem 0.5rem;
    }
}
</style>
