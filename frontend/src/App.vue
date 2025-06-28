<template>
    <div class="app-container">
        <header
            style="
                display: flex;
                align-items: center;
                justify-content: space-between;
            "
        >
            <div style="display: flex; align-items: center">
                <h1 style="margin: 0 1rem 0 0">ISeeTV</h1>
                <nav>
                    <router-link to="/">Home</router-link> |
                    <router-link to="/sources">Sources</router-link>
                </nav>
            </div>
            <button
                aria-label="Settings"
                class="settings-btn"
                @click="openSettings = true"
            >
                <i class="pi pi-cog" style="font-size: 1.7rem"></i>
            </button>
        </header>

        <main>
            <router-view />
        </main>
    </div>
    <SettingsModal
        :open="openSettings"
        v-if="openSettings"
        @close="openSettings = false"
    />
</template>

<script setup lang="ts">
import "primeicons/primeicons.css"
import { ref } from "vue"
import SettingsModal from "./components/SettingsModal.vue"

const openSettings = ref(false)
</script>

<style scoped>
.app-container {
    max-width: 100%;
    margin: auto;
    padding: 1rem;
    font-family: sans-serif;
}
.settings-btn {
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.5rem;
    border-radius: 50%;
    transition: background 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
}
.settings-btn .pi {
    font-size: 1.7rem;
    color: #222;
}
.settings-btn:hover {
    background: #f0f0f0;
}

header {
    margin-bottom: 2rem;
}

nav a {
    margin-right: 1rem;
    text-decoration: none;
    color: #42b983;
}

nav a.router-link-exact-active {
    font-weight: bold;
    text-decoration: underline;
}
</style>
