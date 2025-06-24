<script setup lang="ts">
import HelloWorld from './components/HelloWorld.vue'
import { ref, onMounted } from 'vue'

const message = ref('Click the button to fetch a message from the backend')
const loading = ref(false)
const error = ref('')

const fetchMessage = async () => {
  loading.value = true
  error.value = ''
  message.value = 'Loading...'
  
  try {
    // Using a relative URL so it works with our Nginx proxy setup
    // This will be proxied to the backend running on port 1314
    const response = await fetch('/api/message')
    
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`)
    }
    
    const data = await response.json()
    message.value = data.message
  } catch (err) {
    error.value = `Error fetching message: ${err instanceof Error ? err.message : String(err)}`
    message.value = 'Failed to load message'
  } finally {
    loading.value = false
  }
}

// Optional: Fetch message on component mount
onMounted(fetchMessage)
</script>

<template>
  <div class="container">
    <div class="logos">
      <a href="https://vite.dev" target="_blank">
        <img src="/vite.svg" class="logo" alt="Vite logo" />
      </a>
      <a href="https://vuejs.org/" target="_blank">
        <img src="./assets/vue.svg" class="logo vue" alt="Vue logo" />
      </a>
    </div>
    
    <HelloWorld msg="ISeeTV Frontend + Backend Demo" />
    
    <div class="message-container">
      <button @click="fetchMessage" :disabled="loading" class="fetch-button">
        {{ loading ? 'Loading...' : 'Fetch Message from Backend!' }}
      </button>
      
      <div class="message" :class="{ error: error }">
        {{ error || message }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.container {
  display: flex;
  flex-direction: column;
  align-items: center;
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
}

.logos {
  display: flex;
  justify-content: center;
}

.logo {
  height: 6em;
  padding: 1.5em;
  will-change: filter;
  transition: filter 300ms;
}

.logo:hover {
  filter: drop-shadow(0 0 2em #646cffaa);
}

.logo.vue:hover {
  filter: drop-shadow(0 0 2em #42b883aa);
}

.message-container {
  margin-top: 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
}

.fetch-button {
  background-color: #4CAF50;
  border: none;
  color: white;
  padding: 15px 32px;
  text-align: center;
  text-decoration: none;
  display: inline-block;
  font-size: 16px;
  margin: 4px 2px;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.fetch-button:hover {
  background-color: #45a049;
}

.fetch-button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.message {
  margin-top: 1rem;
  padding: 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  width: 100%;
  text-align: center;
}

.error {
  color: red;
  border-color: red;
}
</style>
