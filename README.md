# R2I2 Winter Resilient Electric Power Systems

Website for the NSF R2I2 subproject — Maximizing Resilience to Winter Weather in Future Electric Power Systems.

Built with **Vite + React**, deployed to **GitHub Pages**, with **Google Sheets** as the content management layer.

## Development

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
npm run preview
```

## Configuration

1. Follow the setup guide at [docs/GOOGLE_CLOUD_SETUP.md](docs/GOOGLE_CLOUD_SETUP.md)
2. Update `src/config.js` with your Google Cloud credentials and Sheet ID

## Deployment

Pushes to the `main` branch automatically deploy to GitHub Pages via GitHub Actions.

Enable Pages in repo Settings > Pages > Source: GitHub Actions.

## Project Structure

```
src/
├── components/    # Reusable UI components
├── constants/     # Theme colors, fallback data
├── hooks/         # Google Sheets, Google Auth, scroll hooks
├── pages/         # Page components (Home, Team, Workshops, etc.)
├── services/      # Google Sheets fetch/parse, portal permissions
├── config.js      # Google API configuration
├── App.jsx        # Root component with routing
└── main.jsx       # Entry point
```
