import {defineConfig} from '@playwright/test'
export default defineConfig({testDir:'./e2e',timeout:60000,use:{baseURL:process.env.E2E_BASE_URL||'http://127.0.0.1:5173',headless:true,channel:process.env.E2E_BROWSER_CHANNEL},reporter:'list',webServer:process.env.E2E_BASE_URL?undefined:{command:'pnpm dev',url:'http://127.0.0.1:5173',reuseExistingServer:true}})
