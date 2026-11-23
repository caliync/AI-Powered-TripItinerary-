// Beta frontend template. SPA for now; switch ssr on when share pages need SEO.
export default defineNuxtConfig({
  compatibilityDate: '2024-10-01',
  ssr: false,
  modules: ['@nuxtjs/tailwindcss'],
  components: [{ path: '~/components', pathPrefix: false }],
  css: ['~/assets/css/tokens.css', '~/assets/css/landing.css', 'leaflet/dist/leaflet.css'],
  app: {
    head: {
      title: 'LakbayWise',
      htmlAttrs: { lang: 'en' },
      meta: [{ name: 'viewport', content: 'width=device-width, initial-scale=1' }],
      link: [
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Lancelot&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap',
        },
      ],
    },
  },
  runtimeConfig: {
    // The real planner is the default. `npm run dev:mock` sets NUXT_PUBLIC_USE_MOCKS=true (see .env.mock).
    // For a deployed site, set NUXT_PUBLIC_API_BASE=https://api.example.com/api/v1
    public: { apiBase: '/api/v1', useMocks: false },
  },
  // In dev the site talks to the FastAPI server on :8000 through this proxy (no CORS needed).
  // 127.0.0.1, not "localhost": on Windows, Node can resolve localhost to ::1 while uvicorn listens on 127.0.0.1.
  nitro: {
    devProxy: { '/api': { target: 'http://127.0.0.1:8000/api', changeOrigin: true } },
  },
  typescript: { strict: true },
})
