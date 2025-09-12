/**
 * Layout Composable - Auto-layout using Dagre algorithm
 *
 * Following atomic design principles:
 * - Single responsibility: handles graph layout calculations
 * - Pure functions: layout calculation with no side effects
 * - Modular: can be used by any flow component
 */

import dagre from 'dagre'
import { Position, useVueFlow } from '@vue-flow/core'
import { ref } from 'vue'
import type { FlowNode, FlowEdge } from '@/types/flow-types'

/**
 * Composable to run the layout algorithm on the graph.
 * It uses the `dagre` library to calculate the layout of the nodes and edges.
 */
export function useLayout() {
    const { findNode } = useVueFlow()

    const graph = ref(new dagre.graphlib.Graph())
    const previousDirection = ref('LR')

    /**
     * Apply auto-layout to nodes using Dagre algorithm
     * @param nodes - Array of flow nodes to layout
     * @param edges - Array of flow edges for layout calculation
     * @param direction - Layout direction ('LR' = left-to-right, 'TB' = top-to-bottom)
     * @returns Array of nodes with updated positions
     */
    function layout(nodes: FlowNode[], edges: FlowEdge[], direction: 'LR' | 'TB' = 'LR'): FlowNode[] {
        // Create a new graph instance to avoid stale node/edge references
        const dagreGraph = new dagre.graphlib.Graph()
        graph.value = dagreGraph

        // Configure dagre graph
        dagreGraph.setDefaultEdgeLabel(() => ({}))
        dagreGraph.setGraph({ 
            rankdir: direction,
            nodesep: 100, // Horizontal spacing between nodes
            ranksep: 150, // Vertical spacing between ranks
            marginx: 50,  // Graph margin
            marginy: 50
        })

        previousDirection.value = direction
        const isHorizontal = direction === 'LR'

        // Add nodes to dagre graph with dimensions
        for (const node of nodes) {
            const graphNode = findNode(node.id)
            
            // Use actual node dimensions if available, otherwise use defaults based on node type
            let width = graphNode?.dimensions?.width || 200
            let height = graphNode?.dimensions?.height || 120
            
            // Adjust default sizes based on node type for better layout
            switch (node.type) {
                case 'source':
                    width = width || 180
                    height = height || 100
                    break
                case 'rule':
                    width = width || 220
                    height = height || 140
                    break
                case 'plugin':
                    width = width || 200
                    height = height || 120
                    break
                case 'stream':
                    width = width || 160
                    height = height || 80
                    break
                default:
                    width = width || 200
                    height = height || 120
            }

            dagreGraph.setNode(node.id, { width, height })
        }

        // Add edges to dagre graph
        for (const edge of edges) {
            dagreGraph.setEdge(edge.source, edge.target)
        }

        // Run dagre layout algorithm
        dagre.layout(dagreGraph)

        // Apply calculated positions to nodes
        return nodes.map((node) => {
            const nodeWithPosition = dagreGraph.node(node.id)

            return {
                ...node,
                // Set handle positions based on layout direction
                targetPosition: isHorizontal ? Position.Left : Position.Top,
                sourcePosition: isHorizontal ? Position.Right : Position.Bottom,
                // Apply calculated position (dagre returns center point, Vue Flow expects top-left)
                position: { 
                    x: nodeWithPosition.x - (nodeWithPosition.width / 2), 
                    y: nodeWithPosition.y - (nodeWithPosition.height / 2) 
                },
            }
        })
    }

    /**
     * Get the current layout direction
     */
    function getDirection(): 'LR' | 'TB' {
        return previousDirection.value as 'LR' | 'TB'
    }

    /**
     * Set layout direction for future layouts
     */
    function setDirection(direction: 'LR' | 'TB'): void {
        previousDirection.value = direction
    }

    return { 
        graph, 
        layout, 
        previousDirection,
        getDirection,
        setDirection
    }
}
