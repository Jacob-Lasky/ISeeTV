<template>
    <div class="app-container">
        <header>
            <h1>ISeeTV</h1>
            <nav>
                <router-link to="/">Home</router-link> |
                <router-link to="/sources">Sources</router-link>
            </nav>
        </header>

        <main>
            <router-view />
            <!-- This displays the matched view -->
        </main>
    </div>
</template>

<script setup lang="ts">
// No logic needed here yet
</script>

<style scoped>
.app-container {
    max-width: 960px;
    margin: auto;
    padding: 1rem;
    font-family: sans-serif;
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
