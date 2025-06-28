import { createApp } from "vue"
import App from "./App.vue"
import router from "./router"
import { createPinia } from "pinia"
import { useThemeStore } from "./stores/themeStore"

import PrimeVue from "primevue/config"
import Aura from "@primeuix/themes/aura"
import { ConfirmationService, ToastService } from "primevue"

import "primeicons/primeicons.css"
import "./assets/theme.css"

// Create Pinia instance
const pinia = createPinia()

// Optional: switch to 'material', 'lara', or 'nora' later
const app = createApp(App)

app.use(router)
app.use(pinia) // Use Pinia before PrimeVue

// Configure PrimeVue
app.use(PrimeVue, {
    theme: {
        preset: Aura,
        options: {
            prefix: "p", // default CSS variable prefix
            darkModeSelector: ".p-dark", // Use PrimeVue's standard dark mode class
            cssLayer: false, // or set to true if you want custom cascade layers
        },
    },
})
app.use(ConfirmationService)
app.use(ToastService)

app.mount("#app")

// Initialize theme store after app is mounted
const themeStore = useThemeStore()
themeStore.init()
