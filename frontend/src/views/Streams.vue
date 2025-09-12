<template>
    <div class="streams-view">
        <div class="view-header">
            <h1>Streams</h1>
            <p class="view-description">
                Browse and search through all available IPTV channels with their
                EPG data and program information.
            </p>
        </div>

        <StreamsTable />
    </div>
</template>

<script setup lang="ts">
import StreamsTable from "@/components/StreamsTable.vue"
</script>

<style scoped>
.streams-view {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    padding: 1rem;
    gap: 1rem;
}

.view-header {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.view-header h1 {
    margin: 0;
    font-size: 2rem;
    font-weight: 600;
    color: var(--text-color);
}

.view-description {
    margin: 0;
    color: var(--text-color-secondary);
    font-size: 1rem;
    line-height: 1.5;
}

/* Responsive design */
@media (max-width: 768px) {
    .streams-view {
        padding: 0.5rem;
    }

    .view-header h1 {
        font-size: 1.5rem;
    }

    .view-description {
        font-size: 0.875rem;
    }
}
</style>
