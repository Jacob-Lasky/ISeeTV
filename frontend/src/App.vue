<template>
    <div class="app-container" :class="{ 'dark-theme': themeStore.isDark }">
        <!-- Toast container for application-wide notifications -->
        <Toast position="bottom-right" />
        <header>
            <div class="header-content">
                <div class="header-left">
                    <!-- Mobile Navigation with Hamburger Menu -->
                    <div class="mobile-nav">
                        <Button
                            icon="pi pi-bars"
                            text
                            rounded
                            aria-label="Menu"
                            @click="toggleSidebar"
                        />
                    </div>

                    <!-- Desktop Navigation with TabMenu -->
                    <nav class="desktop-nav">
                        <TabMenu :model="menuItems" />
                    </nav>
                </div>

                <div class="header-right">
                    <h1>
                        <img src="@/favicons/logo32.png" alt="ISeeTV" />ISeeTV
                    </h1>
                    <Button
                        icon="pi pi-cog"
                        text
                        rounded
                        aria-label="Settings"
                        class="settings-btn"
                        @click="openSettings = true"
                    />
                </div>
            </div>
        </header>

        <!-- Mobile Navigation Drawer -->
        <Drawer
            v-model:visible="drawerVisible"
            position="left"
            class="mobile-drawer"
        >
            <template #header>
                <h2>ISeeTV Menu</h2>
            </template>
            <Menu :model="menuItems" />
        </Drawer>

        <main>
            <router-view />
        </main>
    </div>
    <SettingsModal v-model:visible="openSettings" />
    <ConfirmDialog />
</template>

<script setup lang="ts">
import "primeicons/primeicons.css"
import { ref, onMounted } from "vue"
import { useRouter } from "vue-router"
import SettingsModal from "./components/SettingsModal.vue"
import { useThemeStore } from "./stores/themeStore"
import { useToastListener } from "./services/toastService"
import { useToast } from "primevue/usetoast"

// Import PrimeVue components
import TabMenu from "primevue/tabmenu"
import Menu from "primevue/menu"
import Drawer from "primevue/drawer"
import Button from "primevue/button"
import ConfirmDialog from "primevue/confirmdialog"
import Toast from "primevue/toast"

const router = useRouter()
const themeStore = useThemeStore()
const openSettings = ref(false)
const drawerVisible = ref(false)

// Set up toast functionality
const toast = useToast()
const { subscribe } = useToastListener()

// Listen for toast events and display them
onMounted(() => {
    subscribe((message) => {
        toast.add(message)
    })
})

// Define menu items for both TabMenu and Sidebar Menu
const menuItems = [
    {
        label: "Home",
        icon: "pi pi-home",
        command: () => {
            router.push("/")
            drawerVisible.value = false
        },
    },
    {
        label: "Sources",
        icon: "pi pi-database",
        command: () => {
            router.push("/sources")
            drawerVisible.value = false
        },
    },
    {
        label: "Channels",
        icon: "pi pi-list",
        command: () => {
            router.push("/channels")
            drawerVisible.value = false
        },
    },
    {
        label: "Rules",
        icon: "pi pi-filter",
        command: () => {
            router.push("/rules")
            drawerVisible.value = false
        },
    },
]

// Toggle drawer visibility for mobile menu
function toggleSidebar() {
    drawerVisible.value = !drawerVisible.value
}
</script>

<style scoped>
.app-container {
    max-width: 100%;
    margin: auto;
    padding: 1rem;
    font-family: sans-serif;
}

header {
    margin-bottom: 2rem;
}

.header-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.header-left {
    display: flex;
    align-items: center;
}

.header-right {
    display: flex;
    align-items: center;
}

.header-right h1 {
    margin: 0 1rem 0 0;
}

/* Desktop navigation */
.desktop-nav {
    display: block;
}

/* Mobile navigation */
.mobile-nav {
    display: none;
}

/* Mobile sidebar styling */
.mobile-sidebar h2 {
    padding: 1rem;
    margin-top: 0;
    border-bottom: 1px solid #eee;
}

/* Responsive styles */
@media (max-width: 768px) {
    .desktop-nav {
        display: none;
    }

    .mobile-nav {
        display: block;
    }

    .header-left h1 {
        font-size: 1.5rem;
    }
}

/* Override PrimeVue TabMenu styles for better integration */
:deep(.p-tabmenu) {
    border: none;
}

:deep(.p-tabmenu .p-tabmenu-nav) {
    border: none;
    background: transparent;
}

:deep(.p-tabmenu .p-tabmenu-nav .p-tabmenuitem.p-highlight .p-menuitem-link) {
    border-color: #42b983;
    color: #42b983;
}

:deep(
    .p-tabmenu
        .p-tabmenu-nav
        .p-tabmenuitem
        .p-menuitem-link:not(.p-disabled):focus
) {
    box-shadow: 0 0 0 0.2rem rgba(66, 185, 131, 0.2);
}
</style>
