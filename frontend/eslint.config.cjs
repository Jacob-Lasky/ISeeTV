// eslint.config.cjs

const vue = require("eslint-plugin-vue")
const ts = require("@typescript-eslint/eslint-plugin")
const prettier = require("eslint-plugin-prettier")
const vueRecommended = require("eslint-plugin-vue/lib/configs/vue3-recommended")
const tsRecommended = require("@typescript-eslint/eslint-plugin").configs
    .recommended
const prettierRecommended = require("eslint-plugin-prettier").configs
    .recommended

module.exports = [
    // Global ignores (applies to everything)
    {
        ignores: [
            "node_modules/",
            "dist/",
            "public/",
            "*.config.js",
            "vite.config.ts",
        ],
    },

    // TypeScript and Vue Single File Components
    {
        files: ["**/*.ts", "**/*.vue"],
        languageOptions: {
            parser: require("vue-eslint-parser"),
            parserOptions: {
                parser: require("@typescript-eslint/parser"),
                ecmaVersion: 2021,
                sourceType: "module",
                project: "./tsconfig.eslint.json",
                extraFileExtensions: [".vue"],
            },
        },
        plugins: {
            vue,
            prettier,
            "@typescript-eslint": ts,
        },
        rules: {
            ...vueRecommended.rules,
            ...tsRecommended.rules,
            ...prettierRecommended.rules,
            "prettier/prettier": "error",
            "@typescript-eslint/no-unsafe-member-access": "error",
            "@typescript-eslint/no-unsafe-assignment": "warn",
            "@typescript-eslint/no-unsafe-call": "warn",
        },
    },

    // JavaScript config files (e.g., eslint.config.cjs)
    {
        files: ["**/*.js", "**/*.cjs"],
        languageOptions: {
            ecmaVersion: 2021,
            sourceType: "module",
            globals: {
                console: "readonly",
                module: "readonly",
                require: "readonly",
                __dirname: "readonly",
            },
        },
        plugins: {
            prettier,
            "@typescript-eslint": ts,
        },
        rules: {
            ...prettierRecommended.rules,
            "prettier/prettier": "error",
        },
    },
]
