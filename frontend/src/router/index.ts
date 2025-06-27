import { createRouter, createWebHistory } from "vue-router"
import type { RouteRecordRaw } from "vue-router"

import Home from "../views/Home.vue"
import Sources from "../views/Sources.vue"

const routes: RouteRecordRaw[] = [
    { path: "/", name: "Home", component: Home },
    { path: "/sources", name: "Sources", component: Sources },
]

const router = createRouter({
    history: createWebHistory(),
    routes,
})

export default router
